import bpy, json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'active/jak3/data/decompiler_out/jak3/levels/wascityb/cty-fruit-stand-lod0.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report=[]; points=[]
for o in meshes:
    pts=[o.matrix_world@v.co for v in o.data.vertices];points+=pts
    report.append({'object':o.name,'matrix':list(sum((list(r) for r in o.matrix_world),[])),
        'bounds':[[min(p[a] for p in pts) for a in range(3)],[max(p[a] for p in pts) for a in range(3)]],
        'groups':[g.name for g in o.vertex_groups],
        'vertices':[{'co':list(v.co),'weights':[[o.vertex_groups[g.group].name,g.weight] for g in v.groups]} for v in o.data.vertices],
        'faces':[list(p.vertices) for p in o.data.polygons]})
(HERE/'stand-source-inspection.json').write_text(json.dumps(report,indent=2))
lo=Vector([min(p[a] for p in points) for a in range(3)]);hi=Vector([max(p[a] for p in points) for a in range(3)])
c=(lo+hi)/2;size=max(hi-lo)
for o in meshes:
    for m in o.data.materials:
        if m and m.use_nodes:
            bs=m.node_tree.nodes.get('Principled BSDF')
            if bs:bs.inputs['Roughness'].default_value=.8
bpy.ops.object.camera_add(location=c+Vector((1.25,-1.65,1.1))*size)
cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size*1.52
scene=bpy.context.scene;scene.camera=cam
for xyz,power,scale in [((1,-1,2),1300,3),((-1,-.5,1),750,3),((0,2,2),1100,2)]:
    bpy.ops.object.light_add(type='AREA',location=c+Vector(xyz)*size)
    light=bpy.context.object;light.data.energy=power*size*size;light.data.shape='DISK';light.data.size=scale*size;light.rotation_euler=(c-light.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('Neutral');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.16,1)
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(HERE/'stand-source.png')
scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'stand-source.blend'))
bpy.ops.render.render(write_still=True)
print('BOUNDS',list(lo),list(hi),flush=True)
