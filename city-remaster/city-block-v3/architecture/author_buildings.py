"""Two real Spargus house remodels, native provenance, editable Blender output.

Import native houses; retain ground floor passage, cut through real wall faces,
build deep reveals, balconies and different roof volumes. Never writes game data.
"""
from pathlib import Path
from collections import Counter
import bpy, bmesh, sys, json, math, hashlib
from mathutils import Vector

H=Path(__file__).resolve().parent; R=H.parents[2]
sys.path.insert(0,str(R/'models-v1'))
from blender_common import NativeMesh,reset,render_asset

def read(p): return json.loads(Path(p).read_text())
def write(p,j): Path(p).write_text(json.dumps(j,indent=2)+'\n')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

# Each local frame is right-handed: right cross up = outward normal.
SPECS={
1:{'roof_raise':2.4,'windows':[
 {'id':'wca-house1-west-room','center':[2275.3,27.3,11.45],'normal':[-.437,0,-.900],'width':3.6,'height':3.0},
 {'id':'wca-house1-east-room','center':[2272.98,27.3,16.1],'normal':[-.922,0,.386],'width':3.6,'height':3.0},
 {'id':'wca-house1-upper-room','center':[2276.0,44.2,10.8],'normal':[-.440,0,-.898],'width':3.6,'height':3.7}],
 'dome':[2282.6,52.0,16.3,4.8,3.4]},
2:{'roof_raise':.9,'windows':[
 {'id':'wca-house2-street-room','center':[2339.35,20.5,-26.55],'normal':[-.874,0,.486],'width':3.4,'height':3.0},
 {'id':'wca-house2-upper-room','center':[2339.4,34.25,-26.5],'normal':[-.874,0,.486],'width':3.4,'height':3.8}],
 'dome':None}}

def frame(w):
 n=Vector(w['normal']).normalized();r=Vector((n.z,0,-n.x)).normalized();u=Vector((0,1,0))
 # Positive right is seen on the exterior observer's right.
 return Vector(w['center']),r,u,n

def clip(poly,axis,bound,keep_less):
 out=[]
 for i,a in enumerate(poly):
  b=poly[(i+1)%len(poly)];da=a[2][axis]-bound;db=b[2][axis]-bound
  ain=da<=1e-8 if keep_less else da>=-1e-8;bin=db<=1e-8 if keep_less else db>=-1e-8
  if ain:out.append(a)
  if ain!=bin:
   t=da/(da-db);out.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t)))
 return out

def cut_windows(native,windows):
 mesh=native.obj.data;outv=[];outf=[];outuv=[];outm=[];removed=0
 for face in mesh.polygons:
  poly=[(mesh.vertices[vi].co.copy(),mesh.uv_layers.active.data[li].uv.copy(),Vector()) for vi,li in zip(face.vertices,face.loop_indices)]
  polys=[poly]
  for w in windows:
   c,r,u,n=frame(w);nxt=[]
   for poly in polys:
    pp=[(a,b,Vector(((Vector(native.world(a))-c).dot(r),(Vector(native.world(a))-c).dot(u),(Vector(native.world(a))-c).dot(n)))) for a,b,_ in poly]
    z=[p[2].z for p in pp]
    if min(z)>2 or max(z)<-4:nxt.append(poly);continue
    inside=pp;outside=[]
    for axis,bound,less in [(0,-w['width']/2,False),(0,w['width']/2,True),(1,-w['height']/2,False),(1,w['height']/2,True)]:
     if len(inside)<3:break
     piece=clip(inside,axis,bound,not less)
     if len(piece)>=3:outside.append(piece)
     inside=clip(inside,axis,bound,less)
    if len(inside)>=3:removed+=1
    nxt.extend(outside)
   polys=nxt
  for poly in polys:
   ids=[]
   for p,uv,q in poly:ids.append(len(outv));outv.append(p)
   outf.append(ids);outuv.append([tuple(uv) for p,uv,q in poly]);outm.append(face.material_index)
 out=bpy.data.meshes.new(mesh.name+' real openings');out.from_pydata(outv,[],outf)
 for m in mesh.materials:out.materials.append(m)
 uv=out.uv_layers.new(name='UVMap')
 for p,mat,st in zip(out.polygons,outm,outuv):
  p.material_index=mat
  for li,t in zip(p.loop_indices,st):uv.data[li].uv=t
 out.update();native.obj.data=out
 return removed

