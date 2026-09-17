"""Ray tests through the actual combined source/replacement native triangles."""
from pathlib import Path
import json,sys,hashlib,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text())
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
source=read(H/'native.json');patch=read(H/'wascitya-patch.json');anchors=read(H.parent/'architecture/window-anchors.json')
removed={key(f) for f in patch['remove']}
native={key(f):f for f in source['faces']}
checks=[]
checks.append({'name':'Every removal exists in exact source','passed':all(k in native for k in removed)})
checks.append({'name':'All removed original positions match','passed':all(f['original_positions']==[v['p'] for v in native[key(f)]['vertices']] for f in patch['remove'])})
checks.append({'name':'No duplicate native removals','passed':len(removed)==len(patch['remove'])})
checks.append({'name':'No nonfinite vertices or normals','passed':all(math.isfinite(x) for f in patch['add'] for v in f['vertices'] for x in v['p']+v['normal']+v['uv'])})
for lod in range(4):
 faces=[f for f in source['faces'] if f['geom']==lod and key(f) not in removed]+[f for f in patch['add'] if f['geom']==lod]
 points=[];polys=[]
 for f in faces:
  n=len(points);points.extend(Vector(v['p']) for v in f['vertices']);polys.append((n,n+1,n+2))
 tree=BVHTree.FromPolygons(points,polys,all_triangles=True)
 for w in anchors:
  c=Vector(w['center']);r=Vector(w['right']);u=Vector(w['up']);n=Vector(w['normal']);hits=[]
  for x in(-.35,0,.35):
   for y in(-.35,0,.35):
    origin=c+r*x*w['width']+u*y*w['height']+n*2.2
    hit=tree.ray_cast(origin,-n,5.7)
    if hit[0] is not None:
     f=faces[hit[2]];hits.append({'sample':[x,y],'point':list(hit[0]),'distance':hit[3],'material':f.get('material'),'tree':f['tree'],'draw':f['draw'],'group':f['group'],'key':list(key(f)) if 'stream_index' in f else None})
  checks.append({'name':w['id']+' LOD'+str(lod)+' actual 3x3 rays clear','passed':not hits,'hits':hits})
result={'passed':all(c['passed'] for c in checks),'source_sha256':source['source_fr3']['sha256'],'patch_sha256':hashlib.sha256((H/'wascitya-patch.json').read_bytes()).hexdigest(),'checks':checks}
(H/'opening-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not result['passed']:raise SystemExit(1)
