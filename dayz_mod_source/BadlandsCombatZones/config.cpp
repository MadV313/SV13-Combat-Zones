class CfgPatches
{
 class BadlandsCombatZones { units[]={}; weapons[]={}; requiredVersion=0.1; requiredAddons[]={"DZ_Data"}; };
};
class CfgMods
{
 class BadlandsCombatZones
 {
  dir="BadlandsCombatZones"; name="Badlands Combat Zones"; type="mod";
  dependencies[]={"Game","World","Mission"};
  class defs
  {
   class gameScriptModule { value=""; files[]={"BadlandsCombatZones/Scripts/3_Game"}; };
   class missionScriptModule { value=""; files[]={"BadlandsCombatZones/Scripts/5_Mission"}; };
  };
 };
};
