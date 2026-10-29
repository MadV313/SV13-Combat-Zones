// SV13 Combat Zones: game-side reward data. No Discord account is required.
class BCZRewardTier
{
 int streak;
 string container;
 ref array<string> items;
 void BCZRewardTier()
 {
  items = new array<string>;
 }
};
class BCZRewardConfig
{
 bool physical_rewards_enabled;
 bool dry_run;
 int max_items_per_crate;
 float max_terrain_height_difference;
 int same_victim_cooldown_ms;
 ref array<ref BCZRewardTier> tiers;
 void BCZRewardConfig()
 {
  physical_rewards_enabled = false;
  dry_run = true;
  max_items_per_crate = 5;
  max_terrain_height_difference = 2.5;
  same_victim_cooldown_ms = 300000;
  tiers = new array<ref BCZRewardTier>;
 }
};
class BCZPlayerStreak
{
 string id;
 int streak;
};
class BCZRewardReceipt
{
 int grant_id;
 string player_id;
 string victim_id;
 int streak;
 string zone;
 string status; // reserved, delivered, failed, dry_run, disabled
};
class BCZRewardState
{
 int next_grant_id;
 int next_kill_event_id;
 ref array<ref BCZPlayerStreak> players;
 ref array<ref BCZRewardReceipt> grants;
 void BCZRewardState()
 {
  next_grant_id = 1;
  next_kill_event_id = 1;
  players = new array<ref BCZPlayerStreak>;
  grants = new array<ref BCZRewardReceipt>;
 }
};
