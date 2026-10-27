import os, time, logging
from pathlib import Path
from .adm import parse
log=logging.getLogger(__name__)
class Reader:
 def __init__(self,db):self.db=db
 def read_snapshot(self):
  """Read latest remote ADM safely with persistent cursor. Never ingest full old history on first boot."""
  path=os.getenv('ADM_LOCAL_PATH','').strip()
  if path:
   p=Path(path)
   if not p.exists():raise FileNotFoundError(path)
   return str(p),p.read_bytes()
  host=os.getenv('SFTP_HOST','')
  if not host:return None,None
  import paramiko
  client=paramiko.SSHClient();client.set_missing_host_key_policy(paramiko.RejectPolicy())
  known=os.getenv('SFTP_KNOWN_HOSTS','')
  if not known: raise RuntimeError('Set SFTP_KNOWN_HOSTS to a verified known_hosts file (no TOFU)')
  client.load_host_keys(known)
  client.connect(hostname=host,port=int(os.getenv('SFTP_PORT',22)),username=os.getenv('SFTP_USER'),password=os.getenv('SFTP_PASSWORD'),timeout=20,allow_agent=False,look_for_keys=False)
  try:
   with client.open_sftp() as s:
    directory=os.getenv('SFTP_DIRECTORY','.')
    suffix=os.getenv('SFTP_FILE_SUFFIX','.ADM').lower()
    files=[v for v in s.listdir_attr(directory) if v.filename.lower().endswith(suffix)]
    if not files:return None,None
    newest=max(files,key=lambda x:x.st_mtime)
    name=directory.rstrip('/')+'/'+newest.filename
    with s.open(name,'rb') as f:data=f.read()
    return name,data
  finally:client.close()
 def new_lines(self):
  name,data=self.read_snapshot()
  if data is None:return []
  row=self.db.one('SELECT remote_name,offset_bytes,tail FROM ingest WHERE id=1');old_name,offset,tail=row
  if name!=old_name or len(data)<offset:
   # Deliberately don't replay preexisting kills on first import / rotation.
   self.db.execute('UPDATE ingest SET remote_name=?,offset_bytes=?,tail=? WHERE id=1',(name,len(data),''))
   log.info('ADM cursor initialized for %s at %s bytes',name,len(data));return []
  fresh=data[offset:]
  raw=tail.encode('utf8')+fresh
  if b'\n' not in raw:
   self.db.execute('UPDATE ingest SET offset_bytes=?,tail=? WHERE id=1',(len(data),raw.decode('utf8',errors='replace')));return []
  *complete,remainder=raw.split(b'\n')
  self.db.execute('UPDATE ingest SET offset_bytes=?,tail=? WHERE id=1',(len(data),remainder.decode('utf8',errors='replace')))
  return [line.decode('utf8',errors='replace').rstrip('\r') for line in complete]
