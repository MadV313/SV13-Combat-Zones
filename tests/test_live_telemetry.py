import tempfile, unittest, time
from pathlib import Path
from badlands.adm import parse
from badlands.config import Config
from badlands.db import DB
from badlands.engine import Engine

class LiveTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); base=Path(self.temp.name)
  self.db=DB(str(base/'db.sqlite'));self.cfg=Config(str(base/'zones.json'))
  conf=self.cfg.get();conf['zones']=[{'name':'ComeGetSome','x':4154,'z':5382,'radius':200,'enabled':True}]
  conf['options']['max_kill_position_age_seconds']=45;self.cfg.set(conf)
  self.engine=Engine(self.db,self.cfg)
 def tearDown(self):self.db.conn.close();self.temp.cleanup()
 def test_server_position_without_discord(self):
  line='12:00 [BCZ] POS id=GUID12345678 name="SoloPlayer" x=4154 z=5382'
  self.assertEqual(parse(line)[0][0],'position')
  events=self.engine.handle(line)
  self.assertEqual(events[0][0],'entry')
  row=self.db.one('SELECT discord_id FROM players WHERE guid=?',('GUID12345678',))
  self.assertIsNone(row['discord_id'])
 def test_no_duplicate_on_repeated_position(self):
  line='[BCZ] POS id=GUID12345678 name="SoloPlayer" x=4154 z=5382'
  self.engine.handle(line);self.assertEqual(self.engine.handle(line),[])
 def test_position_freshness_gate(self):
  a='[BCZ] POS id=GUID12345678 name="A" x=4154 z=5382'
  b='[BCZ] POS id=GUID87654321 name="B" x=4160 z=5384'
  self.engine.handle(a);self.engine.handle(b)
  self.db.execute('UPDATE positions SET seen_at=? WHERE guid=?',(time.time()-120,'GUID12345678'))
  kill='Player "B" (id=GUID87654321 pos=<4160, 5384, 1>) killed by Player "A" (id=GUID12345678 pos=<4154, 5382, 1>)'
  self.assertEqual(self.engine.handle(kill),[])

if __name__=='__main__':unittest.main()
