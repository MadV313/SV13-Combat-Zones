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
 for m in PLAYER.finditer(line):out.append(('position',m.groupdict()))
 m=CONNECT.search(line)
 if m:out.append(('connect',m.groupdict()))
 m=KILL.search(line)
 if m:out.append(('kill',m.groupdict()))
 return out
