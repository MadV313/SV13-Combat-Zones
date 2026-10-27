import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from badlands.db import DB
from badlands.ingest import Reader

class FakeFTPS:
    last = None
    def __init__(self, context=None, timeout=None):
        assert context and context.verify_mode
        self.calls = []
        FakeFTPS.last = self
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def connect(self, host, port): self.calls.append(('connect', host, port))
    def auth(self): self.calls.append(('auth',))
    def login(self, user, password): self.calls.append(('login', user))
    def prot_p(self): self.calls.append(('prot_p',))
    def cwd(self, directory): self.calls.append(('cwd', directory))
    def mlsd(self):
        return iter([('older.ADM', {'type':'file','modify':'20261026010000'}),
                     ('newer.ADM', {'type':'file','modify':'20261027010000'}),
                     ('other.RPT', {'type':'file','modify':'20261028010000'})])
    def retrbinary(self, cmd, cb):
        self.calls.append(('retrbinary', cmd))
        cb(b'12:00 first\n')

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = DB(str(Path(self.tmp.name)/'db.sqlite3'))
    def tearDown(self):
        self.db.conn.close();self.tmp.cleanup()
    def test_ftps_encryption_and_latest_file(self):
        env = {'ADM_LOCAL_PATH':'','FTP_HOST':'usny412.gamedata.io','FTP_PORT':'21',
               'FTP_USER':'username','FTP_PASSWORD':'password','FTP_DIRECTORY':'/config',
               'FTP_FILE_SUFFIX':'.ADM'}
        with patch.dict(os.environ, env), patch('badlands.ingest.FTP_TLS', FakeFTPS):
            name, data = Reader(self.db).read_snapshot()
        self.assertIn('newer.ADM', name)
        self.assertEqual(data, b'12:00 first\n')
        calls = FakeFTPS.last.calls
        self.assertLess(calls.index(('auth',)), calls.index(('login','username')))
        self.assertLess(calls.index(('prot_p',)), calls.index(('retrbinary','RETR newer.ADM')))
    def test_cursor_skips_existing_history_then_reads_new_lines(self):
        path = Path(self.tmp.name)/'server.ADM'
        path.write_bytes(b'old event\n')
        with patch.dict(os.environ, {'ADM_LOCAL_PATH':str(path)}):
            self.assertEqual(Reader(self.db).new_lines(), [])
            with path.open('ab') as f:f.write(b'new event\n')
            self.assertEqual(Reader(self.db).new_lines(), ['new event'])
    def test_unconfigured(self):
        with patch.dict(os.environ, {'ADM_LOCAL_PATH':'','FTP_HOST':'','SFTP_HOST':''}):
            self.assertEqual(Reader(self.db).new_lines(), [])

if __name__=='__main__': unittest.main()
