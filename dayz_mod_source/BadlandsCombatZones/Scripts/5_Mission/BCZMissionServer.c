// SERVER-ONLY source preview. Compile/test using DayZ Tools before production.
modded class MissionServer
{
 protected ref BCZConfig m_BCZ_Config;
 protected ref map<string,string> m_BCZ_Presence;
 protected ref map<string,float> m_BCZ_LastExit;
 protected float m_BCZ_Accumulator;
 protected float m_BCZ_TelemetryAccumulator;

 override void OnInit()
 {
  super.OnInit();
  m_BCZ_Accumulator = 0;
  m_BCZ_TelemetryAccumulator = 0;
  m_BCZ_Presence = new map<string,string>;
  m_BCZ_LastExit = new map<string,float>;
  string folder = "$profile:BadlandsCombatZones";
  if (!FileExist(folder)) MakeDirectory(folder);
  string path = folder + "/zones.json";
  m_BCZ_Config = new BCZConfig();
  if (FileExist(path))
  {
   JsonFileLoader<BCZConfig>.JsonLoadFile(path, m_BCZ_Config);
   Print("[BCZ] Loaded combat zones from " + path);
  }
  else
  {
   JsonFileLoader<BCZConfig>.JsonSaveFile(path, m_BCZ_Config);
   Print("[BCZ] No zones configured; created empty template");
  }
 }

 protected string BCZ_FindZone(float x, float z, string current)
 {
  foreach (BCZSafeZone safe : m_BCZ_Config.safe_zones)
  {
   if (!safe) continue;
   float sx = x - safe.x;
   float sz = z - safe.z;
   if (sx*sx + sz*sz <= safe.radius*safe.radius) return "";
  }
  foreach (BCZZone zone : m_BCZ_Config.zones)
  {
   if (!zone || !zone.enabled) continue;
   float dx = x-zone.x;
   float dz = z-zone.z;
   float r = zone.radius;
   if (current == zone.name) r = r+10;
   else r = r-10;
   if (r < 0) r = 0;
   if (dx*dx+dz*dz <= r*r) return zone.name;
  }
  return "";
 }

 override void OnUpdate(float timeslice)
 {
  super.OnUpdate(timeslice);
  if (!GetGame().IsServer() || !m_BCZ_Config) return;
  m_BCZ_TelemetryAccumulator = m_BCZ_TelemetryAccumulator + timeslice;
  bool sendTelemetry = m_BCZ_TelemetryAccumulator >= 10.0;
  if (sendTelemetry) m_BCZ_TelemetryAccumulator = 0;
  m_BCZ_Accumulator = m_BCZ_Accumulator + timeslice;
  if (m_BCZ_Accumulator < 2.0) return;
  m_BCZ_Accumulator = 0;
  ref array<Man> players = new array<Man>;
  GetGame().GetPlayers(players);
  foreach (Man man : players)
  {
   PlayerBase player = PlayerBase.Cast(man);
   if (!player || !player.GetIdentity() || !player.IsAlive()) continue;
   string id = player.GetIdentity().GetId();
   if (id == "") continue;
   vector pos = player.GetPosition();
   if (sendTelemetry)
   {
    string pname = player.GetIdentity().GetName();
    pname.Replace("\"", "'");
    pname.Replace("\n", " ");
    pname.Replace("\r", " ");
    GetGame().AdminLog("[BCZ] POS id=" + id + " name=\"" + pname + "\" x=" + pos[0] + " z=" + pos[2]);
   }
   string oldZone = "";
   if (m_BCZ_Presence.Contains(id)) oldZone = m_BCZ_Presence.Get(id);
   string nextZone = BCZ_FindZone(pos[0],pos[2],oldZone);
   if (nextZone == oldZone) continue;
   m_BCZ_Presence.Set(id,nextZone);
   if (oldZone != "")
   {
    m_BCZ_LastExit.Set(id,GetGame().GetTime());
    NotificationSystem.SendNotificationToPlayerExtended(player,7.0,"COMBAT ZONE EXITED","You have left " + oldZone);
    GetGame().AdminLog("[BCZ] EXIT guid=" + id + " zone=" + oldZone);
   }
   if (nextZone != "")
   {
    NotificationSystem.SendNotificationToPlayerExtended(player,7.0,"COMBAT ZONE ENTERED","You are entering " + nextZone);
    float lastExit = -999999.0;
    if (m_BCZ_LastExit.Contains(id)) lastExit = m_BCZ_LastExit.Get(id);
    if ((GetGame().GetTime()-lastExit) > 300000.0)
    {
     NotificationSystem.SendNotificationToPlayerIdentityExtended(null,8.0,"COMBAT ZONE ACTIVITY","A survivor entered " + nextZone);
    }
    GetGame().AdminLog("[BCZ] ENTER guid=" + id + " zone=" + nextZone);
   }
  }
 }
};
