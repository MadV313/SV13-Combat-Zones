import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from badlands.adm import parse
from badlands.config import Config
from badlands.db import DB
from badlands.engine import Engine

class GameEventTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();base=Path(self.t.name)
  self.db=DB(str(base/'players.sqlite3'));self.config=Config(str(base/'zones.json'))
  obj=self.config.get();obj['zones']=[{'name':'ComeGetSome','x':4154,'z':5382,'radius':200,'enabled':True}];self.config.set(obj)
  self.engine=Engine(self.db,self.config)
 def tearDown(self):
  self.db.conn.close();self.t.cleanup()
 def test_parser_accepts_server_event(self):
  line='00:00:01 [BCZ] VERIFIED_KILL event=7 kid=guidK123456 vid=guidV123456 zone="ComeGetSome" streak=3'
  self.assertIn('verified_kill',[t for t,v in parse(line)])
 def test_default_ignores_server_kill(self):
  with patch.dict(os.environ,{'BCZ_AUTHORITATIVE_KILLS':'0'}):
   self.engine.handle('00:00:01 [BCZ] VERIFIED_KILL event=7 kid=guidK123456 vid=guidV123456 zone="ComeGetSome" streak=3')
  self.assertEqual(self.db.one('SELECT COUNT(*) AS c FROM kills')['c'],0)
 def test_authoritative_dedupe_and_no_unearned_pending_reward(self):
  line='00:00:01 [BCZ] VERIFIED_KILL event=7 kid=guidK123456 vid=guidV123456 zone="ComeGetSome" streak=3'
  with patch.dict(os.environ,{'BCZ_AUTHORITATIVE_KILLS':'1'}):
   self.engine.handle(line);self.engine.handle(line)
  self.assertEqual(self.db.one('SELECT COUNT(*) AS c FROM kills')['c'],1)
  self.assertEqual(self.db.one('SELECT kills,streak FROM stats WHERE guid=?',('guidK123456',))['streak'],3)
  self.assertEqual(self.db.one('SELECT COUNT(*) AS c FROM rewards')['c'],0)
 def test_game_grant_deduplication(self):
  line='00:00:02 [BCZ] REWARD grant=16 id=guidK123456 tier=3 status=delivered'
  with patch.dict(os.environ,{'BCZ_AUTHORITATIVE_KILLS':'1'}):
   result=self.engine.handle(line);self.engine.handle(line)
  self.assertEqual(result[0][0],'game_reward')
  self.assertEqual(self.db.one('SELECT COUNT(*) AS c FROM game_grants')['c'],1)
 def test_legacy_mode_preserved(self):
  with patch.dict(os.environ,{'BCZ_AUTHORITATIVE_KILLS':'0'}):
   result=self.engine.handle('00:00:02 [BCZ] REWARD grant=16 id=guidK123456 tier=3 status=delivered')
  self.assertEqual(result,[])
  self.assertEqual(self.db.one('SELECT COUNT(*) AS c FROM game_grants')['c'],0)

if __name__=='__main__':unittest.main()
