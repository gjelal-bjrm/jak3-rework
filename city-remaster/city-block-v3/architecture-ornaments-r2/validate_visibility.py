"""Cast the actual street camera through the complete exported native block.

No occluders are excluded. The source contains all TIE/TFRAG triangles
intersecting X2260..2370 Z-45..40, in all four LODs.
"""
from pathlib import Path
import json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
s=read(H/'native.json');p=read(H/'wascitya-patch.json');a=read(H/'author-report.json')
removed={key(f) for f in p['remove']}
camera=Vector((2321,31,-16));target=Vector((2342,27,-21))
forward=(target-camera).normalized();right=Vector((forward.z,0,-forward.x)).normalized()
cameras=[camera,camera+right*2,camera-right*2]
report={'status':'passed','source_sha256':s['source_fr3']['sha256'],'patch_sha256':sha(H/'wascitya-patch.json'),'native_export_sha256':sha(H/'native.json'),'author_report_sha256':sha(H/'author-report.json'),'cameras_m':[list(v) for v in cameras],'native_camera_target_m':list(target),'full_block_faces':len(s['faces']),'occluders_excluded':[],'checks':{},'plaques':[]}
for lod in range(4):
 fs=[{**f,'replacement':False} for f in s['faces'] if f['geom']==lod and key(f) not in removed]+[{**f,'replacement':True} for f in p['add'] if f['geom']==lod]
 ps=[];tris=[]
 for f in fs:
  i=len(ps);ps.extend(Vector(v['p']) for v in f['vertices']);tris.append((i,i+1,i+2))
 b=BVHTree.FromPolygons(ps,tris,all_triangles=True)
 for obj in [o for o in a['objects'] if o['lod']==lod]:
  front=[Vector(v) for v in obj['front_face_samples_m']]
  samples=[]
  for w0 in (.15,.3,.45,.6,.75):
   for w1 in (.15,.3,.45,.6,.75):
    w2=1-w0-w1
    if w2>=.1:samples.append(front[0]*w0+front[1]*w1+front[2]*w2)
  checks=[];normal=Vector(obj['normal']);local_rays=[]
  for point in samples:
   hit=b.ray_cast(point+normal*2,-normal,3)
   f=fs[hit[2]] if hit[0] is not None else None
   ok=f is not None and f['replacement'] and f['tree']==0 and f['group']==obj['group']
   local_rays.append({'sample_m':list(point),'passed':ok,'hit_m':list(hit[0]) if hit[0] is not None else None})
  report['checks'][obj['name']+' all samples ahead of support wall']=all(x['passed'] for x in local_rays)
  for ci,cam in enumerate(cameras):
   hits=[];passed=True
   for point in samples:
    direction=(point-cam).normalized();hit=b.ray_cast(cam,direction,(point-cam).length+1)
    f=fs[hit[2]] if hit[0] is not None else None
    ok=f is not None and f['replacement'] and f['tree']==0 and f['group']==obj['group']
    gap=(point-hit[0]).length if hit[0] is not None else 0
    ordinary_occlusion=not ok and f is not None and not f['replacement'] and gap>3
    passed=passed and (ok or ordinary_occlusion)
    hits.append({'sample_m':list(point),'visible':ok,'ordinary_foreground_occlusion':ordinary_occlusion,'separation_to_occluder_m':gap,'hit_m':list(hit[0]) if hit[0] is not None else None,'face':{k:f.get(k) for k in ('replacement','tree_type','tree','draw','group','material','stream_index')} if f else None})
   name=obj['name']+' camera'+str(ci)+' no support wall clipping';report['checks'][name]=passed
   checks.append({'camera_index':ci,'no_support_wall_clipping':passed,'visible_samples':sum(x['visible'] for x in hits),'rays':hits})
  report['checks'][obj['name']+' fully visible in an adjacent street view']=any(c['visible_samples']==len(samples) for c in checks)
  if lod==0:report['checks'][obj['name']+' native close camera minimum 85 percent visible']=checks[0]['visible_samples']/len(samples)>=.85
  report['plaques'].append({'name':obj['name'],'lod':lod,'group':obj['group'],'normal':obj['normal'],'samples_per_camera':len(samples),'local_street_side_rays':local_rays,'cameras':checks})
report['status']='passed' if all(report['checks'].values()) else 'failed'
(H/'visibility-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],sum(report['checks'].values()),len(report['checks']))
for k,v in report['checks'].items():
 if not v:print('FAILED',k)
if report['status']!='passed':raise SystemExit(1)
