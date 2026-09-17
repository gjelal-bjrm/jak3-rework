"""Reanchor four closed house2 shields to the street side of the native double-sided wall."""
from pathlib import Path
from collections import defaultdict
import bpy,bmesh,json,sys,math,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent;A=H.parent/'architecture';R=H.parents[2]
sys.path.insert(0,str(R/'models-v1'))
from blender_common import NativeMesh,reset,render_asset
def read(p):return json.loads(Path(p).read_text())
def write(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bvh(fs):
 ps=[];polys=[]
 for f in fs:
  i=len(ps);ps.extend(Vector(v['p']) for v in f['vertices']);polys.append((i,i+1,i+2))
 return BVHTree.FromPolygons(ps,polys,all_triangles=True)
def component_faces(fs):
 byvertex=defaultdict(set)
 for i,f in enumerate(fs):
  for v in f['vertices']:byvertex[tuple(round(x,3) for x in v['p'])].add(i)
 unseen=set(range(len(fs)));result=[]
 while unseen:
  todo=[unseen.pop()];used=set(todo)
  while todo:
   f=fs[todo.pop()]
   for v in f['vertices']:
    for i in byvertex[tuple(round(x,3) for x in v['p'])]:
     if i in unseen:unseen.remove(i);used.add(i);todo.append(i)
  result.append([fs[i] for i in sorted(used)])
 return result

def remodel(component,targets,wall,lod,name):
 native=NativeMesh(name,component)
 points=[Vector(v['p']) for f in component for v in f['vertices']]
 center=sum(points,Vector())/len(points);near=wall.find_nearest(center)
 n=Vector((near[1].x,0,near[1].z)).normalized()
 if n.dot(Vector((2321,31,-16))-center)<0:n=-n
 r=Vector((n.z,0,-n.x));u=Vector((0,1,0))
 xl=min((p-center).dot(r) for p in points);xh=max((p-center).dot(r) for p in points)
 yl=min(p.y for p in points);yh=max(p.y for p in points)
 midpoint=(xl+xh)/2;w=xh-xl;height=yh-yl
 # Original long pointed silhouette, rebuilt as a closed metal shield.
 outline=[(xl,yh-.09),(xh,yh-.09),(midpoint+.025,yh-height+.04)]
 back=[];normals=[]
 for x,y in outline:
  seed=center+r*x;seed.y=y
  hit=wall.ray_cast(seed+n*4,-n,8)
  if hit[0] is None:raise RuntimeError('No wall behind metal plaque')
  back.append(hit[0]+n*.022);normals.append(hit[1])
 front=[p+n*.25 for p in back]
 # A raised central ridge catches the light and makes the new plaque legible.
 ridge=sum(front,Vector())/3+n*.10
 world=back+front+[ridge]
 faces=[(2,1,0),(0,1,4,3),(1,2,5,4),(2,0,3,5),(3,4,6),(4,5,6),(5,3,6)]
 bm=bmesh.new();vv=[bm.verts.new(native.local(p)) for p in world]
 for f in faces:bm.faces.new([vv[i] for i in f])
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 bmesh.ops.bevel(bm,geom=list(bm.edges),offset=.065,segments=3 if lod<2 else 2,affect='EDGES',clamp_overlap=True)
 bm.normal_update();mesh=bpy.data.meshes.new(name+' closed bevel');bm.to_mesh(mesh);bm.free()
 for m in native.obj.data.materials:mesh.materials.append(m)
 native.obj.data=mesh
 uv=mesh.uv_layers.new(name='UVMap')
 for face in mesh.polygons:
  for li,vi in zip(face.loop_indices,face.vertices):
   wp=Vector(native.world(mesh.vertices[vi].co));uv.data[li].uv=(((wp-center).dot(r)-xl)/max(w,.01),(wp.y-yl)/max(height,.01))
 rem,add,dev=native.records(targets)
 # Normal records reflect actual final triangle winding.
 for f in add:
  p=[Vector(v['p']) for v in f['vertices']];nn=(p[1]-p[0]).cross(p[2]-p[0]).normalized()
  for v in f['vertices']:
   v['normal']=list(nn)
   # The nearest old beveled triangle can be very thin. Clamp its numerically
   # unstable barycentric weights to the colour simplex before native export.
   weights=[max(0,x) for x in v['color_weights']];total=sum(weights)
   v['color_weights']=[x/total for x in weights]
 native.obj.location=(native.origin.x,-native.origin.z,native.origin.y)
 native.obj.hide_set(lod!=0);native.obj.hide_render=lod!=0
 return add,{'name':name,'width_m':w,'height_m':height,'center_m':list(center),'normal':list(n),'backing_offset_m':.022,'front_offset_m':.272,'ridge_offset_m':.372,'added':len(add),'closed_mesh':True,'front_face_samples_m':[list(v) for v in front],'back_face_samples_m':[list(v) for v in back],'street_reference_m':[2321,31,-16]}

def main():
 reset();current=read(H/'native.json');baseline=read(A/'block-native.json')
 patch={'level':'wascitya','source_fr3':current['source_fr3'],'preserve_bvh':True,'remove':[],'add':[]}
 report={'status':'authored','source_fr3':current['source_fr3'],'author_sha256':sha(__file__),'objects':[],'deleted_groups':[],'window_anchors':str(A/'window-anchors.json'),'window_anchors_sha256':sha(A/'window-anchors.json')}
 for lod in range(4):
  wall=bvh([f for f in current['faces'] if f['geom']==lod and f['tree_type']=='tie' and f['tree']==1 and f['group']==2 and 'stucco' in f['material']])
  draw=40 if lod<3 else 38
  for group in (5,6,7):
   targets=[f for f in current['faces'] if f['tree_type']=='tie' and f['geom']==lod and f['tree']==0 and f['draw']==draw and f['group']==group]
   original=[f for f in baseline['faces'] if f['tree_type']=='tie' and f['geom']==lod and f['tree']==0 and f['draw']==draw and f['group']==group]
   parts=component_faces(original)
   assert len(parts)==(2 if group in (6,9) else 1),(lod,group,len(parts))
   patch['remove'].extend({**{k:f[k] for k in ('tree_type','geom','tree','draw','group','stream_index')},'original_positions':[v['p'] for v in f['vertices']]} for f in targets)
   for ci,part in enumerate(parts):
    add,details=remodel(part,targets,wall,lod,f'House2 metal shield group{group}-{ci} LOD{lod}')
    patch['add'].extend(add);report['objects'].append({'lod':lod,'group':group,'source_components':len(parts),'source_faces':[f['stream_index'] for f in part],'source_vertices':sorted({v['index'] for f in part for v in f['vertices']}),**details})
 bpy.ops.wm.save_as_mainfile(filepath=str(H/'house2-metal-ornaments.blend'))
 write(H/'wascitya-patch.json',patch);write(H/'author-report.json',report)
 print('Removed',len(patch['remove']),'added',len(patch['add']))
if __name__=='__main__':main()
