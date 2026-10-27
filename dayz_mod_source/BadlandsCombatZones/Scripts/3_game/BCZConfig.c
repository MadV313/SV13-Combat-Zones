class BCZZone
{
 string name;
 float x;
 float z;
 float radius;
 bool enabled;
};
class BCZSafeZone
{
 string name;
 float x;
 float z;
 float radius;
};
class BCZConfig
{
 ref array<ref BCZZone> zones;
 ref array<ref BCZSafeZone> safe_zones;
 void BCZConfig()
 {
  zones = new array<ref BCZZone>;
  safe_zones = new array<ref BCZSafeZone>;
 }
};
