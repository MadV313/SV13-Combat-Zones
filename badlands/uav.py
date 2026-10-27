"""UAV map snapshot of last logged player positions; never claims real-time accuracy."""
from PIL import Image,ImageDraw
from io import BytesIO
import math, time

def render(path,maxx,maxz,zones,positions,age=360):
 im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im,'RGBA');w,h=im.size
 for z in zones:
  x=(z['x']/maxx)*w;y=h-(z['z']/maxz)*h;r=z['radius']/maxx*w
  d.ellipse((x-r,y-r,x+r,y+r),outline=(255,85,65,220),width=3)
  d.text((x+4,y+4),z['name'],fill=(255,255,255,255))
 for p in positions:
  if time.time()-p['seen_at']>age:continue
  x=p['x']/maxx*w;y=h-p['z']/maxz*h
  d.ellipse((x-5,y-5,x+5,y+5),fill=(255,220,10,220))
 bio=BytesIO();im.save(bio,'PNG');bio.seek(0);return bio