def append_geometry(native,verts,faces,matname):
 mesh=native.obj.data;offset=len(mesh.vertices)
 vs=[v.co.copy() for v in mesh.vertices]+[native.local(p) for p in verts]
 fs=[list(p.vertices) for p in mesh.polygons]+[[i+offset for i in f] for f in faces]
 ms=[p.material_index for p in mesh.polygons]+[native.materials.index(matname)]*len(faces)
 uvs=[[tuple(mesh.uv_layers.active.data[li].uv) for li in p.loop_indices] for p in mesh.polygons]
 for f in faces:
  p=[Vector(verts[i]) for i in f];n=(p[1]-p[0]).cross(p[2]-p[0]).normalized();axes=[0,2] if abs(n.y)>.7 else ([2,1] if abs(n.x)>.7 else [0,1])
  uvs.append([(q[axes[0]]/4,q[axes[1]]/4) for q in p])
 out=bpy.data.meshes.new(mesh.name+' authored volumes');out.from_pydata(vs,[],fs)
 for m in mesh.materials:out.materials.append(m)
 uv=out.uv_layers.new(name='UVMap')
 for p,m,st in zip(out.polygons,ms,uvs):
  p.material_index=m
  for li,t in zip(p.loop_indices,st):uv.data[li].uv=t
 out.update();native.obj.data=out

def box(native,c,r,u,n,dimensions,material,bevel=.08):
 # Standalone closed volume, bevel only this new object, never the native shell.
 c=Vector(c);r=Vector(r);u=Vector(u);n=Vector(n);w,h,d=dimensions
 vs=[c+r*(x*w/2)+u*(y*h/2)+n*(z*d/2) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)]
 bm=bmesh.new();vv=[bm.verts.new(native.local(p)) for p in vs]
 for f in fs:bm.faces.new([vv[i] for i in f])
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bevel:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=bevel,segments=3,affect='EDGES')
 bm.verts.ensure_lookup_table();bm.verts.index_update();bm.normal_update()
 append_geometry(native,[native.world(v.co) for v in bm.verts],[[v.index for v in f.verts] for f in bm.faces],material);bm.free()

def window_architecture(native,w,lod):
 c,r,u,n=frame(w);width=w['width'];height=w['height'];m='wascity-stucco-wall-bleached-01'
 # Deep actual wall reveals have no plane across the opening.
 for sign in (-1,1):box(native,c+r*sign*(width/2+.20)-n*.16,r,u,n,(.42,height+.78,.96),m,.10)
 for sign in (-1,1):box(native,c+u*sign*(height/2+.19)-n*.13,r,u,n,(width+.84,.40,1.08),m,.10)
 # Small outer balcony adds a genuine floor and open side rail, not a decal.
 if 'upper' not in w['id']:
  base=c-u*(height/2+.52)+n*.62
  box(native,base,r,u,n,(width+1.35,.42,2.0),m,.16)
  rail=base+u*.87+n*.83
  box(native,rail,r,u,n,(width+1.22,.18,.22),m,.06)
  for k in range(7):box(native,base+r*((k/6-.5)*(width+.94))+n*.83+u*.45,r,u,n,(.12,.82,.15),m,.035)
  for sign in(-1,1):box(native,base+r*sign*(width/2+.54)+u*.87,r,u,n,(.18,.18,1.75),m,.045)

