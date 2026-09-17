import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent
s=json.loads((H/'block-native.json').read_text());o=json.loads((H.parents[2]/'city-remaster/environment/architecture/wascitya-native.json').read_text())
keys={(f['tree'],f['draw'],f['group']) for f in o['faces'] if f['geom']==0 and f['tree']==1 and f['instance']==2}
fs=[f for f in s['faces'] if f['geom']==0 and (f['tree'],f['draw'],f['group']) not in keys];p=[];t=[]
for f in fs:
 k=len(p);p.extend(Vector(v['p']) for v in f['vertices']);t.append((k,k+1,k+2))
b=BVHTree.FromPolygons(p,t,all_triangles=True)
for c,n in [([2352.55,18.0,0],[-.991,0,-.136]),([2352.55,21.0,0],[-.991,0,-.136]),([2352.55,25.0,0],[-.991,0,-.136]),([2339.35,19.0,-26.55],[-.874,0,.486]),([2350.7,12.2,-6],[-.874,0,.486]),([2348.5,12.2,-10],[-.874,0,.486]),([2352.55,12.2,0],[-.991,0,-.136]),([2334,12.2,-33],[.349,0,-.937]),([2356,12.2,-17],[.534,0,.846]),([2349.5,12.2,-13.2],[.436,0,.9])]:
 c=Vector(c);n=Vector(n).normalized();r=Vector((n.z,0,-n.x));u=Vector((0,1,0));hits=[]
 for x in(-.35,0,.35):
  for y in(-.35,0,.35):
   hit=b.ray_cast(c+r*x*3.4+u*y*3+n*2.2,-n,5.7)
   if hit[0] is not None:hits.append((fs[hit[2]]['material'],tuple(round(a,2) for a in hit[0])))
 print(list(c),list(n),len(hits),hits[:3])
