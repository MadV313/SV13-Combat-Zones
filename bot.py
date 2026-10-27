import os,asyncio,logging,json,time
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands,tasks
from dotenv import load_dotenv
from badlands.config import Config
from badlands.db import DB
from badlands.ingest import Reader
from badlands.engine import Engine

load_dotenv();logging.basicConfig(level=logging.INFO)
log=logging.getLogger('badlands')
TOKEN=os.getenv('DISCORD_TOKEN','')
GUILD_ID=int(os.getenv('DISCORD_GUILD_ID','0') or 0)
ADMIN_ROLE_ID=int(os.getenv('ADMIN_ROLE_ID','0') or 0)
ANNOUNCE_CHANNEL_ID=int(os.getenv('ANNOUNCE_CHANNEL_ID','0') or 0)
config=Config();db=DB(os.getenv('DATABASE_PATH','data/badlands.sqlite3'));engine=Engine(db,config);reader=Reader(db)
intents=discord.Intents.default();bot=commands.Bot(command_prefix='!',intents=intents)

def authorized(i):return i.user.guild_permissions.manage_guild or (ADMIN_ROLE_ID and any(r.id==ADMIN_ROLE_ID for r in getattr(i.user,'roles',[])))
async def admin(i):
 if not authorized(i):
  await i.response.send_message('Admin role or Manage Server required.',ephemeral=True);return False
 return True
async def notice(kind,p):
 if not ANNOUNCE_CHANNEL_ID:return
 channel=bot.get_channel(ANNOUNCE_CHANNEL_ID)
 if channel is None:
  try:channel=await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
  except Exception:return
 cfg=config.get().get('options',{})
 if kind=='entry' and cfg.get('announce_zone_entry',True):msg=f'📡 **Combat zone activity:** A survivor entered **{p["zone"]}**.'
 elif kind=='kill' and cfg.get('announce_kills',True):msg=f'⚔️ **{p["killer"]}** eliminated **{p["victim"]}** at **{p["zone"]}** | streak **{p["streak"]}**.'
 elif kind=='reward':msg=f'🏆 **{p["name"]}** earned a **{p["tier"]}-kill reward** (pending in-game delivery).'
 else:return
 try:await channel.send(msg,allowed_mentions=discord.AllowedMentions.none())
 except Exception:log.exception('Announcement failed')
@tasks.loop(seconds=max(15,int(os.getenv('POLL_SECONDS','60'))))
async def scan():
 try:
  for line in await asyncio.to_thread(reader.new_lines):
   for kind,details in engine.handle(line):await notice(kind,details)
 except Exception:log.exception('ADM scan failed; no events credited')
@scan.before_loop
async def wait_ready():await bot.wait_until_ready()
@bot.event
async def on_ready():
 if not scan.is_running():scan.start()
 log.info('Ready as %s',bot.user)
@bot.event
async def setup_hook():
 if GUILD_ID:
  guild=discord.Object(id=GUILD_ID);bot.tree.copy_global_to(guild=guild);await bot.tree.sync(guild=guild)
 else:await bot.tree.sync()

@bot.tree.command(name='setzone',description='Create or replace a Nasdara combat zone (X/Z meters).')
@app_commands.describe(name='Unique zone name',x='Map X',z='Map Z',radius='Meters (50–1500)')
async def setzone(i:discord.Interaction,name:str,x:float,z:float,radius:app_commands.Range[int,50,1500]):
 if not await admin(i):return
 data=config.get()
 if any((x-s['x'])**2+(z-s['z'])**2 < (radius+s['radius'])**2 for s in data['safe_zones']):
  return await i.response.send_message('Zone overlaps a protected trader safe zone; move or resize it.',ephemeral=True)
 data['zones']=[v for v in data['zones'] if v['name'].casefold()!=name.casefold()]
 data['zones'].append(dict(name=name[:64],x=x,z=z,radius=radius,enabled=True));config.set(data)
 await i.response.send_message(f'✅ Zone **{name}** ({x:.0f}, {z:.0f}) r={radius}m saved. Export config to sync the DayZ mod.',ephemeral=True)

@bot.tree.command(name='removezone',description='Delete combat zone.')
async def removezone(i:discord.Interaction,name:str):
 if not await admin(i):return
 data=config.get();before=len(data['zones']);data['zones']=[z for z in data['zones'] if z['name'].casefold()!=name.casefold()];config.set(data)
 await i.response.send_message('Removed.' if len(data['zones'])<before else 'Not found.',ephemeral=True)

@bot.tree.command(name='togglezone',description='Enable or disable a zone.')
async def togglezone(i:discord.Interaction,name:str,enabled:bool):
 if not await admin(i):return
 data=config.get();found=False
 for z in data['zones']:
  if z['name'].casefold()==name.casefold():z['enabled']=enabled;found=True
 if found:config.set(data)
 await i.response.send_message(f'{name}: {"enabled" if enabled else "disabled"}' if found else 'Not found.',ephemeral=True)

