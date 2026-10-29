// SV13 Combat Zones - staged server-only runtime. DayZ Tools compilation required.
// Physical rewards OFF and DRY-RUN by default. Does not depend on Discord identity.
modded class MissionServer
{
 protected ref BCZConfig m_BCZ_Config;
 protected ref BCZRewardConfig m_BCZ_Rewards;
 protected ref BCZRewardState m_BCZ_State;
 protected ref map<string,string> m_BCZ_Presence;
 protected ref map<string,float> m_BCZ_LastExit;
 protected ref map<string,float> m_BCZ_PairLastKill;
 protected float m_BCZ_Accumulator;
 protected float m_BCZ_TelemetryAccumulator;

 override void OnInit()
 {
  super.OnInit();
  if (!GetGame().IsServer()) return;
  m_BCZ_Accumulator = 0;
  m_BCZ_TelemetryAccumulator = 0;
  m_BCZ_Presence = new map<string,string>;
  m_BCZ_LastExit = new map<string,float>;
  m_BCZ_PairLastKill = new map<string,float>;
  string folder = "$profile:BadlandsCombatZones";
  if (!FileExist(folder)) MakeDirectory(folder);
  m_BCZ_Config = new BCZConfig();
  string path = folder + "/zones.json";
  if (FileExist(path))
  {
   JsonFileLoader<BCZConfig>.JsonLoadFile(path,m_BCZ_Config);
   Print("[BCZ] Loaded zones from " + path);
  }
  else
  {
   JsonFileLoader<BCZConfig>.JsonSaveFile(path,m_BCZ_Config);
   Print("[BCZ] Zones file absent; created empty template. Nothing active.");
  }
  if (!m_BCZ_Config || !m_BCZ_Config.zones || !m_BCZ_Config.safe_zones)
  {
   Print("[BCZ] Invalid zones.json; zone system disabled for safety");
   m_BCZ_Config = null;
  }
  BCZ_LoadRewards(folder);
 }

 protected void BCZ_LoadRewards(string folder)
 {
  m_BCZ_Rewards = new BCZRewardConfig();
  string configPath = folder + "/rewards.json";
  if (FileExist(configPath))
  {
   JsonFileLoader<BCZRewardConfig>.JsonLoadFile(configPath,m_BCZ_Rewards);
  }
  else
  {
   BCZRewardTier medical = new BCZRewardTier();
   medical.streak=3; medical.container="SeaChest";
   medical.items.Insert("BandageDressing");medical.items.Insert("Morphine");
   BCZRewardTier armor = new BCZRewardTier();
   armor.streak=5;armor.container="SeaChest";
   armor.items.Insert("Paragon_IOTV_Black");
   BCZRewardTier rare = new BCZRewardTier();
   rare.streak=10;rare.container="SeaChest";
   rare.items.Insert("SVD");
   m_BCZ_Rewards.tiers.Insert(medical);
   m_BCZ_Rewards.tiers.Insert(armor);
   m_BCZ_Rewards.tiers.Insert(rare);
   JsonFileLoader<BCZRewardConfig>.JsonSaveFile(configPath,m_BCZ_Rewards);
  }
  if (!m_BCZ_Rewards || !m_BCZ_Rewards.tiers)
  {
   m_BCZ_Rewards = new BCZRewardConfig();
   Print("[BCZ] Invalid reward config: disabled physical prizes");
  }
  if (m_BCZ_Rewards.max_items_per_crate < 1 || m_BCZ_Rewards.max_items_per_crate > 10)
  {
   m_BCZ_Rewards.physical_rewards_enabled = false;
   Print("[BCZ] Invalid item cap; rewards disabled");
  }
  if (m_BCZ_Rewards.max_terrain_height_difference <= 0 || m_BCZ_Rewards.max_terrain_height_difference > 5)
  {
   m_BCZ_Rewards.physical_rewards_enabled = false;
   Print("[BCZ] Invalid terrain safety threshold; rewards disabled");
  }
  string statePath = folder + "/reward_state.json";
  m_BCZ_State = new BCZRewardState();
  if (FileExist(statePath)) JsonFileLoader<BCZRewardState>.JsonLoadFile(statePath,m_BCZ_State);
  if (!m_BCZ_State || !m_BCZ_State.players || !m_BCZ_State.grants)
  {
   Print("[BCZ] Invalid reward_state.json! Turning OFF physical rewards; preserve state backup before repair");
   m_BCZ_State = new BCZRewardState();
   m_BCZ_Rewards.physical_rewards_enabled = false;
  }
  if (m_BCZ_State.next_grant_id < 1) m_BCZ_State.next_grant_id = 1;
  if (m_BCZ_State.next_kill_event_id < 1) m_BCZ_State.next_kill_event_id = 1;
  Print("[BCZ] Reward init: enabled=" + m_BCZ_Rewards.physical_rewards_enabled + " dry_run=" + m_BCZ_Rewards.dry_run);
 }

 protected void BCZ_SaveState()
 {
  if (!m_BCZ_State) return;
  JsonFileLoader<BCZRewardState>.JsonSaveFile("$profile:BadlandsCombatZones/reward_state.json",m_BCZ_State);
 }

 protected string BCZ_FindZone(float x,float z,string current)
 {
  if (!m_BCZ_Config) return "";
  foreach (BCZSafeZone safe:m_BCZ_Config.safe_zones)
  {
   if (!safe || safe.radius <= 0) continue;
   float sx=x-safe.x;float sz=z-safe.z;
   if(sx*sx+sz*sz<=safe.radius*safe.radius) return "";
  }
  foreach (BCZZone zone:m_BCZ_Config.zones)
  {
   if (!zone || !zone.enabled || zone.radius <= 10) continue;
   float dx=x-zone.x;float dz=z-zone.z;
   float r=zone.radius;
   if (current == zone.name) r=r+10;else r=r-10;
   if(dx*dx+dz*dz<=r*r) return zone.name;
  }
  return "";
 }

 protected BCZPlayerStreak BCZ_GetStreak(string id)
 {
  foreach (BCZPlayerStreak state:m_BCZ_State.players)
   if (state && state.id == id) return state;
  BCZPlayerStreak fresh=new BCZPlayerStreak();
  fresh.id=id;fresh.streak=0;m_BCZ_State.players.Insert(fresh);
  return fresh;
 }

 protected BCZRewardTier BCZ_GetTier(int streak)
 {
  foreach (BCZRewardTier tier:m_BCZ_Rewards.tiers)
   if (tier && tier.streak == streak) return tier;
  return null;
 }

 protected void BCZ_HandleDeath(BCZDeathRecord death)
 {
  if (!death || !m_BCZ_State || !m_BCZ_Rewards || !m_BCZ_Config) return;
  if (death.victimId == "") return;
  BCZ_GetStreak(death.victimId).streak = 0;
  BCZ_SaveState();
  m_BCZ_Presence.Remove(death.victimId);
  if (death.killerId == "" || death.killerId == death.victimId) return;
  string zone=BCZ_FindZone(death.killerPosition[0],death.killerPosition[2],"");
  string victimZone=BCZ_FindZone(death.victimPosition[0],death.victimPosition[2],"");
  if (zone == "" || victimZone != zone) return;
  string pair=death.killerId + ":" + death.victimId;
  float now=GetGame().GetTime();
  float last=-999999999.0;
  if (m_BCZ_PairLastKill.Contains(pair)) last=m_BCZ_PairLastKill.Get(pair);
  int cooldown=m_BCZ_Rewards.same_victim_cooldown_ms;
  if (cooldown < 0) cooldown = 300000;
  if (now-last < cooldown)
  {
   Print("[BCZ] Repeated-victim kill ignored for streak credit");
   return;
  }
  m_BCZ_PairLastKill.Set(pair,now);
  BCZPlayerStreak killerState=BCZ_GetStreak(death.killerId);
  killerState.streak=killerState.streak+1;
  int streak=killerState.streak;
  int eventId=m_BCZ_State.next_kill_event_id;
  m_BCZ_State.next_kill_event_id=eventId+1;
  BCZ_SaveState();
  // Unique server-generated event sequence for deduplication on the Discord side.
  string zoneSafe=zone;
  zoneSafe.Replace("\"","'");
  GetGame().AdminLog("[BCZ] VERIFIED_KILL event=" + eventId + " kid=" + death.killerId + " vid=" + death.victimId + " zone=\"" + zoneSafe + "\" streak=" + streak);
  BCZRewardTier tier=BCZ_GetTier(streak);
  if (tier) BCZ_GrantReward(death,tier,zone,streak);
 }

 protected void BCZ_GrantReward(BCZDeathRecord death,BCZRewardTier tier,string zone,int streak)
 {
  BCZRewardReceipt receipt=new BCZRewardReceipt();
  receipt.grant_id=m_BCZ_State.next_grant_id;
  m_BCZ_State.next_grant_id=m_BCZ_State.next_grant_id+1;
  receipt.player_id=death.killerId;
  receipt.victim_id=death.victimId;
  receipt.streak=streak;
  receipt.zone=zone;
  // Reserve in durable profile state BEFORE attempting an item spawn.
  receipt.status="reserved";
  m_BCZ_State.grants.Insert(receipt);
  BCZ_SaveState();

  if (!m_BCZ_Rewards.physical_rewards_enabled)
  {
   receipt.status="disabled";
  }
  else if (m_BCZ_Rewards.dry_run)
  {
   receipt.status="dry_run";
  }
  else
  {
   receipt.status="failed";
   if (tier && tier.items && tier.items.Count()>0 && tier.items.Count()<=m_BCZ_Rewards.max_items_per_crate)
   {
    // Refuse to place gear under buildings or distant from actual ground.
    vector ground=death.killerPosition;
    ground[0]=ground[0]+1.5;
    ground[2]=ground[2]+1.5;
    ground[1]=GetGame().SurfaceY(ground[0],ground[2]);
    float heightDelta=Math.AbsFloat(death.killerPosition[1]-ground[1]);
    if(heightDelta <= m_BCZ_Rewards.max_terrain_height_difference && BCZ_FindZone(ground[0],ground[2],"") == zone)
    {
     if (GetGame().ConfigIsExisting("CfgVehicles " + tier.container))
     {
      EntityAI crate=EntityAI.Cast(GetGame().CreateObjectEx(tier.container,ground,ECE_PLACE_ON_SURFACE));
      if (crate)
      {
       int created=0;
       foreach(string classname:tier.items)
       {
        if (GetGame().ConfigIsExisting("CfgVehicles " + classname))
        {
         if (crate.GetInventory().CreateInInventory(classname)) created=created+1;
        }
        else Print("[BCZ] Reward class missing: " + classname);
       }
       if (created > 0)
       {
        crate.SetLifetime(1800);
        receipt.status="delivered";
       }
       else crate.Delete();
      }
     }
    }
    else Print("[BCZ] Reward blocked: ground-height or zone safety check failed");
   }
  }
  BCZ_SaveState();
  GetGame().AdminLog("[BCZ] REWARD grant=" + receipt.grant_id + " id=" + receipt.player_id + " tier=" + streak + " status=" + receipt.status);
 }

 override void OnUpdate(float timeslice)
 {
  super.OnUpdate(timeslice);
  if (!GetGame().IsServer() || !m_BCZ_Config) return;
  // PlayerBase deaths are captured in 4_World then processed in this 5_Mission layer.
  BCZDeathRecord death=BCZDeathQueue.Pop();
  int processed=0;
  while (death && processed<100)
  {
   BCZ_HandleDeath(death);
   processed=processed+1;
   death=BCZDeathQueue.Pop();
  }
  m_BCZ_TelemetryAccumulator=m_BCZ_TelemetryAccumulator+timeslice;
  bool sendTelemetry=m_BCZ_TelemetryAccumulator>=10.0;
  if (sendTelemetry) m_BCZ_TelemetryAccumulator=0;
  m_BCZ_Accumulator=m_BCZ_Accumulator+timeslice;
  if (m_BCZ_Accumulator<2.0) return;
  m_BCZ_Accumulator=0;
  ref array<Man> players=new array<Man>;
  GetGame().GetPlayers(players);
  ref map<string,bool> currentlyOnline=new map<string,bool>;
  foreach(Man man:players)
  {
   PlayerBase player=PlayerBase.Cast(man);
   if (!player || !player.GetIdentity() || !player.IsAlive()) continue;
   string id=player.GetIdentity().GetId();
   if(id=="")continue;
   currentlyOnline.Set(id,true);
   vector pos=player.GetPosition();
   if(sendTelemetry)
   {
    string name=player.GetIdentity().GetName();
    name.Replace("\"","'");name.Replace("\n"," ");name.Replace("\r"," ");
    GetGame().AdminLog("[BCZ] POS id="+id+" name=\""+name+"\" x="+pos[0]+" z="+pos[2]);
   }
   string previous="";
   if(m_BCZ_Presence.Contains(id))previous=m_BCZ_Presence.Get(id);
   string current=BCZ_FindZone(pos[0],pos[2],previous);
   if(current==previous)continue;
   m_BCZ_Presence.Set(id,current);
   if(previous!="")
   {
    m_BCZ_LastExit.Set(id,GetGame().GetTime());
    NotificationSystem.SendNotificationToPlayerExtended(player,7.0,"COMBAT ZONE EXITED","You have left "+previous);
    GetGame().AdminLog("[BCZ] EXIT guid="+id+" zone="+previous);
   }
   if(current!="")
   {
    NotificationSystem.SendNotificationToPlayerExtended(player,7.0,"COMBAT ZONE ENTERED","You are entering "+current);
    float last=-999999999.0;
    if(m_BCZ_LastExit.Contains(id))last=m_BCZ_LastExit.Get(id);
    if(GetGame().GetTime()-last>300000.0)
     NotificationSystem.SendNotificationToPlayerIdentityExtended(null,8.0,"COMBAT ZONE ACTIVITY","A survivor entered "+current);
    GetGame().AdminLog("[BCZ] ENTER guid="+id+" zone="+current);
   }
  }
  // Remove disconnected players rather than leaving ghost combat-zone sessions.
  for(int i=m_BCZ_Presence.Count()-1;i>=0;i=i-1)
  {
   string guid=m_BCZ_Presence.GetKey(i);
   if(!currentlyOnline.Contains(guid))m_BCZ_Presence.Remove(guid);
  }
 }
};
