"""DayZ ADM and server-authoritative Combat Zones record parsing.

Only BCZ VERIFIED_KILL records may grant authoritative streak credit. Standard
ADM death messages are useful for survivor names and clearing dead-zone presence,
but must not be counted a second time as verified kills.
"""
import re

NUM = r'-?\d+(?:\.\d+)?'
PLAYER = re.compile(
    r'Player "(?P<name>[^"\r\n]+)"(?:\s+\(DEAD\))?\s*'
    r'\(id=(?P<id>[^\s,)]+)\s+pos=<\s*(?P<x>' + NUM + r'),\s*'
    r'(?P<z>' + NUM + r'),\s*' + NUM + r'\s*>\)', re.I
)
CONNECT = re.compile(
    r'Player "(?P<name>[^"\r\n]+)"\s*\(id=(?P<id>[^\s,)]+)'
    r'(?:\s+pos=<[^>]+>)?\) is connected', re.I
)
KILL = re.compile(
    r'Player "(?P<victim>[^"\r\n]+)"(?:\s+\(DEAD\))?\s*'
    r'\(id=(?P<vid>[^\s,)]+).*?\)\s+(?:was )?killed by\s+'
    r'(?:Player\s+)?"(?P<killer>[^"\r\n]+)"\s*'
    r'\(id=(?P<kid>[^\s,)]+)', re.I
)
BCZ_POSITION = re.compile(
    r'\[BCZ\] POS id=(?P<id>[^\s]+) name="(?P<name>[^"\r\n]{1,80})" '
    r'x=(?P<x>' + NUM + r') z=(?P<z>' + NUM + r')', re.I
)
BCZ_BOUNDARY = re.compile(
    r'\[BCZ\] (?P<action>ENTER|EXIT) guid=(?P<id>[^\s]+) '
    r'zone=(?P<zone>[^\r\n]+)', re.I
)
BCZ_VERIFIED_KILL = re.compile(
    r'\[BCZ\] VERIFIED_KILL event=(?P<event>\d+) '
    r'kid=(?P<kid>[^\s]+) vid=(?P<vid>[^\s]+) '
    r'zone="(?P<zone>[^"\r\n]+)" streak=(?P<streak>\d+)', re.I
)
BCZ_GAME_REWARD = re.compile(
    r'\[BCZ\] REWARD grant=(?P<grant>\d+) id=(?P<id>[^\s]+) '
    r'tier=(?P<tier>\d+) status=(?P<status>delivered|reserved|disabled|dry_run|failed)', re.I
)


def parse(line):
    out = []
    kill = KILL.search(line)
    for m in PLAYER.finditer(line):
        # A deceased character's final position must never cause a new entry
        # alert. Preserve positions for live players, including the killer.
        if kill:
            continue
        out.append(('position', m.groupdict()))
    connect = CONNECT.search(line)
    if connect:
        out.append(('connect', connect.groupdict()))
    if kill:
        vals = kill.groupdict()
        people = {m.group('id'): m.groupdict() for m in PLAYER.finditer(line)}
        killer_pos = people.get(vals['kid'], {})
        victim_pos = people.get(vals['vid'], {})
        clock = re.match(r'^(\d{2}:\d{2}:\d{2})\s*\|', line)
        weapon_match = re.search(r'\bwith\s+(.+?)(?:\s+from\s+([\d.]+)\s+meters?)?\s*$', line, re.I)
        out.append(('death', {
            'id': vals['vid'], 'name': vals['victim'],
            'killer_id': vals['kid'], 'killer_name': vals['killer'],
            'x': killer_pos.get('x'), 'z': killer_pos.get('z'),
            'victim_x': victim_pos.get('x'), 'victim_z': victim_pos.get('z'),
            'clock': clock.group(1) if clock else '',
            'weapon': weapon_match.group(1).strip() if weapon_match else '',
            'distance': weapon_match.group(2) if weapon_match else None,
        }))
        out.append(('kill', vals))
    for expression, typ in (
        (BCZ_POSITION, 'position'),
        (BCZ_BOUNDARY, 'boundary'),
        (BCZ_VERIFIED_KILL, 'verified_kill'),
        (BCZ_GAME_REWARD, 'game_reward'),
    ):
        m = expression.search(line)
        if m:
            fields=m.groupdict()
            if typ=='verified_kill':
                clock=re.match(r'^(\d{2}:\d{2}:\d{2})\s*\|',line)
                fields['clock']=clock.group(1) if clock else ''
            out.append((typ, fields))
    return out
