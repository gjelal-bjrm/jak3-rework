from pathlib import Path
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent;s=json.loads((H/'native.json').read_text());o=json.loads((H.parent/'architecture-ornaments-r1/author-report.json').read_text())
fs=[f for f in s['faces'] if f['geom']==0];ps=[];ts=[]
for f in fs:
 i=len(ps);ps.extend(Vector(v['p']) for v in f['vertices']);ts.append((i,i+1,i+2))
b=BVHTree.FromPolygons(ps,ts,all_triangles=True);cam=Vector((2321,31,-16));out=[]
for o in o['objects']:
 if o['lod']!=0:continue
 c=Vector(o['center_m']);d=(c-cam).normalized();origin=cam.copy();hits=[]
 for t in range(8):
  hit=b.ray_cast(origin,d,(c-cam).length+3)
  if hit[0] is None:break
  f=fs[hit[2]];hits.append({'p':list(hit[0]),'distance':(hit[0]-cam).length,'face':{k:f[k] for k in ('material','tree_type','tree','draw','group','stream_index')}});origin=hit[0]+d*.01
 out.append({'name':o['name'],'center':list(c),'normal':o['normal'],'hits':hits})
 print(o['name'],list(c),o['normal'],hits[:4])
(H/'occlusion-diagnosis.json').write_text(json.dumps(out,indent=2))