def roof_volumes(native,spec,lod):
 mesh=native.obj.data;lo=min(v.co.z for v in mesh.vertices);hi=max(v.co.z for v in mesh.vertices)
 # Lift the roof continuously through the upper floor; no detached shell seam.
 threshold=hi-8.2
 for v in mesh.vertices:
  if v.co.z>threshold:v.co.z+=spec['roof_raise']*min(1,(v.co.z-threshold)/7)
 mesh.update()
 # Capped raised terrace turret: broad low desert dome for house 1.
 if spec['dome']:
  x,y,z,radius,height=spec['dome']
  from mathutils.bvhtree import BVHTree
  top_bvh=BVHTree.FromPolygons([v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
  probe=native.local((x,80,z));hit=top_bvh.ray_cast(probe,Vector((0,0,-1)))
  if hit[0] is None:raise RuntimeError('Dome has no supporting native roof')
  y=native.world(hit[0])[1]-.12
  c=Vector((x,y,z));seg=32 if lod<2 else 16;rings=8 if lod<2 else 4
  vs=[];fs=[]
  for j in range(rings):
   t=j/(rings-1);rad=radius*math.cos(t*math.pi*.46);yy=height*math.sin(t*math.pi*.46)
   for i in range(seg):
    a=i*math.tau/seg;vs.append(list(c+Vector((rad*math.cos(a),yy,rad*math.sin(a)))))
  for j in range(rings-1):
   for i in range(seg):fs.append((j*seg+i,j*seg+(i+1)%seg,(j+1)*seg+(i+1)%seg,(j+1)*seg+i))
  fs.append(tuple(reversed(range(seg))));fs.append(tuple((rings-1)*seg+i for i in range(seg)))
  # Resolve winding on this closed, authored turret only.
  bm=bmesh.new();vv=[bm.verts.new(Vector(p)) for p in vs]
  for f in fs:bm.faces.new([vv[i] for i in f])
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.verts.index_update()
  append_geometry(native,[list(v.co) for v in bm.verts],[[v.index for v in f.verts] for f in bm.faces],'wascity-stucco-wall-bleached-01');bm.free()
 # Continuous roof parapet follows real roof boundaries, rather than floating trim.
 for f in native.faces:
  p=[Vector(v['p']) for v in f['vertices']];nn=(p[1]-p[0]).cross(p[2]-p[0]);
  if nn.length<1e-6 or nn.normalized().y<.45:continue
  if min(q.y for q in p)<native.origin.y+hi-4.5:continue
  for i in range(3):
   a,b=p[i],p[(i+1)%3];d=b-a
   if d.length<4 or abs(d.y)>1.5:continue
   # Only external roof contour edges, no source triangulation diagonals.
   occurrences=sum(any((Vector(g['vertices'][j]['p'])-a).length<.005 and (Vector(g['vertices'][(j+1)%3]['p'])-b).length<.005 or (Vector(g['vertices'][j]['p'])-b).length<.005 and (Vector(g['vertices'][(j+1)%3]['p'])-a).length<.005 for j in range(3)) for g in native.faces if (Vector(g['vertices'][1]['p'])-Vector(g['vertices'][0]['p'])).cross(Vector(g['vertices'][2]['p'])-Vector(g['vertices'][0]['p'])).normalized().y>.45)
   if occurrences!=1:continue
   a.y+=spec['roof_raise'];b.y+=spec['roof_raise'];rr=Vector((d.x,0,d.z)).normalized();nn=rr.cross(Vector((0,1,0)))
   box(native,(a+b)/2+Vector((0,.48,0)),rr,Vector((0,1,0)),nn,(d.length,.98,.56),'wascity-stucco-wall-bleached-01',.13)

def main():
 reset();old=read(R/'city-remaster/environment/architecture/wascitya-native.json');current=read(H/'block-native.json')
 patch={'level':'wascitya','source_fr3':current['source_fr3'],'preserve_bvh':True,'remove':[],'add':[]}
 report={'source_fr3':current['source_fr3'],'author_sha256':sha(__file__),'buildings':[],'native_validation':False}
 anchors=[]
 for inst,spec in SPECS.items():
  for w in spec['windows']:
   c,r,u,n=frame(w);anchors.append({**w,'center':list(c),'normal':list(n),'right':list(r),'up':list(u),'wall_depth':.5,'room_depth':2.0 if 'east-room' in w['id'] else 3.5,'building_native_instance':inst,'tree':1,'level':'wascitya','inhabited':inst==1 and 'upper' not in w['id'],'street_ground_y':19.1 if inst==1 else 9.56})
  for lod in range(4):
   base=[f for f in old['faces'] if f['tree']==1 and f['instance']==inst and f['geom']==lod]
   keys={(f['tree_type'],f['geom'],f['tree'],f['draw'],f['group']) for f in base}
   target=[f for f in current['faces'] if (f['tree_type'],f['geom'],f['tree'],f['draw'],f['group']) in keys]
   native=NativeMesh(f'Spargus real house {inst} LOD{lod}',base)
   if lod==0 and '--no-previews' not in sys.argv:render_asset(native.obj,H/f'house-{inst}-before.png',view=((-6,7,3) if inst==1 else (-6,-7,3)),resolution=1100)
   # Roof changes precede holes so their exact position stays stable.
   roof_volumes(native,spec,lod);cuts=cut_windows(native,spec['windows'])
   for w in spec['windows']:window_architecture(native,w,lod)
   rem,add,dev=native.records(target)
   valid=[]
   for f in add:
    a,b,c=[Vector(v['p']) for v in f['vertices']];n=(b-a).cross(c-a)
    if n.length<1e-8:continue
    n.normalize()
    for v in f['vertices']:v['normal']=list(n)
    valid.append(f)
   patch['remove'].extend(rem);patch['add'].extend(valid)
   report['buildings'].append({'instance':inst,'lod':lod,'source_triangles':len(base),'removed_triangles':len(rem),'added_triangles':len(valid),'cut_polygons':cuts,'max_distance_m':dev})
   if lod==0 and '--no-previews' not in sys.argv:render_asset(native.obj,H/f'house-{inst}-after.png',view=((-6,7,3) if inst==1 else (-6,-7,3)),resolution=1100)
   native.obj.location=(native.origin.x,-native.origin.z,native.origin.y)
   native.obj.hide_set(lod!=0);native.obj.hide_render=lod!=0
 # Original decorative window frames and dark interior cards are distinct
 # native draws, not part of the house's plaster mesh. Cut those actual
 # blockers too, preserving their geometry outside the new apertures.
 for lod in range(4):
  blockers=[(9,81),(44 if lod<3 else 42,34),(40 if lod<3 else 38,10)]
  for draw,group in blockers:
   target=[f for f in current['faces'] if f['tree_type']=='tie' and f['geom']==lod and f['tree']==0 and f['draw']==draw and f['group']==group]
   if not target:raise RuntimeError(f'Missing expected window occluder {lod}/{draw}/{group}')
   blocker=NativeMesh(f'Old opening occluder {lod} {draw} {group}',target)
   cuts=cut_windows(blocker,[w for spec in SPECS.values() for w in spec['windows']])
   if not cuts:
    blocker.obj.hide_set(True);blocker.obj.hide_render=True;continue
   rem,add,dev=blocker.records(target)
   patch['remove'].extend(rem);patch['add'].extend(add)
   report.setdefault('occluders',[]).append({'lod':lod,'draw':draw,'group':group,'removed':len(rem),'added':len(add),'cuts':cuts})
   blocker.obj.location=(blocker.origin.x,-blocker.origin.z,blocker.origin.y)
   blocker.obj.hide_set(True);blocker.obj.hide_render=True
 bpy.ops.wm.save_as_mainfile(filepath=str(H/'spargus-houses-v3.blend'))
 write(H/'window-anchors.json',anchors);write(H/'wascitya-patch.json',patch);write(H/'author-report.json',report)
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()
