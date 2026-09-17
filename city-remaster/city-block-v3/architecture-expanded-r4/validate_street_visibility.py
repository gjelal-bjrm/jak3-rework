"""Check sight lines from actual terrain-level views to four new apertures."""
from pathlib import Path
import json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
s=read(H/'native.json');p=read(H/'wascitya-patch.json');specs=read(H/'new-window-specs.json');removed={key(f) for f in p['remove']}
result={'status':'passed','source_sha256':s['source_fr3']['sha256'],'patch_sha256':sha(H/'wascitya-patch.json'),'native_export_sha256':sha(H/'native.json'),'new_window_specs_sha256':sha(H/'new-window-specs.json'),'checks':{},'windows':[],'occluders_excluded':[]}
for lod in range(4):
 faces=[f for f in s['faces'] if f['geom']==lod and key(f) not in removed]+[f for f in p['add'] if f['geom']==lod]
 points=[];tris=[]
 for f in faces:
  i=len(points);points.extend(Vector(v['p']) for v in f['vertices']);tris.append((i,i+1,i+2))
 tree=BVHTree.FromPolygons(points,tris,all_triangles=True)
 for w in specs:
  c=Vector(w['center']);r=Vector(w['right']);u=Vector(w['up']);n=Vector(w['normal']);cam=Vector(w['street_camera']);rays=[]
  for x in (-.23,0,.23):
   for y in (-.23,0,.23):
    point=c+r*x*w['width']+u*y*w['height'];direction=(point-cam).normalized();hit=tree.ray_cast(cam,direction,(point-cam).length+.6)
    f=faces[hit[2]] if hit[0] is not None else None
    rays.append({'sample':[x,y],'passed':hit[0] is None,'hit_m':list(hit[0]) if hit[0] is not None else None,'face':{k:f.get(k) for k in ('tree_type','tree','draw','group','material','stream_index')} if f else None})
  passed=all(x['passed'] for x in rays)
  result['checks'][w['id']+' LOD'+str(lod)+' street sight lines']=passed
  result['windows'].append({'id':w['id'],'lod':lod,'camera_m':list(cam),'target_m':list(c),'ground_y':w['street_ground_y'],'rays':rays})
result['status']='passed' if all(result['checks'].values()) else 'failed'
(H/'street-visibility-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['checks'])
if result['status']!='passed':raise SystemExit(1)
