// Server-side PvP attribution only. Non-player/environmental deaths cannot award gear.
// EEKilled's killer argument is not dependable for every weapon; remember the last
// actual player who damaged this victim and only accept recent, verified evidence.
modded class PlayerBase
{
 protected PlayerBase m_BCZ_LastAttacker;
 protected int m_BCZ_LastAttackMs;

 override void EEHitBy(TotalDamageResult damageResult, int damageType, EntityAI source, int component, string dmgZone, string ammo, vector modelPos, float speedCoef)
 {
  super.EEHitBy(damageResult, damageType, source, component, dmgZone, ammo, modelPos, speedCoef);
  if (!GetGame().IsServer() || !source) return;
  PlayerBase attacker = PlayerBase.Cast(source);
  if (!attacker) attacker = PlayerBase.Cast(source.GetHierarchyRootPlayer());
  if (!attacker || attacker == this || !attacker.GetIdentity()) return;
  m_BCZ_LastAttacker = attacker;
  m_BCZ_LastAttackMs = GetGame().GetTime();
 }

 override void EEKilled(Object killer)
 {
  if (GetGame().IsServer())
  {
   PlayerBase attacker = PlayerBase.Cast(killer);
   if (!attacker)
   {
    EntityAI killerEntity = EntityAI.Cast(killer);
    if (killerEntity) attacker = PlayerBase.Cast(killerEntity.GetHierarchyRootPlayer());
   }
   if (!attacker && m_BCZ_LastAttacker && GetGame().GetTime() - m_BCZ_LastAttackMs <= 20000)
   {
    attacker = m_BCZ_LastAttacker;
   }
   BCZDeathQueue.RecordDeath(this, attacker);
  }
  super.EEKilled(killer);
 }
};
