"""Conservative PC ADM parser. Kill credit only when both GUIDs appear in a recognized log event."""
import re
GUID=r'([A-Za-z0-9_=-]{8,})'
# Standard DayZ: Player "Name" (id=GUID pos=<X, Z, ALT>)
PLAYER=re.compile(r'Player "(?P<name>[^"]+)"\s*\(id=(?P<id>[^\s,)]+)(?:[, ]+)?[^)]*?pos=<\s*(?P<x>-?\d+(?:\.\d+)?),\s*(?P<z>-?\d+(?:\.\d+)?),\s*-?\d+(?:\.\d+)?>',re.I)
CONNECT=re.compile(r'Player "(?P<name>[^"]+)"\s*\(id=(?P<id>[^\s,)]+)\) is connected',re.I)
# DayZ baseline kill: Player "Victim" (id=GUID pos=<..>) killed by Player "Killer" (id=GUID pos=<..>)
KILL=re.compile(r'Player "(?P<victim>[^"]+)"\s*\(id=(?P<vid>[^\s,)]+).*?\)\s+(?:was )?killed by (?:Player )?"(?P<killer>[^"]+)"\s*\(id=(?P<kid>[^\s,)]+)',re.I)
# Some standard logs use "killed by Player" with an unquoted player after word Player; customize only with evidence.
def parse(line):
 out=[]
 if not KILL.search(line):
  for m in PLAYER.finditer(line):out.append(('position',m.groupdict()))
 m=CONNECT.search(line)
 if m:out.append(('connect',m.groupdict()))
 m=KILL.search(line)
 if m:out.append(('kill',m.groupdict()))
 return out

# Authoritative game-side location telemetry. Player ID comes from DayZ GetIdentity().GetId().
# Never treat these as authenticated if read from an untrusted arbitrary source.
BCZ_POSITION=re.compile(r'\[BCZ\] POS id=(?P<id>[^\s]+) name="(?P<name>[^"\r\n]{1,80})" x=(?P<x>-?\d+(?:\.\d+)?) z=(?P<z>-?\d+(?:\.\d+)?)',re.I)
BCZ_BOUNDARY=re.compile(r'\[BCZ\] (?P<action>ENTER|EXIT) guid=(?P<id>[^\s]+) zone=(?P<zone>[^\r\n]+)',re.I)
_old_parse=parse
def parse(line):
 out=_old_parse(line)
 m=BCZ_POSITION.search(line)
 if m:out.append(('position',m.groupdict()))
 # Boundary markers are for audit only. Position processing remains authoritative
 # for Discord zone state, preventing duplicate announcements from two log formats.
 return out
