import tempfile,unittest
from pathlib import Path
from badlands.config import Config
from badlands.db import DB
from badlands.engine import Engine
from badlands.adm import parse
class EngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();r=Path(self.tmp.name);self.db=DB(str(r/'t.db'));self.cfg=Config(str(r/'zones.json'))
  a=self.cfg.get();a['zones']=[{'name':'test','x':1000,'z':1000,'radius':250,'enabled':True}];self.cfg.set(a);self.e=Engine(self.db,self.cfg)
 def tearDown(self):self.db.conn.close();self.tmp.cleanup()
 def test_zone_and_safezone(self):
  self.assertEqual(self.e.zone_for(1000,1000),'test')
  self.assertIsNone(self.e.zone_for(1400,1400))
  self.assertIsNone(self.e.zone_for(8342.02,7806.61))
 def test_parse(self):
  self.assertEqual(parse('12:00 Player "A" (id=ABCDEF012345 pos=<1010.5, 1001, 4.5>)')[0][0],'position')
 def test_position(self):
  ev=self.e.handle('12:00 Player "A" (id=ABCDEF012345 pos=<1000, 1000, 4>)');self.assertEqual(ev[0][0],'entry')
if __name__=='__main__':unittest.main()
