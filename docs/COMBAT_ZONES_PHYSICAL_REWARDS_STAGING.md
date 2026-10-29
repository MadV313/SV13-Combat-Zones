# SV13 Combat Zones - DayZ rewards staging / KOTH-based design

## What was audited

- Current uploaded `SV13-Combat-Zones-main(2).zip` is a 44-entry Python+DayZ-source repo. Existing FTPS ingest, bot commands, DB and original zone/radar logic preserved, with the new files/modified files listed here.
- Supplied MZ KOTH PBO creates a configurable reward chest with `CreateObject`, sets its orientation, and adds random configured inventory/attachments via the inventory APIs. KOTH itself remains untouched.
- This patch implements its own game-side **server-authoritative killstreak rewards**, without requiring that KOTH be installed. Game players need no Discord account.

## Added/updated files in this patch

- `dayz_mod_source/BadlandsCombatZones/config.cpp`: load 4_World script layer for player-death hooks.
- `dayz_mod_source/BadlandsCombatZones/Scripts/3_Game/BCZRewards.c` (new): reward tiers, receipt, persisted player streak types.
- `dayz_mod_source/BadlandsCombatZones/Scripts/4_World/BCZDeathQueue.c` (new): safe 4_World-to-5_Mission death event queue.
- `dayz_mod_source/BadlandsCombatZones/Scripts/4_World/BCZPlayerDeath.c` (new): conservative player-vs-player attribution; no reward for invalid/no killer.
- `dayz_mod_source/BadlandsCombatZones/Scripts/5_Mission/BCZMissionServer.c`: existing alert/telemetry and zone logic, with server-verified PvP streaks and physical crate grants.
- `config/rewards.staging.example.json` (new): conservative, safe default rewards.
- `badlands/adm.py`, `badlands/engine.py`, `badlands/db.py`, `bot.py`, `.env.example`: opt-in authoritative kill/receipt ingest; retains legacy behavior when disabled.
- `tests/test_authoritative_game_events.py` (new): dedupe, no bot/server double count, reward receipt tests.

## Ownership / safety model

- DayZ server observes player deaths and recent player damage. A null/environmental/suicide death, non-verified killer, or zone mismatch is not a qualifying PvP kill.
- Player names and IDs are captured from DayZ itself; Discord is OPTIONAL for participation, stats and physical rewards. `GetIdentity().GetId()` is a game-server identity value, **not automatically a Steam64 ID**.
- When a streak crosses a configured threshold (default 3/5/10), the server writes a receipt to `$profile:BadlandsCombatZones/reward_state.json` **before** spawning. A crash after reservation can leave a `reserved` receipt; no automatic replays are allowed. Investigate manually; don't erase this state.
- Physical delivery is disabled and dry-run by default. The admin must choose to enable only after testing. Run with `physical_rewards_enabled=true, dry_run=true` first for simulation logs. Actual spawns need both `physical_rewards_enabled=true, dry_run=false`.
- When enabled, spawn is allowed only if a whitelisted configured type exists and a terrain-height/zone check succeeds. It spawns a container adjacent to the killer using `ECE_PLACE_ON_SURFACE` and adds allowed cargo through `CreateInInventory` (same general pattern as KOTH, different implementation).
- Failed/partial delivery is recorded; no automatic retry. Admin must inspect both crate and receipt. A partially filled crate counts delivered if at least one item spawned (log/verify your actual content).
- Same killer/victim pair has a default five-minute cooldown (game-session only); repeat farming won't generate multiple streak credits in that interval.
- 3/5/10 milestone reward arrays are independent of the Discord bot's existing pending rewards; activating authoritative ingest avoids duplicate bot-created `pending` claims for game-side prizes.
- **Weekly/monthly Top Assassin automatic award/claim, offline redemption, cross-restart anti-farm timestamps, and admin recovery commands are NOT implemented by this patch.** They require a signed or otherwise authenticated grant/claim bridge; do NOT assume `/pendingrewards` triggers item spawning.

## Build / staging steps

1. Keep the full original repo. Copy only these patched files into matching relative paths, commit to GitHub. Railway may redeploy; with `BCZ_AUTHORITATIVE_KILLS=0` (default), the current ADM statistics behavior is unchanged.
2. Do not change the existing FTPS/Discord/Railway credentials. Preserve the working Nitrado server startup, traders, killfeed and other mods.
3. Copy `dayz_mod_source/BadlandsCombatZones` onto your DayZ Tools P: drive with a proper `BadlandsCombatZones` addon prefix. Package using DayZ Tools Addon Builder. Source is **not a compiled PBO**.
4. Staging server: add the compiled `@BadlandsCombatZones` addon to the existing `-serverMod` list if this implementation passes server-only loading, and keep your preexisting `-mod` / `-serverMod` entries. No client-side scripts/RPC are defined here, but client compatibility still needs in-game testing.
5. Export `/exportzones` in Discord. Copy `zones.json` to `$profile:BadlandsCombatZones/zones.json`. Confirm that `ComeGetSome` X=4154 Z=5382 radius=200m is present, and that trader safe zones are correct. **The live-server config is not auto-synced with Discord.**
6. On first mod boot, the server creates `$profile:BadlandsCombatZones/rewards.json` with `physical_rewards_enabled=false` and `dry_run=true`. Verify this against `config/rewards.staging.example.json` and back it up.
7. Conduct entry/exit/reconnect tests and verify actual 10s `[BCZ] POS` lines in the ADM, then test PvP while all rewards remain disabled. `[BCZ] VERIFIED_KILL event=... kid=... vid=... zone="ComeGetSome" streak=N` must appear. Check any game script errors in RPT/script logs.
8. For an isolated maintenance test, set `physical_rewards_enabled=true`, `dry_run=true` in rewards.json, restart, score a legitimate 3-kill streak (or adjust the threshold in the staging copy), and verify `[BCZ] REWARD ... status=dry_run` plus persisted receipt. Multiple kills of the **same victim** inside 5 minutes do not increment streak.
9. With the test server isolated from public economy, set `physical_rewards_enabled=true`, `dry_run=false`, restart, use harmless test items first, and confirm physical crate, contents, elevation, and single delivery. Do not use rare items until verified; do not test public server with live spawning enabled.
10. After the server emits verified unique kills and reward receipts, set Railway `BCZ_AUTHORITATIVE_KILLS=1`; redeploy once. This switches the bot from legacy `killed by` text crediting to authoritative `VERIFIED_KILL` events; it ingests `[BCZ] REWARD` audit records separately. Test `/health`, `/radarstats`, `/playerstats`, `/gamerewards`. Leave it 0 if no compiled mod is running.

## Rollback / recovery

- Revert only the `@BadlandsCombatZones` entry from the existing `-serverMod` arguments; do not erase any other mods.
- Set `BCZ_AUTHORITATIVE_KILLS=0` in Railway when returning to the old ADM kill model.
- Back up `$profile:BadlandsCombatZones/rewards.json`, `reward_state.json`, and `zones.json`; **never delete reward_state.json merely to repeat a test** (grant IDs and streak data would reset).
- Duplicate or failed receipt: inspect RPT, ADM, crate content and `reward_state.json`; do not auto-retry `reserved` grants. Resolve manually.

## Compiler caveat

The Python tests are runnable here, but Enforce Script must be compiled with Windows DayZ Tools and tested with your actual Nasdara game/mod stack. Dependencies, behavior of another killfeed mod's `EEHitBy` hooks, and item/container space may require adjustments after actual script/compiler logs. No test here proves that the PBO loads or items actually spawn in DayZ.
