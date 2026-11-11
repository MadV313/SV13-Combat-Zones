"""Presentation-only Combat Zones Discord embed data.

Reuse the exact animated Discord emoji IDs from the 2025 RewardsBot's
sv_radar/callback_registrar.py and listradars.py. These are Discord-hosted
emoji, not image attachments; the bot/guild must have permission to render them.
No unverified Nasdara map URLs or guessed player coordinates are emitted.
"""
import re

RADAR = '<a:radar:1381409288160936116>'
FROST = '<a:ezgif:1385822657852735499>'
ZONE_ON = '<a:on:1388954436738617565>'


def safe(text):
    """Limit user-controlled display text and avoid mention / Markdown abuse."""
    value = str(text or 'Unknown')[:90]
    value = value.replace('@', '@\u200b').replace('`', "'")
    return re.sub(r'([\\*_~|>])', r'\\\1', value)


def make(kind, payload, zones):
    """Return ordinary Python data; bot.py converts it to discord.Embed."""
    zone_name = safe(payload.get('zone', 'Unknown zone'))
    who = safe(payload.get('name', 'Survivor'))
    zone = next((z for z in zones if z.get('name') == payload.get('zone')), None)
    fields = []
    if zone:
        fields.append(('📍 Zone reference',
            f'`X {float(zone["x"]):.0f} · Z {float(zone["z"]):.0f}` (zone center)', True))
        fields.append(('📐 Zone radius', f'`{int(zone["radius"])} m`', True))
    if kind == 'entry':
        return dict(title=f'{RADAR} COMBAT ZONE — CONTACT',
            description=f'{ZONE_ON} **{who}** has entered **{zone_name}**.\nStay frosty, survivors! {FROST}',
            color=0x00FF99, fields=fields,
            footer='Server-confirmed combat-zone entry')
    if kind == 'exit':
        return dict(title=f'{RADAR} COMBAT ZONE — DEPARTURE',
            description=f'**{who}** has moved beyond the perimeter of **{zone_name}**.',
            color=0x607D8B, fields=fields,
            footer='Server-confirmed boundary exit · Death is not an exit')
    if kind == 'kill':
        killer = safe(payload.get('killer'))
        victim = safe(payload.get('victim'))
        streak = int(payload.get('streak', 1))
        fields += [('💀 Confirmed elimination', f'**{killer}** → **{victim}**', False),
                   ('🔥 Active streak', f'**{streak}** credited kill' + ('' if streak == 1 else 's'), True)]
        if payload.get('x') is not None and payload.get('z') is not None:
            fields.append(('🎯 Verified kill location',
                           f'`X {float(payload["x"]):.1f} · Z {float(payload["z"]):.1f}`', False))
        if payload.get('weapon'):
            fields.append(('🔫 Weapon (ADM)', safe(payload['weapon']), True))
        if payload.get('distance'):
            fields.append(('📏 Distance (ADM)', f'`{float(payload["distance"]):.1f} m`', True))
        if streak >= 10:
            status = f'**ZONE REAPER** — {killer} has reached **{streak}** kills!'
            color = 0xBD2233
        elif streak >= 5:
            status = f'**ZONE REAPER** — {killer} is on a **{streak}-kill streak**!'
            color = 0xE4572E
        elif streak >= 3:
            status = f'**ON A RAMPAGE** — {killer} has **{streak}** consecutive credited kills.'
            color = 0xF5A623
        elif streak == 2:
            status = f'**DOUBLE ELIMINATION** — {killer} has started a streak.'
            color = 0xE9AD43
        else:
            status = f'**{killer}** eliminated **{victim}** in **{zone_name}**.'
            color = 0x00FF99
        return dict(title=f'{RADAR} COMBAT ZONE — KILL CONFIRMED',
            description=f'⚔️ {status}\n{FROST}', color=color, fields=fields,
            footer='Server-verified PvP · Repeat-victim cooldown enforced')
    if kind == 'reward':
        tier = int(payload.get('tier', 0))
        return dict(title='🏆 COMBAT ZONE — REWARD MILESTONE',
            description=f'**{who}** reached **{tier} credited kills**. Reward is pending in the legacy queue; this is not proof of item delivery.',
            color=0xD9A441, fields=fields, footer='Pending reward · Not a physical delivery receipt')
    if kind == 'game_reward':
        tier = int(payload.get('tier', 0))
        return dict(title='🏆 COMBAT ZONE — REWARD DELIVERED',
            description=f'**{who}** earned an in-game reward crate for **{tier} credited kills**.',
            color=0x00FF99, fields=fields, footer='Server-confirmed physical reward receipt')
    return None
