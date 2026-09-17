"""Verify an opaque native wall replaces the removed lateral opening at all LODs."""
from pathlib import Path
from collections import Counter
import json,hashlib,struct
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent;A=H.parent/'architecture';R=H.parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
def signature(f):
 pts=[tuple(struct.unpack('f',struct.pack('f',x))[0] for x in v['p']) for v in f['vertices']]
 return (f['tree_type'],f['geom'],f['tree'],f['draw'],f['group'],min(tuple(pts[i:]+pts[:i]) for i in range(3)))
def bvh(fs):
 points=[];tri=[]
 for f in fs:
  i=len(points);points.extend(Vector(v['p']) for v in f['vertices']);tri.append((i,i+1,i+2))
 return BVHTree.FromPolygons(points,tri,all_triangles=True)
source=read(H/'native.json');patch=read(H/'wascitya-patch.json');a=read(H/'author-report.json');expected=read(H/'expected-house-without-east.json')
baseline=read(a['pre_opening_source']);anchors=read(A/'window-anchors.json');newanchors=read(H/'window-anchors.json')
w=next(w for w in anchors if w['id']=='wca-house1-east-room')
c=Vector(w['center']);r=Vector(w['right']);u=Vector(w['up']);n=Vector(w['normal'])
removed={key(f) for f in patch['remove']}
result={'status':'passed','source_sha256':source['source_fr3']['sha256'],'patch_sha256':sha(H/'wascitya-patch.json'),'author_report_sha256':sha(H/'author-report.json'),'native_export_sha256':sha(H/'native.json'),'expected_house_sha256':sha(H/'expected-house-without-east.json'),'baseline_sha256':sha(a['pre_opening_source']),'removed_window_id':w['id'],'previous_window_anchors_sha256':sha(A/'window-anchors.json'),'window_anchors_sha256':sha(H/'window-anchors.json'),'checks':{},'lods':[]}
result['checks']['Only east-room anchor removed']=newanchors==[x for x in anchors if x['id']!=w['id']]
for lod in range(4):
 faces=[f for f in source['faces'] if f['geom']==lod and key(f) not in removed]+[f for f in patch['add'] if f['geom']==lod]
 desired=[f for f in expected if f['geom']==lod]
 groups={(f['tree_type'],f['tree'],f['draw'],f['group']) for f in desired}
 house=[f for f in faces if (f['tree_type'],f['tree'],f['draw'],f['group']) in groups]
 result['checks'][f'LOD{lod} exact house without lateral frame and balcony']=Counter(signature(f) for f in house)==Counter(signature(f) for f in desired)
 wall=[f for f in baseline['faces'] if f['geom']==lod and f['tree']==1 and f['instance']==1]
 tree=bvh(faces);original=bvh(wall);samples=[]
 for x in (-.45,-.3,-.15,0,.15,.3,.45):
  for y in (-.45,-.3,-.15,0,.15,.3,.45):
   origin=c+r*(x*w['width'])+u*(y*w['height'])+n*2.2
   hit=tree.ray_cast(origin,-n,6);old=original.ray_cast(origin,-n,6)
   f=faces[hit[2]] if hit[0] is not None else None
   distance=(hit[0]-old[0]).length if hit[0] is not None and old[0] is not None else None
   ok=f is not None and f['tree_type']=='tie' and f['tree']==1 and f['group']==1 and distance is not None and distance<.005
   samples.append({'sample':[x,y],'passed':ok,'native_wall_deviation_m':distance,'hit_m':list(hit[0]) if hit[0] is not None else None,'baseline_hit_m':list(old[0]) if old[0] is not None else None,'face':{k:f.get(k) for k in ('tree_type','tree','draw','group','material','stream_index')} if f else None})
 result['checks'][f'LOD{lod} 49 opaque wall rays at original surface']=all(s['passed'] for s in samples)
 result['lods'].append({'lod':lod,'after_house_triangles':len(house),'expected_house_triangles':len(desired),'wall_samples':samples})
result['status']='passed' if all(result['checks'].values()) else 'failed'
(H/'closed-window-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],result['checks'])
if result['status']!='passed':raise SystemExit(1)
