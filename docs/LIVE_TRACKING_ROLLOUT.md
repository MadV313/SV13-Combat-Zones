# Live zone tracking rollout (development / staging only)

## Included in this patch
- Preserves the existing Nitrado FTPS reader, Discord commands and SQLite schema.
- Accepts `[BCZ] POS id=... name="..." x=... z=...` emitted by the supplied DayZ server-side mod source.
- Game-side position telemetry targets 10 seconds, while entry/exit checks remain 2 seconds. Log transfer and Railway polling add latency.
- Player name and game identity are stored automatically whether or not they have a Discord account. `/radarstats` and `/playerstats` work for unlinked players.
- `/setpositionage` configures maximum eligible position age (recommended 45s **only after** mod telemetry is confirmed).

## Do not mistake for completed deployment
The updated Enforce Script is **source**, not a compiled or tested PBO. It must be compiled, signed and tested with the running DayZ version/mod stack before live installation. Merely deploying the Discord ZIP to Railway does not cause 10-second telemetry. The existing Nitrado `Log Playerlist` setting stays unchanged.

## Safe rollout
1. Replace only the included GitHub files; Railway deploys as before. Do not overwrite `/data/zones.json` or `/data/badlands.sqlite3` on the Railway volume.
2. `/health`, `/zones`, `/radarstats` and `/playerstats` should work as before. The default stays at the original 360 seconds until the DayZ mod has been compiled and tested. Then run `/setpositionage seconds:45` to tighten kill qualification.
3. Export `/exportzones` to obtain the authoritative active zones (including ComeGetSome). Test mod source on a staging DayZ server before installing it on the live server.
4. Once the mod is tested, watch the **ADM file** for `[BCZ] POS` markers; check name, GUID and coordinates.
5. Set `POLL_SECONDS=15` in Railway **only after** measured traffic and rate limits allow; 15s FTPS polling still does not guarantee instant Discord updates.
6. Run a test entry, exit, two-player PvP event, and repeated log read; verify no duplicate rewards and no safe-zone false positives.

## Rewards and identity
No player needs Discord to appear in rankings or to have a pending prize record. `/linkplayer` is optional and currently admin-managed. `GetIdentity().GetId()` is a game-provided identity, **not necessarily Steam64**; don't label it Steam64 until independently mapped/verified. Physical item spawning, offline claims, authoritative kill hooks, scheduled champion awards, and automatic Discord-to-game reward delivery are **not implemented** here. Pending prizes stay pending; do not manually mark delivered without proof.

## Security
The FTPS endpoint remains certificate-verified. Do not use unencrypted FTP or disable TLS certificate validation. Do not expose UAV locations or raw player identifiers in public channels.
