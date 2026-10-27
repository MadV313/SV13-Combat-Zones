import json,time,math,hashlib
from .adm import parse
class Engine:
 def __init__(self,db,config):self.db=db;self.config=config
 def zone_for(self,x,z,current=None):
  cfg=self.config.get();edge=float(cfg.get('options',{}).get('zone_edge_hysteresis_m',10))
  for safe in cfg.get('safe_zones',[]):
   if math.hypot(x-safe['x'],z-safe['z'])<=safe['radius']:return None
  for zone in cfg['zones']:
   if not zone.get('enabled',True):continue
   r=float(zone['radius'])+(edge if current==zone['name'] else -edge)
   if math.hypot(x-zone['x'],z-zone['z'])<=max(0,r):return zone['name']
  return None
 def handle(self,line):
  events=[];now=time.time()
  for typ,v in parse(line):
   if typ=='connect':self.db.player(v['id'],v['name'])
   elif typ=='position':
    guid=v['id'];self.db.player(guid,v['name']);x=float(v['x']);z=float(v['z'])
    self.db.execute('INSERT INTO positions VALUES(?,?,?,?) ON CONFLICT(guid) DO UPDATE SET x=excluded.x,z=excluded.z,seen_at=excluded.seen_at',(guid,x,z,now))
    previous=self.db.one('SELECT zone,entered_at,last_exit FROM presence WHERE guid=?',(guid,));prev=previous['zone'] if previous else None
    new=self.zone_for(x,z,prev)
    if new!=prev:
     if prev and previous:
      duration=max(0,now-previous['entered_at']);self.db.stat(guid)
      self.db.execute('UPDATE stats SET zone_seconds=zone_seconds+? WHERE guid=?',(duration,guid))
      events.append(('exit',{'name':v['name'],'zone':prev,'guid':guid}))
     self.db.execute('INSERT INTO presence(guid,zone,entered_at,last_exit) VALUES(?,?,?,?) ON CONFLICT(guid) DO UPDATE SET zone=excluded.zone,entered_at=excluded.entered_at,last_exit=excluded.last_exit',(guid,new,now,now if prev else (previous['last_exit'] if previous else 0)))
     if new:
      cooldown=self.config.get().get('options',{}).get('reentry_cooldown_seconds',300)
      if not previous or now-(previous['last_exit'] or 0)>cooldown:events.append(('entry',{'name':v['name'],'zone':new,'guid':guid}))
   elif typ=='kill':
    killer=v['kid'];victim=v['vid'];self.db.player(killer,v['killer']);self.db.player(victim,v['victim'])
    if killer==victim:continue
    # Never credit without fresh position for both participants.
    a=self.db.one('SELECT x,z,seen_at FROM positions WHERE guid=?',(killer,));b=self.db.one('SELECT x,z,seen_at FROM positions WHERE guid=?',(victim,))
    max_age=float(self.config.get().get('options',{}).get('max_kill_position_age_seconds',360))
    if not a or not b or now-a['seen_at']>max_age or now-b['seen_at']>max_age:continue
    ka=self.zone_for(a['x'],a['z']);kb=self.zone_for(b['x'],b['z'])
    if not ka or ka!=kb:continue
    key=hashlib.sha256(line.encode('utf8')).hexdigest()
    if self.db.one('SELECT 1 FROM kills WHERE unique_key=?',(key,)):continue
    self.db.execute('INSERT INTO kills(unique_key,killer,victim,zone,occurred_at) VALUES(?,?,?,?,?)',(key,killer,victim,ka,now))
    self.db.stat(killer);self.db.stat(victim)
    self.db.execute('UPDATE stats SET kills=kills+1,streak=streak+1,best_streak=max(best_streak,streak+1) WHERE guid=?',(killer,))
    self.db.execute('UPDATE stats SET deaths=deaths+1,streak=0 WHERE guid=?',(victim,))
    streak=self.db.one('SELECT streak FROM stats WHERE guid=?',(killer,))['streak']
    tier=self.config.get().get('rewards',{}).get('killstreak_tiers',{}).get(str(streak))
    if tier:
     self.db.execute('INSERT INTO rewards(guid,kind,tier,items,created_at) VALUES(?,?,?,?,?)',(killer,'killstreak',str(streak),json.dumps(tier.get('items',[])),now))
     events.append(('reward',{'name':v['killer'],'tier':streak,'guid':killer}))
    events.append(('kill',{'killer':v['killer'],'victim':v['victim'],'zone':ka,'streak':streak}))
  return events
