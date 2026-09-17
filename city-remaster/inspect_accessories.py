import bpy, json, math, ast
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'active/jak3/data/decompiler_out/jak3/levels/wascityb'
NAMES=['market-crate-lod0','market-basket-a-lod0','market-basket-b-lod0','market-sack-a-lod0','market-sack-b-lod0']
BOUNDS=next(ast.literal_eval(n.value) for n in ast.parse((HERE/'author_accessories.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BOUNDS' for t in n.targets))
reports=[]
for name in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE/(name+'.glb')))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[]; objects=[]
    for o in meshes:
        ids=sorted(set(v for f in o.data.polygons for v in f.vertices))
        points.extend(o.matrix_world@o.data.vertices[i].co for i in ids)
        objects.append({'name':o.name,'materials':[m.name for m in o.data.materials],
                        'vertices':[{'p':list(v.co),'weights':[[o.vertex_groups[g.group].name,g.weight] for g in v.groups]} for v in o.data.vertices],
                        'faces':[{'vertices':list(f.vertices),'material':f.material_index} for f in o.data.polygons]})
    lo=Vector([min(p[a] for p in points) for a in range(3)]);hi=Vector([max(p[a] for p in points) for a in range(3)])
    reports.append({'control':name,'bounds_blender_import':[list(lo),list(hi)],'bounds_indexed_native_blender_axes':BOUNDS[name],'objects':objects})
    # Native GLBs contain imported helper vertices; identical comparison cameras
    # are derived from the indexed native bounds used by the replacement.
    lo,hi=map(Vector,BOUNDS[name]);c=(lo+hi)/2;size=max(hi-lo)
    bpy.ops.object.camera_add(location=c+Vector((1.3,-1.7,1.15))*size)
    camera=bpy.context.object;camera.rotation_euler=(c-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=size*1.52
    scene=bpy.context.scene;scene.camera=camera
    for xyz,power,scale in [((1,-1,2),60,3),((-1,-.5,1),28,3),((0,2,2),55,2)]:
        bpy.ops.object.light_add(type='AREA',location=c+Vector(xyz)*size)
        light=bpy.context.object;light.data.energy=power*size*size;light.data.shape='DISK';light.data.size=scale*size;light.rotation_euler=(c-light.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Neutral');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.16,1)
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1000;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(HERE/(name+'-source.png'));scene.view_settings.view_transform='AgX'
    bpy.ops.render.render(write_still=True)
(HERE/'accessories-source-inspection.json').write_text(json.dumps(reports,indent=2))
