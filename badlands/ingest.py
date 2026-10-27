"""Nitrado DayZ ADM ingestion via verified FTPS, SFTP, or local file.

Existing offset/cursor handling is retained: never replay historic events on startup.
"""
import logging
import os
import ssl
from datetime import datetime, timezone
from ftplib import FTP_TLS, error_perm
from pathlib import Path
from posixpath import join as remote_join

log = logging.getLogger(__name__)


class Reader:
    def __init__(self, db):
        self.db = db

    def read_snapshot(self):
        """Read latest ADM snapshot. Never silently downgrade a secure connection."""
        path = os.getenv('ADM_LOCAL_PATH', '').strip()
        if path:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(path)
            return str(p), p.read_bytes()

        if os.getenv('FTP_HOST', '').strip():
            return self._read_ftps()
        if os.getenv('SFTP_HOST', '').strip():
            return self._read_sftp()
        return None, None

    @staticmethod
    def _credentials(prefix):
        host = os.getenv(prefix + '_HOST', '').strip()
        username = os.getenv(prefix + '_USER', '').strip()
        password = os.getenv(prefix + '_PASSWORD', '')
        if not username or not password:
            raise RuntimeError(f'{prefix}_USER and {prefix}_PASSWORD are required')
        return host, username, password

    def _read_ftps(self):
        """Explicit TLS on port 21, cert-verified control AND encrypted data channel."""
        host, username, password = self._credentials('FTP')
        port = int(os.getenv('FTP_PORT', '21'))
        directory = os.getenv('FTP_DIRECTORY', '/dayzstandalone/config').strip() or '.'
        suffix = os.getenv('FTP_FILE_SUFFIX', '.ADM').lower()
        context = ssl.create_default_context()
        # This uses TLS hostname verification + trusted CAs. No insecure fallback to FTP.
        with FTP_TLS(context=context, timeout=25) as ftp:
            ftp.connect(host, port)
            ftp.auth()
            ftp.login(username, password)
            ftp.prot_p()  # PRIVATE transfer channel; critical for credentials/log confidentiality.
            ftp.cwd(directory)
            names = []
            try:
                for name, facts in ftp.mlsd():
                    if facts.get('type', 'file') == 'file' and name.lower().endswith(suffix):
                        names.append((name, facts.get('modify', '')))
            except (error_perm, NotImplementedError):
                # Some hosts disable MLSD; NLST + MDTM is widely supported.
                for entry in ftp.nlst():
                    name = entry.rsplit('/', 1)[-1]
                    if not name.lower().endswith(suffix):
                        continue
                    try:
                        stamp = ftp.sendcmd('MDTM ' + name).split(' ', 1)[-1]
                    except error_perm:
                        stamp = ''
                    names.append((name, stamp))
            if not names:
                log.info('No %s files in FTPS directory %s', suffix, directory)
                return None, None
            # Names break ties; DayZ rotates ADM using timestamp-bearing filenames.
            chosen = max(names, key=lambda item: (item[1], item[0]))[0]
            chunks = []
            ftp.retrbinary('RETR ' + chosen, chunks.append)
            return f'ftps://{host}:{port}{remote_join(directory, chosen)}', b''.join(chunks)

    def _read_sftp(self):
        host, username, password = self._credentials('SFTP')
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        known = os.getenv('SFTP_KNOWN_HOSTS', '').strip()
        if not known:
            raise RuntimeError('Set SFTP_KNOWN_HOSTS to a verified known_hosts file (no TOFU)')
        client.load_host_keys(known)
        client.connect(hostname=host, port=int(os.getenv('SFTP_PORT', '22')),
                       username=username, password=password, timeout=20,
                       allow_agent=False, look_for_keys=False)
        try:
            with client.open_sftp() as s:
                directory = os.getenv('SFTP_DIRECTORY', '.')
                suffix = os.getenv('SFTP_FILE_SUFFIX', '.ADM').lower()
                files = [v for v in s.listdir_attr(directory)
                         if v.filename.lower().endswith(suffix)]
                if not files:
                    return None, None
                newest = max(files, key=lambda x: x.st_mtime)
                name = directory.rstrip('/') + '/' + newest.filename
                with s.open(name, 'rb') as f:
                    return name, f.read()
        finally:
            client.close()

    def new_lines(self):
        name, data = self.read_snapshot()
        if data is None:
            return []
        row = self.db.one('SELECT remote_name,offset_bytes,tail FROM ingest WHERE id=1')
        old_name, offset, tail = row
        if name != old_name or len(data) < offset:
            # Initialize at end of current log: no back-pay of old kills / rewards.
            self.db.execute('UPDATE ingest SET remote_name=?,offset_bytes=?,tail=? WHERE id=1',
                            (name, len(data), ''))
            log.info('ADM cursor initialized for %s at %s bytes', name, len(data))
            return []
        raw = tail.encode('utf8') + data[offset:]
        if b'\n' not in raw:
            self.db.execute('UPDATE ingest SET offset_bytes=?,tail=? WHERE id=1',
                            (len(data), raw.decode('utf8', errors='replace')))
            return []
        *complete, remainder = raw.split(b'\n')
        self.db.execute('UPDATE ingest SET offset_bytes=?,tail=? WHERE id=1',
                        (len(data), remainder.decode('utf8', errors='replace')))
        return [line.decode('utf8', errors='replace').rstrip('\r') for line in complete]
