from pathlib import Path
from collections import defaultdict
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent;A=H.parent/'architecture'
s=json.loads((A/'block-native.json').read_text());c=json.loads((H/'native.json').read_text());groups=defaultdict(list)
def bvh(fs):
 p=[];f=[]
 for x in fs:
  n=len(p);p.extend(Vector(v['p']) for v in x['vertices']);f.append((n,n+1,n+2))
 return BVHTree.FromPolygons(p,f,all_triangles=True)
for house in (1,2):
 bf=[f for f in s['faces'] if f['geom']==0 and f['tree_type']=='tie' and f['tree']==1 and f['group']==house and 'stucco-wall' in f['material']]
 af=[f for f in c['faces'] if f['geom']==0 and f['tree_type']=='tie' and f['tree']==1 and f['group']==house and 'stucco-wall' in f['material']]
 b=bvh(bf);a=bvh(af)
 groups=defaultdict(list)
 for f in s['faces']:
  if f['geom']==0 and f['tree']==0 and ('metal-piece' in f['material'] or 'steel' in f['material'] or 'metal-dirty' in f['material']):groups[(f['draw'],f['group'],f['material'])].append(f)
 for k,fs in groups.items():
  ps=[Vector(v['p']) for f in fs for v in f['vertices']];near=[b.find_nearest(q) for q in ps]
  if min(t[3] for t in near)>1:continue
  values=[]
  for q,old in zip(ps,near):
   new=a.find_nearest(q);signed_old=(q-old[0]).dot(old[1]);signed_new=(q-new[0]).dot(new[1]);values.append((signed_old,signed_new))
  print(house,k,'Y',round(min(q.y for q in ps),2),round(max(q.y for q in ps),2),'old',round(min(v[0] for v in values),3),round(max(v[0] for v in values),3),'new',round(min(v[1] for v in values),3),round(max(v[1] for v in values),3),'nowburied',sum(x>=-.003 and y<-.01 for x,y in values))
