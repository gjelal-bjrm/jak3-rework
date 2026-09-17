"""Prove restoration to the exact R2 house1 surface, UVs and palette sources."""
from pathlib import Path
from collections import Counter
import json,hashlib,struct
H=Path(__file__).resolve().parent;A=H.parent/'architecture';R3=H.parent/'architecture-single-window-r3'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
def group(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','group'))
def signature(f):
 pts=[]
 for v in f['vertices']:
  color=v['color'] if 'color' in v else v['color_indices'][0]
  if 'color_indices' in v:assert v['color_indices']==[color]*3 and v['color_weights']==[1,0,0]
  pts.append(tuple(v['p'])+tuple(v['uv'])+(color,))
 return group(f)+(min(tuple(pts[i:]+pts[:i]) for i in range(3)),)
s=read(H/'native.json');p=read(H/'wascitya-patch.json');old=read(R3/'native.json');r3=read(R3/'wascitya-patch.json');historic=read(A/'wascitya-patch.json')
removed={key(f) for f in p['remove']};oldkeys={key(f):f for f in old['faces']}
house1={group(f) for f in historic['add'] if f['tree']==1 and f['group']==1}
house2={group(f) for f in historic['add'] if f['tree']==1 and f['group']==2}
expected=[f for f in old['faces'] if group(f) in house1]
actual=[f for f in s['faces'] if group(f) in house1 and key(f) not in removed]+[f for f in p['add'] if group(f) in house1]
oldanchors=read(A/'window-anchors.json');specs=read(H/'new-window-specs.json');anchors=read(H/'window-anchors.json')
checks={'house1_exact_R2_positions_uv_and_palette':Counter(signature(f) for f in actual)==Counter(signature(f) for f in expected),'restoration_face_count_6250':len(p['add'][:6250])==len(r3['remove'])==6250,'removed_R3_faces_266':len(p['remove'][:266])==len(r3['add'])==266,'house2_geometry_unselected':not any(group(f) in house2 for f in p['remove']+p['add']),'five_historical_anchors_exact':anchors[:5]==oldanchors,'four_new_anchors_exact':anchors[5:]==specs and len(specs)==4,'six_distinct_houses':{w['building_native_instance'] for w in anchors}=={0,1,2,3,4,58}}
checks['restored_faces_in_original_R3_removal_order']=all(signature(add)==signature(oldkeys[key(rem)]) for add,rem in zip(p['add'][:6250],r3['remove']))
result={'status':'passed' if all(checks.values()) else 'failed','source_sha256':s['source_fr3']['sha256'],'patch_sha256':sha(H/'wascitya-patch.json'),'r2_native_export_sha256':sha(R3/'native.json'),'r3_patch_sha256':sha(R3/'wascitya-patch.json'),'window_anchors_sha256':sha(H/'window-anchors.json'),'new_window_specs_sha256':sha(H/'new-window-specs.json'),'restored_house1_triangle_count':len(actual),'expected_house1_triangle_count':len(expected),'checks':checks}
(H/'restoration-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if result['status']!='passed':raise SystemExit(1)
