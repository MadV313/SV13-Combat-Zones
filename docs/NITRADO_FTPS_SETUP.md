# SV13 Combat Zones — Nitrado FTP/FTPS reader patch

## What changed
- `badlands/ingest.py`: verified explicit TLS FTP (FTPS, port 21) with private encrypted data transfers, plus unchanged SSH/SFTP and local-file support. Selects most recent `.ADM` file and keeps existing persistent cursor logic.
- `.env.example`: documents the new `FTP_*` Railway variables. Never commit your credentials.
- `tests/test_ingest.py`: regression tests for secure FTPS access and ADM cursor processing.

## Railway variables (bot service → Variables)

| Name | Value |
|---|---|
| FTP_HOST | usny412.gamedata.io |
| FTP_PORT | 21 |
| FTP_USER | ni13528390_1 |
| FTP_PASSWORD | Your Nitrado **FTP** password — enter privately in Railway |
| FTP_DIRECTORY | /dayzstandalone/config **candidate; verify FTP account root** |
| FTP_FILE_SUFFIX | .ADM |

Keep `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `ADMIN_ROLE_ID`, `ANNOUNCE_CHANNEL_ID`, `DATABASE_PATH=/data/badlands.sqlite3`, `CONFIG_PATH=/data/zones.json`, `POLL_SECONDS=60`, and your `/data` Railway volume. Nothing needs changing in the DayZ server, trader configs or killfeed.

**Use a clean config:** Remove the *old Railway* `SFTP_HOST`, `SFTP_PORT`, `SFTP_USER`, `SFTP_PASSWORD`, `SFTP_DIRECTORY`, `SFTP_FILE_SUFFIX`, `SFTP_KNOWN_HOSTS` variable entries once you have migrated the values to `FTP_*`. These are Railway bot-service variables, NOT Nitrado server settings. A nonempty `FTP_HOST` takes precedence over SFTP, but removing stale entries reduces confusion. Do not set `ADM_LOCAL_PATH` unless a log is physically mounted into Railway's container.

Railway will redeploy after variables and GitHub source changes are applied. No public HTTP domain is required. Check Deploy Logs.

### If FTPS connection fails
- `550 ...` or directory not found: try `/config` for `FTP_DIRECTORY`. It depends on what Nitrado exposes as the FTP account's root. Check with WinSCP (FTP → TLS/SSL Explicit encryption).
- TLS/auth error or timeout: Nitrado's FTP endpoint may not support explicit TLS. **The reader intentionally never downgrades to unencrypted FTP.** It will require a secure ingestion bridge or an alternative authenticated log API; report the error before changing code.
- `No .adm files`: check the Nitrado profile directory and ensure an `.ADM` log exists. `.RPT` and `server.log` are not substitutes. ADM player list location events are periodic, not instantaneous.
- On the first successful read the reader starts the cursor at the end, to avoid paying out historical kills. New lines will be processed on subsequent polls.
- The `/health` command reports the last successfully initialized log cursor. Test `/health`, `/zones`, `/radarstats`. Confirm announcements only after real new ADM events.

### Safety and limitations
- FTPS verifies standard trusted certificate authorities and hostname, and encrypts the data connection with `PROT P`.
- This is still a **snapshot-based reader**, fetching the latest whole ADM file on each poll. Suitable to start with, but monitor bandwidth and log sizes.
- The original ADM event parser remains conservative and not validated against your actual Nasdara `.ADM` content. The bot cannot guarantee accurate rewards until a redacted sample is tested.
- No game-side reward spawning or live in-game announcements are claimed in this patch; uncompiled mod source remains unchanged.

Run tests locally: `python -m unittest discover -s tests -v`.
