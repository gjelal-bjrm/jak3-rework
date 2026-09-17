"""Author one corner room, shared by both original house-1 windows."""
from pathlib import Path
import bpy,json,hashlib,shutil
from mathutils import Vector
H=Path(__file__).resolve().parent
SOURCE=H.parent
ns={'__file__':str(SOURCE/'author_rooms.py')}
exec(compile((SOURCE/'author_rooms.py').read_text().split("\nfor layout in('lounge','conversation'):")[0],str(SOURCE/'author_rooms.py'),'exec'),ns)
ns['scene']('conversation')
remove=('rear plaster wall','left plaster wall','right plaster wall','ceiling','floor','roof timber','beam bronze strap','wall foot course')
for o in list(bpy.context.scene.objects):
    if o.type=='MESH' and o.name.startswith(remove):bpy.data.objects.remove(o,do_unlink=True)
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    # All furnishings occupy one physical room. Window changes never spawn copies.
    o.location.x+=.55
    if o.name.startswith(('wall bench','bench cushion','wall textile','textile')):
        o.location.y+=1.45
    if o.name.startswith(('storage shelf','shelf bracket','shelf clay jar')):
        o.location.x-=3.2
        o.location.y+=.65
ns['cube']('shared rear wall',(.60,1.65,-5.24),(5.8,3.3,.16),0,.035)
ns['cube']('shared left wall',(-2.3,1.65,-2.66),(.16,3.3,5.25),0,.035)
# The right facade is slightly oblique (93.18 degrees to front).
# Leave both native facade openings unobstructed; floor/ceiling stay inside them.
def right(z):return 4.1181175-.0555984*(z+2.629595)-.70
poly=[(-2.3,-.12),(right(-.12),-.12),(right(-5.16),-5.16),(-2.3,-5.16)]
def panel(name,y,mat):
    verts=[ns['local']((x,y,z))for x,z in poly]
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],[(0,1,2,3)]);m.update()
    o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);ns['finish'](o,name,mat)
panel('shared floor',-.035,1);panel('shared ceiling',3.27,0)
for x in(-1.55,-.2,1.15,2.5):
    ns['cube']('shared ceiling timber',(x,3.15,-2.64),(.17,.23,5.05),2,.035)
for x in(-.80,1.00):
    ns['cube']('bench solid foot',(x,.20,-4.50),(.16,.40,.50),2,.025)
ns['H']=3.3;ns['W']=6.7;ns['D']=5.24
out=H/'no-ao';out.mkdir(parents=True,exist_ok=True);ns['HERE']=out
ns['export']([o for o in bpy.context.scene.objects if o.type=='MESH'],'corner-conversation')
bpy.ops.wm.save_as_mainfile(filepath=str(H/'corner-conversation.blend'))
# Reuse the established neutral vertex contact-occlusion bake, with fresh geometry.
bake=(SOURCE/'ao-candidate/bake.py').read_text().replace("for layout in ('lounge','conversation'):","for layout in ('corner-conversation',):")
ao=H/'ao';ao.mkdir(exist_ok=True)
bn={'__file__':str(ao/'bake.py'),'__name__':'shared_corner_bake'}
exec(compile(bake,str(SOURCE/'ao-candidate/bake.py'),'exec'),bn)
bn['HERE']=ao;bn['SOURCE']=out;bn['main']()
for ext in('.bin','.json'):shutil.copy2(ao/('corner-conversation'+ext),H/('corner-conversation'+ext))
meta=json.loads((H/'corner-conversation.json').read_text())
assert meta['vertex_ao']['minimum']>=.6
(H/'author-report.json').write_text(json.dumps({
'mesh':meta['binary'],'sha256':meta['sha256'],'shared_windows':['wca-house1-west-room','wca-house1-east-room'],
'floor_polygon_xz':poly,'floor_y':-.035,'ceiling_y':3.27,
'one_world_instance':True,'front_and_right_walls':'native facade with real openings',
'occupants':[{'mesh':'conversing-male','position':[.25,.058,-2.15],'yaw':2.214297435588181},
{'mesh':'conversing-female','position':[1.45,.058,-3.05],'yaw':-0.9272952180016122}],
'author_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))
print('Shared corner room authored and baked',flush=True)
