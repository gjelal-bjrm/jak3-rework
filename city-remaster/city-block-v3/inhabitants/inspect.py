import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sex=sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(HERE/(sex+'-selected.glb')))
meshes=[o for o in bpy.data.objects if o.type=='MESH'];arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
info={'objects':[(o.name,o.type,[list(row)for row in o.matrix_world])for o in bpy.data.objects],
 'bones':{b.name:{'head':list(b.head),'tail':list(b.tail),'matrix':[list(r)for r in b.matrix]}for b in arm.pose.bones},
 'actions':[(a.name,list(a.frame_range))for a in bpy.data.actions]}
(HERE/(sex+'-rig-info.json')).write_text(json.dumps(info,indent=2))
arm.animation_data_clear()
for b in arm.pose.bones:b.matrix_basis.identity()
bpy.context.view_layer.update()
for o in meshes:
 for p in o.data.polygons:p.use_smooth=True
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24
sc.world=bpy.data.worlds.new('World');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.12,.12,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.7
for pos,power,size in [((4,-4,6),650,5),((-4,1,4),400,4)]:
 d=bpy.data.lights.new('softbox','AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new('softbox',d);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camd);sc.collection.objects.link(cam);cam.location=(5,-8,3.3);cam.rotation_euler=(Vector((0,0,1.5))-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=3.8;sc.camera=cam
sc.render.resolution_x=720;sc.render.resolution_y=800;sc.render.resolution_percentage=100;sc.view_settings.view_transform='AgX'
sc.render.filepath=str(HERE/(sex+'-selected-rest.png'));bpy.ops.render.render(write_still=True)
