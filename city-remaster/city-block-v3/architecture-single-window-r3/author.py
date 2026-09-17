"""Remove one lateral window, reconstructing its wall from pre-opening sources.

Replay the pinned historical Blender author both ways, then export only the
triangle difference. Whole-house reauthoring is never applied to the FR3.
"""
from pathlib import Path
from collections import Counter,defaultdict
import importlib.util,json,hashlib,copy,sys,struct,bpy
from mathutils import Vector
H=Path(__file__).resolve().parent;A=H.parent/'architecture';R=H.parents[2]
spec=importlib.util.spec_from_file_location('historical_author',A/'author_buildings.py')
author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
NativeMesh=author.NativeMesh
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')
def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
def signature(f):
 # Face order may rotate after mesh compilation; its winding is preserved.
 pts=[tuple(f32(x) for x in v['p']) for v in f['vertices']]
 rotations=[tuple(pts[i:]+pts[:i]) for i in range(3)]
 return (f['tree_type'],f['geom'],f['tree'],f['draw'],f['group'],min(rotations))
def export(native,target):
 _,faces,_=native.records(target);out=[]
 for f in faces:
  a,b,c=[Vector(v['p']) for v in f['vertices']];n=(b-a).cross(c-a)
  if n.length<1e-8:continue
  n.normalize()
  for v in f['vertices']:v['normal']=list(n)
  out.append(f)
 return out
def diff(before,after,current):
 # Before is reproduced historical geometry, matched to exact current native
 # triangles. Its unchanged subset stays byte-identical in the game file.
 oldcount=Counter(signature(f) for f in before);newcount=Counter(signature(f) for f in after)
 removed=oldcount-newcount;added=newcount-oldcount
 lookup=defaultdict(list)
 for f in current:lookup[signature(f)].append(f)
 rem=[];add=[]
 for sig,count in removed.items():
  assert len(lookup[sig])>=count,('Current source missing authored triangle',sig,count)
  rem.extend(lookup[sig][:count])
 for f in after:
  sig=signature(f)
  if added[sig]:add.append(f);added[sig]-=1
 return rem,add
def main():
 author.reset();source=read(H/'native.json');historical=read(A/'wascitya-patch.json');targetsource=read(A/'block-native.json')
 original_path=R/'city-remaster/environment/architecture/wascitya-native.json';original=read(original_path)
 assert read(A/'author-report.json')['author_sha256']==sha(A/'author_buildings.py')
 windows=copy.deepcopy(author.SPECS[1]['windows']);kept=[w for w in windows if w['id']!='wca-house1-east-room']
 patch={'level':'wascitya','source_fr3':source['source_fr3'],'preserve_bvh':True,'remove':[],'add':[]};desired=[]
 report={'status':'authored','source_fr3':source['source_fr3'],'author_sha256':sha(__file__),'historical_author':str(A/'author_buildings.py'),'historical_author_sha256':sha(A/'author_buildings.py'),'pre_opening_source':str(original_path),'pre_opening_source_sha256':sha(original_path),'historical_patch':str(A/'wascitya-patch.json'),'historical_patch_sha256':sha(A/'wascitya-patch.json'),'removed_window_id':'wca-house1-east-room','groups':[],'checks':{}}
 for lod in range(4):
  base=[f for f in original['faces'] if f['tree']==1 and f['instance']==1 and f['geom']==lod]
  groups={(f['tree_type'],f['geom'],f['tree'],f['draw'],f['group']) for f in base}
  target=[f for f in targetsource['faces'] if (f['tree_type'],f['geom'],f['tree'],f['draw'],f['group']) in groups]
  replay=[]
  for label,winlist in [('before',windows),('after',kept)]:
   n=NativeMesh('House1 '+label+' LOD'+str(lod),base)
   author.roof_volumes(n,author.SPECS[1],lod);author.cut_windows(n,winlist)
   for w in winlist:author.window_architecture(n,w,lod)
   faces=export(n,target);replay.append(faces)
   n.obj.location=(n.origin.x,-n.origin.z,n.origin.y);n.obj.hide_set(label=='before' or lod!=0);n.obj.hide_render=label=='before' or lod!=0
  expected=[f for f in historical['add'] if f['tree']==1 and f['group']==1 and f['geom']==lod]
  desired.extend({**{k:f[k] for k in ('tree_type','geom','tree','draw','group')},'vertices':[{'p':v['p']} for v in f['vertices']]} for f in replay[1])
  identical=Counter(signature(f) for f in replay[0])==Counter(signature(f) for f in expected)
  report['checks'][f'LOD{lod} exact historical replay']=identical
  assert identical,('Historical geometry could not be reproduced',lod,len(replay[0]),len(expected))
  current=[f for f in source['faces'] if f['tree_type']=='tie' and f['tree']==1 and f['group']==1 and f['geom']==lod]
  rem,add=diff(replay[0],replay[1],current)
  patch['remove'].extend({**{k:f[k] for k in ('tree_type','geom','tree','draw','group','stream_index')},'original_positions':[v['p'] for v in f['vertices']]} for f in rem);patch['add'].extend(add)
  report['groups'].append({'lod':lod,'tree':1,'group':1,'removed':len(rem),'added':len(add),'removed_by_draw':dict(Counter(f['draw'] for f in rem)),'added_by_draw':dict(Counter(f['draw'] for f in add))})
  # Restore only any native decorative occluder triangles cut by the now-closed
  # lateral window. Other window cuts are replayed identically and retained.
  allwin=[w for s in author.SPECS.values() for w in s['windows']]
  for draw,group in [(9,81),(44 if lod<3 else 42,34)]:
   target=[f for f in targetsource['faces'] if f['tree_type']=='tie' and f['geom']==lod and f['tree']==0 and f['draw']==draw and f['group']==group]
   if not target:continue
   results=[]
   for label,winlist in [('before',allwin),('after',[w for w in allwin if w['id']!='wca-house1-east-room'])]:
    n=NativeMesh('Historical trim '+label+' '+str((lod,draw,group)),target);author.cut_windows(n,winlist)
    results.append(export(n,target));n.obj.hide_set(True);n.obj.hide_render=True
   if Counter(signature(f) for f in results[0])==Counter(signature(f) for f in results[1]):continue
   current=[f for f in source['faces'] if f['tree_type']=='tie' and f['geom']==lod and f['tree']==0 and f['draw']==draw and f['group']==group]
   rem,add=diff(results[0],results[1],current)
   patch['remove'].extend({**{k:f[k] for k in ('tree_type','geom','tree','draw','group','stream_index')},'original_positions':[v['p'] for v in f['vertices']]} for f in rem);patch['add'].extend(add)
   report['groups'].append({'lod':lod,'tree':0,'draw':draw,'group':group,'removed':len(rem),'added':len(add)})
 for f in patch['add']:
  for v in f['vertices']:
   w=[max(0,x) for x in v['color_weights']];v['color_weights']=[x/sum(w) for x in w]
 report['faces_removed']=len(patch['remove']);report['faces_added']=len(patch['add'])
 write(H/'expected-house-without-east.json',desired)
 report['expected_house']=str(H/'expected-house-without-east.json');report['expected_house_sha256']=sha(H/'expected-house-without-east.json')
 write(H/'wascitya-patch.json',patch);write(H/'author-report.json',report)
 bpy.ops.wm.save_as_mainfile(filepath=str(H/'house1-single-window.blend'))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
