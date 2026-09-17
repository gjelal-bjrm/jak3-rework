"""Stage and strictly audit the two-house patch. Never modifies live data."""
from pathlib import Path
import sys, json, hashlib, struct, math, subprocess
H=Path(__file__).resolve().parent;R=H.parents[2];C=R/'city-remaster'
BRIDGE=R/'engine-build/bin/Release/palace_mesh_bridge.exe'
BLENDER=Path(r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
sys.path.insert(0,str(C))
from audit_native_patch import audit
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')

def verify_geometry(p):
 bad=deg=weights=0
 for f in p['add']:
  ps=[[struct.unpack('f',struct.pack('f',x))[0] for x in v['p']] for v in f['vertices']]
  a,b,c=ps;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
  n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
  if math.sqrt(sum(x*x for x in n))<1e-9:deg+=1;continue
  for v in f['vertices']:
   if abs(math.sqrt(sum(x*x for x in v['normal']))-1)>1e-3 or sum(n[i]*v['normal'][i] for i in range(3))<0:bad+=1
   if abs(sum(v['color_weights'])-1)>1e-4 or min(v['color_weights'])<-.0001:weights+=1
 result={'passed':not(deg or bad or weights),'faces_removed':len(p['remove']),'faces_added':len(p['add']),
  'degenerate_float32':deg,'bad_normals':bad,'bad_palettes':weights,'patch_sha256':sha(H/'wascitya-patch.json'),'source_fr3':p['source_fr3']}
 write(H/'geometry-validation.json',result)
 if not result['passed']:raise ValueError(result)

def main():
 stage=H/'staging';stage.mkdir(exist_ok=True)
 patch=H/'wascitya-patch.json';p=read(patch)
 parent=H.parent/'architecture/installed.json';prec=read(parent)
 before=Path(prec['output_path']);after=stage/'wascitya.fr3'
 assert p['preserve_bvh'] is True,'The native coverage audit allows unchanged BVH; no blind expansion'
 assert sha(before)==p['source_fr3']['sha256']==prec['output_sha256']
 verify_geometry(p)
 with (stage/'opening-validation.log').open('w') as f:
  subprocess.run([str(BLENDER),'--background','--python',str(H/'validate_openings.py')],stdout=f,stderr=subprocess.STDOUT,check=True)
 assert read(H/'opening-validation.json')['passed']
 with (stage/'coverage.log').open('w') as f:
  subprocess.run([str(BRIDGE),'--audit-bvh-coverage',str(before),str(patch),str(H/'bvh-coverage.json')],stdout=f,stderr=subprocess.STDOUT,check=True)
 with (stage/'bridge.log').open('w') as f:
  subprocess.run([str(BRIDGE),str(before),str(patch),str(after)],stdout=f,stderr=subprocess.STDOUT,check=True)
 proof=stage/'preservation.json';result=audit(before,after,patch,proof)
 assert result['status']=='passed'
 manifest={'status':'staged','path':'out/jak3/fr3/wascitya.fr3','base_path':str(before),'base_sha256':sha(before),
  'output_path':str(after),'output_sha256':sha(after),'patch':str(patch),'patch_sha256':sha(patch),
  'preservation_report':str(proof),'preservation_report_sha256':sha(proof),'parent_record':str(parent),'parent_record_sha256':sha(parent),
  'author_report':str(H/'author-report.json'),'author_report_sha256':sha(H/'author-report.json'),
  'native_visual_validation':False,'scope':'House2 seven closed beveled bronze pointed ornaments, remove entire superseded motif intersecting window and loose fragments; no walls or windows moved'}
 for field,filename in [('bvh_coverage','bvh-coverage.json'),('opening_validation','opening-validation.json'),('geometry_validation','geometry-validation.json'),('window_anchors','window-anchors.json')]:
  path=(H.parent/'architecture'/filename) if field=='window_anchors' else H/filename;manifest[field]=str(path);manifest[field+'_sha256']=sha(path)
 write(H/'candidate.json',manifest)
 print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
