import bpy, json
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'active/jak3/data/decompiler_out/jak3/levels/wascityb/wascity-awning-b-lod0.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
report={'bones':[{'name':b.name,'head':list(b.head_local),'tail':list(b.tail_local)}for b in rig.data.bones],'meshes':[]}
points=[]
for o in meshes:
    used=sorted({i for p in o.data.polygons for i in p.vertices})
    pts=[o.matrix_world@o.data.vertices[i].co for i in used];points+=pts
    report['meshes'].append({'name':o.name,'bounds':[[min(p[a]for p in pts)for a in range(3)],[max(p[a]for p in pts)for a in range(3)]],
        'materials':[m.name for m in o.data.materials],
        'vertices':{str(i):{'co':list(o.data.vertices[i].co),'weights':[[o.vertex_groups[g.group].name,g.weight]for g in o.data.vertices[i].groups]}for i in used},
        'faces':[{'v':list(p.vertices),'material':p.material_index}for p in o.data.polygons]})
    for material in o.data.materials:
        for node in material.node_tree.nodes:
            if node.type=='TEX_IMAGE':
                name=material.name.replace('/','-')+'-original.png'
                node.image.filepath_raw=str(HERE/name);node.image.file_format='PNG';node.image.save()
lo=Vector([min(p[a]for p in points)for a in range(3)]);hi=Vector([max(p[a]for p in points)for a in range(3)])
c=(lo+hi)/2;size=max(hi-lo)
bpy.ops.object.camera_add(location=c+Vector((1.3,-1.6,.85))*size)
cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size*1.6
scene=bpy.context.scene;scene.camera=cam
for xyz,power in [((1,-1,2),90),((-1,-.5,1),40),((0,2,2),70)]:
    bpy.ops.object.light_add(type='AREA',location=c+Vector(xyz)*size)
    light=bpy.context.object;light.data.energy=power*size*size;light.data.size=size*2;light.rotation_euler=(c-light.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('Neutral');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.16,1)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(HERE/'awning-source.png');scene.view_settings.view_transform='AgX'
(HERE/'awning-source-inspection.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'awning-source.blend'))
bpy.ops.render.render(write_still=True)
print('AWNING',[(m['name'],m['bounds'],m['materials'])for m in report['meshes']],flush=True)
