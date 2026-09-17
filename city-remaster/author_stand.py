"""Rebuild the market display in its native footprint, keeping the original rig."""
import bpy, math, json, random
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'active/jak3/data/decompiler_out/jak3/levels/wascityb/cty-fruit-stand-lod0.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
old=next(o for o in bpy.context.scene.objects if o.type=='MESH')
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
material=old.data.materials[0];parts=[]
hd=HERE/'wood-hd-v2.png'
if not hd.exists():hd=HERE/'wood-hd.png'
if hd.exists():
    image=bpy.data.images.load(str(hd),check_existing=True)
    for node in material.node_tree.nodes:
        if node.type=='TEX_IMAGE':node.image=image
angle=math.atan2(1.465,2.564)
# Native display bed slopes upward toward the back. Its fruit plane is retained.
def deck(x,y,z=0):return Vector((x,y,.110+(y+1.172)*(1.465/2.564)+z))
def timber(name,centre,dimensions,angle_y=0,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=centre)
    o=bpy.context.object;o.name=name;o.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if angle_y:o.rotation_euler[0]=angle_y
    o.data.materials.append(material)
    for p in o.data.polygons:p.use_smooth=False
    mod=o.modifiers.new('Worn rounded timber edges','BEVEL');mod.width=bevel;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Each board has its own long grain. No broad fake masonry or colour swap.
    uv=o.data.uv_layers.active
    rng=random.Random(name+str(tuple(round(x,3) for x in centre)))
    strip_center=.3+rng.random()*.4
    for p in o.data.polygons:
        axes=sorted(range(3),key=lambda a:abs(p.normal[a]))[:2]
        # Grain follows the length of each separate piece, including the legs.
        a,b=sorted(axes,key=lambda a:dimensions[a],reverse=True)
        for li in p.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co
            strip_width=min(.48,dimensions[b]/1.2)
            uv.data[li].uv=(co[a]/max(dimensions[a],.01)*.88+.5,co[b]/max(dimensions[b],.01)*strip_width+strip_center)
    parts.append(o);return o
def beam_between(name,a,b,width,depth):
    a,b=Vector(a),Vector(b);o=timber(name,(a+b)/2,(width,depth,(b-a).length),bevel=.028)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def cord(name,points,radius=.019):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=2
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for dest,point in zip(spline.points,points):dest.co=(*point,1)
    curve.bevel_depth=radius;curve.bevel_resolution=1;curve.resolution_u=2
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.ops.object.convert(target='MESH')
    parts.append(bpy.context.object)
# Individually fitted bed boards: shallow seams, full underside and real thickness.
board_count=15
for i in range(board_count):
    x=-4.255+(i+.5)*8.51/board_count
    # Broad sawn boards, slightly unequal end cuts, with a stable fruit plane.
    # The shallow worn edge is modeled rather than painted as a stripe.
    timber('Display bed board %02d'%i,deck(x,.04+.012*math.sin(i*4.1),-.09),
           (8.51/board_count-.012,2.89+.025*math.sin(i*2.3),.15),angle,bevel=.022)
# Sloped outer frame and two original compartment divisions; low lips retain fruit.
for x in (-4.44,-1.58,1.56,4.44):
    timber('Rebated tray rail',deck(x,.03,.16),(.235,3.04,.36),angle,bevel=.035)
for y in (-1.29,1.29):
    timber('Continuous rounded rim',deck(0,y,.15),(8.91,.235,.37),angle,bevel=.04)
    timber('Lower rim moulding',deck(0,y,-.115),(9.01,.265,.085),angle,bevel=.018)
# Indexed native geometry starts at -0.256 m. The glTF also contains unused
# helper vertices at -1 m; those must not set the visible ground footprint.
floor=-.256
for x in (-4.25,4.25):
    for y in (-1.07,1.07):
        z=deck(x,y,-.13).z
        post=timber('Tapered foot post',(x,y,(z+floor)/2),(.36,.40,max(z-floor,.08)),bevel=.035)
        # Flared feet and a slightly bowed shaft replace the straight source slab.
        for vertex in post.data.vertices:
            t=(vertex.co.z/max(z-floor,.08))+.5
            factor=.86+.27*(2*t-1)**2
            vertex.co.x*=factor;vertex.co.y*=factor
            vertex.co.x+=math.copysign(.035,x)*math.sin(t*math.pi)
        timber('Mortise shoulder collar',(x,y,z-.14),(.49,.49,.18),bevel=.024)
    beam_between('Side bracing',(x,-1.10,-.12),(x,1.09,1.13),.18,.19)
    beam_between('Side bracing',(x,1.10,-.12),(x,-1.09,-.03),.18,.19)
    timber('Low side stretcher',(x,0,-.14),(.23,2.42,.20),bevel=.025)
