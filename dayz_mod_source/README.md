# DayZ mod source (NOT A COMPILED MOD)

This is DayZ Enforce Script source for zone entry/exit and global alerts. It is NOT a ready-to-install PBO and has not been built/tested against the particular DayZ server/mod stack.

## Before use
1. Compile with DayZ Tools / Addon Builder using `BadlandsCombatZones` as the correct PBO prefix. Validate scripts on a **staging** DayZ PC server.
2. Place the compiled addon in `@BadlandsCombatZones/Addons/`, create/sign a key using your usual mod-signing process, and configure `-mod=` on the **server and client** as appropriate. A notification-only server-only implementation may be possible after validating load constraints; do not claim that this source is already a server-only PBO.
3. Put the `/exportzones` JSON from Discord into your server profile at `$profile:BadlandsCombatZones/zones.json`. Restart to reload.
4. Turn on `-adminlog`. The mod emits `[BCZ]` enter/exit markers for audit.
5. Test trader protection, joining inside a zone, reconnecting, multiple players, and boundary jitter. Safe-zone list includes the provided 150 m armor trader marker only. Add any additional protected traders.

## Not yet implemented in the game-side source
- Reward crate spawning and claims; the Discord bot records pending achievements only. Do not award physical items until safe class-name verification, delivery strategy, permissions, and deduplication bridge are finished.
- In-game kill detection/instant killstreak notifications. Discord parses PC ADM events conservatively but does not control DayZ scripts in real time.
- Mod compile/sign and final client/server compatibility tests.

## Safe physical spawning approach
After testing with the DayZ API, implement a server-authoritative reward dispatcher using `GetGame().CreateObjectEx(classname, validatedPosition, ECE_PLACE_ON_SURFACE)` or equivalent for *validated* server classname, add cargo via inventory APIs, and persist claim IDs **before** spawning. Never trust a Discord bot message as an unrestricted spawn command; accept only signed, single-use grants linked to verified platform GUIDs and limit to allowed classes/tier quantities.
