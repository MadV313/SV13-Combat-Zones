"""Regression tests from the Nov 10, 2026 ComeGetSome PvP session."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from badlands.announcements import make, RADAR, FROST
from badlands.adm import parse
from badlands.config import Config
from badlands.db import DB
from badlands.engine import Engine

KILL_LINE = ('19:15:01 | Player "MadV" (DEAD) (id=mad_guid123 pos=<4150.0, 5378.7, 271.1>) '
             'killed by Player "Doc Holliday" (id=doc_guid123 pos=<4150.8, 5379.2, 271.0>) '
             'with (MeleeFist)')

class LiveReplayTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  root=Path(self.tmp.name)
  self.db=DB(str(root/'db.sqlite3'))
  self.cfg=Config(str(root/'zones.json'))
  self.engine=Engine(self.db,self.cfg)
  obj=self.cfg.get()
  obj['zones']=[{'name':'ComeGetSome','x':4154,'z':5382,'radius':200,'enabled':True}]
  self.cfg.set(obj)
 def tearDown(self):
  self.db.conn.close()
  self.tmp.cleanup()
 def test_kill_log_names_death_and_explicit_streak(self):
  self.assertEqual([x for x,_ in parse(KILL_LINE)],["death","kill"])
  with patch.dict(os.environ,{'BCZ_BOUNDARY_SOURCE':'server','BCZ_AUTHORITATIVE_KILLS':'1'}):
   self.engine.handle('Player "MadV" (id=mad_guid123 pos=<4154, 5382, 271>) is connected')
   self.engine.handle('Player "Doc Holliday" (id=doc_guid123 pos=<4154, 5382, 271>) is connected')
   self.assertEqual(self.engine.handle('[BCZ] ENTER guid=mad_guid123 zone=ComeGetSome')[0][0],'entry')
   self.engine.handle(KILL_LINE)
   self.assertEqual(self.db.one('SELECT zone FROM presence WHERE guid=?',('mad_guid123',))['zone'],None)
   self.assertEqual(self.engine.handle('Player "MadV" (id=mad_guid123 pos=<8338, 7814, 271>)'),[])
   self.assertEqual(self.engine.handle('[BCZ] EXIT guid=mad_guid123 zone=ComeGetSome'),[])
   events=self.engine.handle('[BCZ] VERIFIED_KILL event=1 kid=doc_guid123 vid=mad_guid123 zone="ComeGetSome" streak=1')
   self.assertEqual(events[0][0],'kill')
   self.assertEqual(events[0][1]['killer'],'Doc Holliday')
   self.assertEqual(events[0][1]['victim'],'MadV')
   self.assertEqual(self.engine.handle('[BCZ] VERIFIED_KILL event=1 kid=doc_guid123 vid=mad_guid123 zone="ComeGetSome" streak=1'),[])
   self.assertEqual(self.db.one('SELECT kills FROM stats WHERE guid=?',('doc_guid123',))['kills'],1)
 def test_server_boundary_blocks_position_ghost_exits(self):
  with patch.dict(os.environ,{'BCZ_BOUNDARY_SOURCE':'server','BCZ_AUTHORITATIVE_KILLS':'1'}):
   self.engine.handle('Player "MadV" (id=mad_guid123 pos=<5428, 9954, 300>) is connected')
   entry=self.engine.handle('[BCZ] ENTER guid=mad_guid123 zone=ComeGetSome')
   self.assertEqual([k for k,_ in entry],['entry'])
   for _ in range(12):
    self.assertEqual(self.engine.handle('Player "MadV" (id=mad_guid123 pos=<5428, 9954, 300>)'),[])
   exit_events=self.engine.handle('[BCZ] EXIT guid=mad_guid123 zone=ComeGetSome')
   self.assertEqual([k for k,_ in exit_events],['exit'])
   self.assertEqual(self.engine.handle('[BCZ] EXIT guid=mad_guid123 zone=ComeGetSome'),[])
 def test_original_emoji_and_clear_copy(self):
  zones=self.cfg.get()['zones']
  entry=make('entry',{'name':'MadV','zone':'ComeGetSome'},zones)
  self.assertIn(RADAR,entry['title'])
  self.assertIn(FROST,entry['description'])
  self.assertIn('zone center',entry['fields'][0][1])
  kill=make('kill',{'killer':'Doc Holliday','victim':'MadV','zone':'ComeGetSome','streak':2},zones)
  self.assertIn('DOUBLE ELIMINATION',kill['description'])
  self.assertNotIn('entered eliminated',kill['description'])
  self.assertTrue(all('livonia' not in str(f).lower() for f in kill['fields']))
  exit_note=make('exit',{'name':'MadV','zone':'ComeGetSome'},zones)
  self.assertIn('moved beyond',exit_note['description'])
 def test_actual_log_replay_if_present(self):
  # The test also works in GitHub after the uploaded ADM is absent.
  logfile=Path('/mnt/data/DayZServer_x64_2026-11-10_18-21-20.ADM')
  if not logfile.exists():self.skipTest('Session log not available in GitHub')
  all_events=[]
  with patch.dict(os.environ,{'BCZ_BOUNDARY_SOURCE':'server','BCZ_AUTHORITATIVE_KILLS':'1'}):
   for line in logfile.read_text(encoding='utf8',errors='replace').splitlines():
    all_events.extend(self.engine.handle(line))
  kills=[p for kind,p in all_events if kind=='kill']
  self.assertEqual(len(kills),4)
  self.assertEqual([x['streak'] for x in kills],[1,2,1,2])
  self.assertEqual(kills[0].get('weapon'), '(MeleeFist)')
  self.assertAlmostEqual(float(kills[1].get('distance')),3.94443,places=4)
  self.assertAlmostEqual(float(kills[3].get('x')),4135.4,places=1)
  exits=[p for kind,p in all_events if kind=='exit']
  self.assertEqual(len(exits),3)
  self.assertEqual(self.db.one('SELECT COUNT(*) AS c FROM rewards')['c'],0)

if __name__=='__main__':unittest.main()
