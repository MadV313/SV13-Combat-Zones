// Mission script modules cannot be referenced from 4_World. Snapshot deaths here,
// then drain them from MissionServer.OnUpdate on the same server thread.
class BCZDeathRecord
{
 string victimId;
 string victimName;
 vector victimPosition;
 string killerId;
 string killerName;
 vector killerPosition;
};
class BCZDeathQueue
{
 protected static ref array<ref BCZDeathRecord> s_Events;
 static void RecordDeath(PlayerBase victim, PlayerBase killer)
 {
  if (!GetGame().IsServer() || !victim || !victim.GetIdentity()) return;
  BCZDeathRecord record = new BCZDeathRecord();
  record.victimId = victim.GetIdentity().GetId();
  record.victimName = victim.GetIdentity().GetName();
  record.victimPosition = victim.GetPosition();
  if (killer && killer != victim && killer.GetIdentity())
  {
   record.killerId = killer.GetIdentity().GetId();
   record.killerName = killer.GetIdentity().GetName();
   record.killerPosition = killer.GetPosition();
  }
  if (!s_Events) s_Events = new array<ref BCZDeathRecord>;
  s_Events.Insert(record);
 }
 static BCZDeathRecord Pop()
 {
  if (!s_Events || s_Events.Count() == 0) return null;
  BCZDeathRecord result = s_Events.Get(0);
  s_Events.RemoveOrdered(0);
  return result;
 }
};
