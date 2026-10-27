# Badlands Combat Zones — Nasdara PC

**Standalone Discord bot + staging-only DayZ mod source.** Based on review of `Rewards-bot-main(2).zip` (`sv_radar`) and `SV-Bounties-main(3).zip` (`tracer`). Reimplemented rather than copying legacy Xbox config/secrets/economy. Does not change the existing killfeed PBO or trader configs.

## Delivered status

| Feature | Status |
|---|---|
| Discord zone create/remove/toggle/list/export | Implemented |
| SQLite DB and persistent ADM cursor | Implemented |
| PC ADM SFTP/local poll and parsing | Implemented; validate with actual Nasdara ADM samples |
| Zone player entry and kill tracking | Implemented for recognized log formats; ADM positions may be 5+ min delayed |
| Discord zone leaderboards / pending streak awards | Implemented; no real in-game spawning yet |
| Admin UAV last-known-positions map | Implemented; needs calibrated Nasdara image + dimensions |
| Live DayZ zone entry/exit/global alerts | Uncompiled mod source preview; staging verification required |
| Physical reward spawn / claim | **Not yet implemented** — pending rewards queued safely |
| Weekly/monthly top-assassin automated prize issuance | **Not yet implemented** (stats foundation present) |
| Old faction economy, UAV countermeasures | Not migrated (no old wallet needed) |

## Deploy Discord bot
1. Create a NEW Discord application/bot. Invite with `bot` and `applications.commands`, with View Channel, Send Messages, Attach Files. Don't reuse secrets from either legacy repo.
2. New GitHub repo: upload all these files (NOT the old .env files). Railway -> New Project -> Deploy from GitHub. `Dockerfile` handles installation. Add persistent Railway volume mounted at `/data`.
3. Copy `.env.example` values into Railway Variables. Set `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `ADMIN_ROLE_ID` (optional if Manage Server), `ANNOUNCE_CHANNEL_ID`, and ideally SFTP credentials.
4. Set `SFTP_KNOWN_HOSTS` to a mounted verified SSH host-keys file before enabling SFTP. This prevents silent machine-in-the-middle acceptance. Or use `ADM_LOCAL_PATH` for testing where the logs are mounted.
5. Obtain the real PC ADM path and verify `-adminlog` and `adminLogPlayerList = 1;` in `serverDZ.cfg`. **No current PC ADM log was attached.** Verify your host exposes SFTP, not FTP-only; the reader intentionally does not support plaintext FTP. If only FTP is available, implement a secure ingestion bridge first.
6. Start once to initialize ingest cursor at end of latest log, then trigger NEW events. Old kills are intentionally not backfilled.
7. `/setzone` X/Z from Nasdara world; `/zones`, `/togglezone`, `/radarstats`, `/pendingrewards`, `/health`, `/exportzones`, `/uav`.

## Game-side alerts
Source in `dayz_mod_source/` has a `MissionServer.OnUpdate` 2-second location check and standard DayZ notification API. It has not been compiled into a PBO and requires validation before use on a live Nitrado server. Exported JSON must be copied to the DayZ profiles folder; there is no automatic Discord-to-game synchronization yet.

## Reward settings
Edit `CONFIG_PATH` (`/data/zones.json`) as needed. Rewards are queued in the SQLite DB after an accepted kill event. This is not an inventory system and never silently spawns items. The supplied Paragon armor trader catalogue informed provisional item classnames, but each must be confirmed installed on the PC server. Avoid valuable payouts until parser validation and anti-exploit checks.

## Critical limitations
- PC ADM example formats vary by server/version. Exact killer/victim GUIDs are required; unrecognized events are **not credited**, rather than guessing.
- ADM position snapshots every 5 minutes cannot prove both parties were inside a zone at the precise time of a kill. In-game authoritative kill hooks are required before serious rewards go live.
- Kill dedup based on full identical lines works for retried lines but distinct identical events still need unique authoritative event IDs. Historical leaderboard backfill is not built.
- Position data is sensitive. `/uav` requires admin rights and fresh cached positions; this is not a public wallhack feed.
- Trader Safezone from provided `TraderObjects(5).txt`: marker ID 7 at X=8342.02, Z=7806.61 radius 150m; other markers are radius zero. Add any other protected locations yourself. The supplied KOTH mod/source was not available.
- Old uploaded `.env` and configs may contain secrets; none were copied into this repo. Rotate any credentials if previously published.

## Tests
`python -m unittest discover -s tests -v`

## Source references used to plan the mod
- https://community.bohemia.net/wiki/DayZ:Administration_Logs
- https://community.bohemia.net/wiki/DayZ:Modding_Structure
- https://diff.yadz.app/files/3_Game/Client/Notifications/NotificationSystem.c/

## Future integrations (not claimed complete)
- Verify authoritative server-side kill hooks, anti-farming/alt-account checks, safe rewards, offline claims, admin grant/revoke logs.
- Implement durable signed event/grant bridge (secure scheduled file exchange or authenticated endpoint), server-side spawn/claim, weekly/monthly standings, map calibration, timed UAV scans and counter-UAV features.
