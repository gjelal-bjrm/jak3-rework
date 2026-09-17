"""Restore house1's lateral window and add four street-facing house openings."""
from pathlib import Path
from collections import Counter,defaultdict
import importlib.util,inspect,json,hashlib,sys,struct,bpy
from mathutils import Vector
H=Path(__file__).resolve().parent;A=H.parent/'architecture';R3=H.parent/'architecture-single-window-r3';R=H.parents[2]
spec=importlib.util.spec_from_file_location('historical_author',A/'author_buildings.py');author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
NativeMesh=author.NativeMesh
# Keep complete native triangles when they do not overlap the opening's
# projected rectangle. The historical cutter otherwise retriangulates some
# remote parts of the same facade along the rectangle's infinite cut lines.
bounded_cut_source=inspect.getsource(author.cut_windows).replace(
 'if min(z)>2 or max(z)<-4:nxt.append(poly);continue',
 "xs=[p[2].x for p in pp];ys=[p[2].y for p in pp]\n    if min(z)>2 or max(z)<-4 or max(xs)<-w['width']/2 or min(xs)>w['width']/2 or max(ys)<-w['height']/2 or min(ys)>w['height']/2:nxt.append(poly);continue")
exec(compile(bounded_cut_source,'bounded_new_window_cutter','exec'),author.__dict__)
def read(p):return json.loads(Path(p).read_text())
def write(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
def signature(f):
 pts=[tuple(struct.unpack('f',struct.pack('f',x))[0] for x in v['p']) for v in f['vertices']]
 return (f['tree_type'],f['geom'],f['tree'],f['draw'],f['group'],min(tuple(pts[i:]+pts[:i]) for i in range(3)))
def remove_record(f):return {**{k:f[k] for k in ('tree_type','geom','tree','draw','group','stream_index')},'original_positions':[v['p'] for v in f['vertices']]}
def native_record(f):
 pts=[Vector(v['p']) for v in f['vertices']];n=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
 return {**{k:f[k] for k in ('tree_type','geom','tree','draw','group')},'vertices':[{'p':v['p'],'uv':v['uv'],'normal':list(n),'color_indices':[v['color']]*3,'color_weights':[1,0,0]} for v in f['vertices']]}
def new_frame(native,w):
 c,r,u,n=author.frame(w);width=w['width'];height=w['height'];material='wascity-stucco-wall-bleached-01'
 style=w['region'];thickness={'east':.23,'west':.33,'low':.18,'north':.26}[style]
 for sign in(-1,1):author.box(native,c+r*sign*(width/2+thickness/2)-n*.18,r,u,n,(thickness,height+.55,.82),material,.075)
 author.box(native,c-u*(height/2+.17)+n*.08,r,u,n,(width+thickness*2+.2,.32,1.1 if style=='low' else .95),material,.08)
 author.box(native,c+u*(height/2+.17)-n*.04,r,u,n,(width+thickness*2+.14,.34,.85),material,.08)
 if style=='east':
  author.box(native,c+u*(height/2+.44)+n*.1,r,u,n,(width+.98,.19,1.04),material,.07)
 elif style=='west':
  for sign in(-1,1):author.box(native,c+r*sign*(width/2+.18)-u*(height/2+.42)+n*.12,r,u,n,(.52,.34,.93),material,.06)
 elif style=='low':
  # The broad low sill has two short supports; no balcony projects into the path.
  for sign in(-1,1):author.box(native,c+r*sign*.9-u*(height/2+.42)-n*.03,r,u,n,(.32,.36,.63),material,.06)
 else:
  author.box(native,c+u*(height/2+.42)-n*.12,r,u,n,(width+.35,.2,.63),material,.06)
def difference(before,after):
 old=Counter(signature(f) for f in before);new=Counter(signature(f) for f in after);rem=old-new;add=new-old
 removed=[];added=[]
 for f in before:
  k=signature(f)
  if rem[k]:removed.append(f);rem[k]-=1
 for f in after:
  k=signature(f)
  if add[k]:added.append(f);add[k]-=1
 return removed,added
def main():
 author.reset();source=read(H/'native.json');original=read(R/'city-remaster/environment/architecture/wascitya-native.json');new_windows=read(H/'new-window-specs.json')
 patch={'level':'wascitya','source_fr3':source['source_fr3'],'preserve_bvh':True,'remove':[],'add':[]}
 report={'status':'authored','source_fr3':source['source_fr3'],'author_sha256':sha(__file__),'house_count':6,'historical_author':str(A/'author_buildings.py'),'historical_author_sha256':sha(A/'author_buildings.py'),'restoration':{},'windows':[]}
 # Invert only R3's house1 change, reading original vertices/UV/colour indices
 # directly from its exact R2 native export. The palette prefix is preserved.
 r3patch=read(R3/'wascitya-patch.json');r2native=read(R3/'native.json');r2lookup={key(f):f for f in r2native['faces']}
 current=defaultdict(list)
 for f in source['faces']:current[signature(f)].append(f)
 for f in r3patch['add']:
  sig=signature(f);assert current[sig],('R3 restoration face missing',sig)
  patch['remove'].append(remove_record(current[sig].pop()))
 for f in r3patch['remove']:
  native=r2lookup[key(f)];assert [v['p'] for v in native['vertices']]==f['original_positions']
  patch['add'].append(native_record(native))
 report['restoration']={'r3_patch':str(R3/'wascitya-patch.json'),'r3_patch_sha256':sha(R3/'wascitya-patch.json'),'r2_native_export':str(R3/'native.json'),'r2_native_export_sha256':sha(R3/'native.json'),'removed':len(r3patch['add']),'added':len(r3patch['remove']),'positions_uv_palette_exact_from_r2':True}
 for w in new_windows:
  for lod in range(4):
   originals=[f for f in original['faces'] if f['tree_type']=='tie' and f['tree']==1 and f['instance'] in w['building_native_instances'] and f['geom']==lod]
   groups={(f['tree_type'],f['tree'],f['draw'],f['group']) for f in originals}
   target=[f for f in source['faces'] if f['geom']==lod and (f['tree_type'],f['tree'],f['draw'],f['group']) in groups]
   assert target,(w['id'],lod)
   native=NativeMesh(w['id']+' LOD'+str(lod),target)
   cut=author.cut_windows(native,[w]);new_frame(native,w)
   _,after,_=native.records(target);valid=[]
   for f in after:
    ps=[Vector(v['p']) for v in f['vertices']];n=(ps[1]-ps[0]).cross(ps[2]-ps[0])
    if n.length<1e-8:continue
    n.normalize()
    for v in f['vertices']:
     v['normal']=list(n);weights=[max(0,x) for x in v['color_weights']];v['color_weights']=[x/sum(weights) for x in weights]
    valid.append(f)
   rem,add=difference(target,valid)
   patch['remove'].extend(remove_record(f) for f in rem);patch['add'].extend(add)
   report['windows'].append({'id':w['id'],'lod':lod,'region':w['region'],'native_instances':w['building_native_instances'],'cut_polygons':cut,'removed':len(rem),'added':len(add),'groups':sorted({(f['tree'],f['draw'],f['group']) for f in rem+add})})
   native.obj.location=(native.origin.x,-native.origin.z,native.origin.y);native.obj.hide_set(lod!=0);native.obj.hide_render=lod!=0
 assert len({key(f) for f in patch['remove']})==len(patch['remove'])
 report['faces_removed']=len(patch['remove']);report['faces_added']=len(patch['add'])
 write(H/'wascitya-patch.json',patch);write(H/'author-report.json',report)
 bpy.ops.wm.save_as_mainfile(filepath=str(H/'four-street-houses.blend'))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
