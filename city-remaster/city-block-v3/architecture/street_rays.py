from pathlib import Path
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent
s=json.loads((H/'block-native.json').read_text());p=json.loads((H/'wascitya-patch.json').read_text());a=json.loads((H/'window-anchors.json').read_text())
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
remove={key(f) for f in p['remove']};fs=[f for f in s['faces'] if f['geom']==0 and key(f) not in remove]+[f for f in p['add'] if f['geom']==0]
vs=[];ts=[]
for f in fs:
 i=len(vs);vs.extend(Vector(v['p']) for v in f['vertices']);ts.append((i,i+1,i+2))
b=BVHTree.FromPolygons(vs,ts,all_triangles=True)
for cam in [[2267,26.3,10],[2267,21.4,10],[2269,26.3,16],[2269,21.4,16],[2273,26.3,6]]:
 for w in a[:2]:
  c=Vector(cam);q=Vector(w['center']);d=q-c;hit=b.ray_cast(c,d.normalized(),d.length+3)
  print(cam,w['id'], 'CLEAR' if hit[0] is None else (list(hit[0]),hit[3],{k:fs[hit[2]].get(k) for k in ('material','tree_type','tree','draw','group','stream_index')}))
