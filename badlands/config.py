import json, os, tempfile
from pathlib import Path

DEFAULT=Path(__file__).resolve().parent.parent/'config/zones.example.json'
class Config:
    def __init__(self, path=None):
        self.path=Path(path or os.getenv('CONFIG_PATH','data/zones.json'))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if not self.path.exists():
            self.path.write_text(DEFAULT.read_text(encoding='utf8'),encoding='utf8')
    def get(self):
        return json.loads(self.path.read_text(encoding='utf8'))
    def set(self,obj):
        fd,name=tempfile.mkstemp(dir=self.path.parent,prefix='.zones-',suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf8') as f:
                json.dump(obj,f,indent=2); f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name): os.unlink(name)