for y in (-1.03,1.03):
    timber('Long structural stretcher',(0,y,-.14),(8.58,.22,.20),bevel=.025)
    for x in (-4.25,-1.56,1.56,4.25):
        # Wooden pegs are modeled joinery, not shiny decorative metal additions.
        bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=.055,depth=.04,location=(x,y+math.copysign(.23,y),deck(x,y,-.10).z),rotation=(math.pi/2,0,0))
        p=bpy.context.object;p.name='Recessed end-grain peg';p.data.materials.append(material);parts.append(p)
# Removable tray edges have rounded corners and distinct slats. They retain the
# native three fruit compartments, but read as built display bins instead of a
# single rectangular polygon with a painted rim.
for bin_index,(a,b) in enumerate([(-4.24,-1.76),(-1.38,1.36),(1.77,4.23)]):
    for y in [-1.105,1.065]:
        timber('Inset display bin lip',deck((a+b)/2,y,.055),(b-a,.082,.105),angle,bevel=.035)
    for x in [a,b]:
        timber('Inset display bin side',deck(x,-.02,.055),(.082,2.48,.105),angle,bevel=.035)
# Rope repairs near the frame corners add construction detail without changing
# the passages, floor plane or the fruit launch positions.
for x in [-4.30,4.30]:
    for y in [-1.08,1.08]:
        for k in range(3):
            points=[]
            for n in range(25):
                theta=2*math.pi*n/24
                points.append(deck(x+math.cos(theta)*.18,y+(k-1)*.042,.12+math.sin(theta)*.22))
            cord('Wound frame lashing',points,.018)
# Keep all skin vertices assigned to the same native main joint as the old 78 triangles.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
new=bpy.context.object;new.name='cty-fruit-stand-lod0-authored'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for g in old.vertex_groups:new.vertex_groups.new(name=g.name)
new.vertex_groups['main'].add(list(range(len(new.data.vertices))),1.,'REPLACE')
new.parent=old.parent
mod=new.modifiers.new('Native market rig','ARMATURE');mod.object=rig
if old.data.color_attributes:
    original=old.data.color_attributes[0]
    mean=[sum(c.color[k] for c in original.data)/len(original.data) for k in range(4)]
    col=new.data.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
    # A restrained crevice tint makes the joinery readable under the native
    # broad outdoor light. It is attached to the object, not a fake moving shadow.
    for li,c in enumerate(col.data):
        v=new.data.vertices[new.data.loops[li].vertex_index].co
        gain=.98
        if abs(v.x)<4.31 and abs(v.y)<1.20 and v.z>deck(v.x,v.y,-.15).z:
            d=min(abs(v.x-x) for x in (-4.44,-1.58,1.56,4.44))
            d=min(d,abs(v.y+1.29),abs(v.y-1.29))
            gain*=1.-.16*math.exp(-d/.16)
            board=int((v.x+4.255)*board_count/8.51)
            gain*=.97+.03*math.sin(board*2.13)
        elif v.z<deck(v.x,v.y,-.20).z:
            gain*=.84
        c.color=tuple(mean[k]*gain for k in range(3))+(mean[3],)
bpy.data.objects.remove(old,do_unlink=True);new.name='cty-fruit-stand-lod0'
new.data.calc_loop_triangles()
report={'source_triangles':78,'authored_triangles':len(new.data.loop_triangles),'vertices':len(new.data.vertices),'joint_names':[g.name for g in new.vertex_groups],'weights':'all main, matching original','fruit_plane':'native slope retained','board_count':board_count,'surface':'broad sawn boards, shallow worn edges, subdued joinery crevices','texture':str(hd) if hd.exists() else 'original city-slum-wood-plain, HD pass pending','installed':False}
(HERE/'stand-author-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='DESELECT');new.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=new
bpy.ops.export_scene.gltf(filepath=str(HERE/'cty-fruit-stand-lod0.glb'),export_format='GLB',use_selection=True,export_animations=False,export_apply=False,export_extras=True,
                          export_vertex_color='NAME',export_vertex_color_name='COLOR_0',export_all_vertex_colors=False)
# A neutral studio preview is authoring evidence only, never a native-game claim.
pts=[new.matrix_world@v.co for v in new.data.vertices]
lo=Vector([min(p[a] for p in pts) for a in range(3)]);hi=Vector([max(p[a] for p in pts) for a in range(3)])
c=(lo+hi)/2;size=max(hi-lo)
bpy.ops.object.camera_add(location=c+Vector((1.25,-1.65,1.1))*size)
cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size*1.52
scene=bpy.context.scene;scene.camera=cam
for xyz,power,scale in [((1,-1,2),70,3),((-1,-.5,1),35,3),((0,2,2),60,2)]:
    bpy.ops.object.light_add(type='AREA',location=c+Vector(xyz)*size)
    light=bpy.context.object;light.data.energy=power*size*size;light.data.shape='DISK';light.data.size=scale*size;light.rotation_euler=(c-light.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('Neutral');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.16,1)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(HERE/'stand-authored.png')
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'market-stand.blend'))
bpy.ops.render.render(write_still=True)
print(json.dumps(report),flush=True)