@bot.tree.command(name='zones',description='List combat zones.')
async def zones(i:discord.Interaction):
 a=config.get()['zones'];await i.response.send_message('\n'.join(f'**{z["name"]}**: X={z["x"]:.0f} Z={z["z"]:.0f}, r={z["radius"]}m, {"ON" if z.get("enabled",True) else "OFF"}' for z in a)[:1900] or 'No zones configured.',ephemeral=True)

@bot.tree.command(name='exportzones',description='Download DayZ side zone configuration for server installation.')
async def exportzones(i:discord.Interaction):
 if not await admin(i):return
 import io
 body={'zones':config.get()['zones'],'safe_zones':config.get()['safe_zones']}
 await i.response.send_message('Upload this file to the DayZ server profile as `BadlandsCombatZones/zones.json`. Reboot game server.',file=discord.File(io.BytesIO(json.dumps(body,indent=2).encode()),filename='zones.json'),ephemeral=True)

@bot.tree.command(name='radarstats',description='Combat-zone player rankings.')
async def radarstats(i:discord.Interaction):
 rows=db.all('SELECT p.name,s.kills,s.deaths,s.best_streak FROM stats s JOIN players p ON p.guid=s.guid ORDER BY s.kills DESC LIMIT 10')
 await i.response.send_message('\n'.join(f'{idx}. **{r["name"]}** | {r["kills"]} kills | {r["deaths"]} deaths | best streak {r["best_streak"]}' for idx,r in enumerate(rows,1)) or 'No verified zone kills yet.',ephemeral=True)

@bot.tree.command(name='rewards',description='Your linked pending physical rewards.')
async def rewards(i:discord.Interaction):
 rows=db.all('SELECT id,kind,tier,items,status FROM rewards WHERE guid IN (SELECT guid FROM players WHERE discord_id=?) ORDER BY id DESC LIMIT 15',(str(i.user.id),))
 await i.response.send_message('\n'.join(f'#{r["id"]} {r["kind"]} {r["tier"]}: {r["status"]} ({r["items"]})' for r in rows)[:1900] or 'No rewards yet. Link your GUID with an admin.',ephemeral=True)

@bot.tree.command(name='linkplayer',description='Admin only: link verified DayZ GUID to Discord member.')
async def linkplayer(i:discord.Interaction,player_guid:str,member:discord.Member):
 if not await admin(i):return
 if not db.one('SELECT 1 FROM players WHERE guid=?',(player_guid,)):
  return await i.response.send_message('GUID not observed in the ADM logs. Join the server first.',ephemeral=True)
 db.execute('UPDATE players SET discord_id=? WHERE guid=?',(str(member.id),player_guid))
 await i.response.send_message('Linked verified log identity. Check player consent before assigning.',ephemeral=True)

@bot.tree.command(name='pendingrewards',description='Admin audit of pending physical rewards; NO automatic spawning.')
async def pendingrewards(i:discord.Interaction):
 if not await admin(i):return
 rows=db.all("SELECT r.id,p.name,r.kind,r.tier,r.items FROM rewards r LEFT JOIN players p ON p.guid=r.guid WHERE r.status='pending' ORDER BY r.id DESC LIMIT 20")
 await i.response.send_message('\n'.join(f'#{r["id"]} {r["name"]}: {r["kind"]} {r["tier"]} {r["items"]}' for r in rows)[:1900] or 'No pending rewards.',ephemeral=True)

@bot.tree.command(name='uav',description='Show recent ADM-derived player positions on a configured Nasdara map.')
async def uav(i:discord.Interaction):
 if not await admin(i):return
 path=os.getenv('NASDARA_MAP_IMAGE','');mx=float(os.getenv('MAP_MAX_X',0));mz=float(os.getenv('MAP_MAX_Z',0))
 if not path or not Path(path).exists() or mx<=0 or mz<=0:
  return await i.response.send_message('UAV not calibrated. Set NASDARA_MAP_IMAGE, MAP_MAX_X and MAP_MAX_Z.',ephemeral=True)
 from badlands.uav import render
 rows=[dict(r) for r in db.all('SELECT x,z,seen_at FROM positions')];image=render(path,mx,mz,config.get()['zones'],rows)
 await i.response.send_message('Last logged positions only — may be several minutes old. Admin access only.',file=discord.File(image,'uav.png'),ephemeral=True)

@bot.tree.command(name='health',description='Current integration/config status.')
async def health(i:discord.Interaction):
 if not await admin(i):return
 r=db.one('SELECT remote_name,offset_bytes FROM ingest WHERE id=1')
 await i.response.send_message(f'ADM cursor: `{r["remote_name"] or "not connected"}` at byte {r["offset_bytes"]}; zones={len(config.get()["zones"])}; poll={os.getenv("POLL_SECONDS","60")}s. In-game spawning NOT YET WIRED.',ephemeral=True)

if __name__=='__main__':
 if not TOKEN:raise SystemExit('Set DISCORD_TOKEN')
 bot.run(TOKEN)
