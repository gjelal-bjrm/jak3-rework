"""Review full exported block from the native QA camera, not an isolated asset."""
from pathlib import Path
import json,sys,math,bpy
from mathutils import Vector
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'models-v1'))
from blender_common import NativeMesh,reset
s=json.loads((H/'native.json').read_text());p=json.loads((H/'wascitya-patch.json').read_text())
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
removed={key(f) for f in p['remove']};lookup={(f['geom'],f['tree'],f['draw'],f['group']):f for f in s['faces'] if f['tree_type']=='tie'}
fs=[f for f in s['faces'] if f['geom']==0 and key(f) not in removed]
for f in p['add']:
 if f['geom']!=0:continue
 t=lookup[f['geom'],f['tree'],f['draw'],f['group']]
 fs.append({**f,'material':t['material'],'page':t['page']})
reset();native=NativeMesh('Complete native block with corrected street-side shields',fs,origin=(2321,0,-16))
# These are geometry QA previews. Emissive albedo makes double-sided native
# surfaces readable without pretending to reproduce OpenGOAL's baked lighting.
for material in native.obj.data.materials:
 shader=material.node_tree.nodes.get('Principled BSDF')
 tex=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE')
 material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Emission Color'])
 shader.inputs['Emission Strength'].default_value=.8
def transform(p):return native.local(Vector(p))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.world.color=(.7,.7,.7);scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
ld=bpy.data.lights.new('Broad sun','SUN');ld.energy=2.2;ld.angle=.15
light=bpy.data.objects.new('Broad sun',ld);scene.collection.objects.link(light);light.rotation_euler=(.8,-.2,-.7)
camdata=bpy.data.cameras.new('Native QA camera');cam=bpy.data.objects.new('Native QA camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='PERSP';camdata.angle=math.radians(70);camdata.clip_end=1000
pos=Vector((2321,31,-16));target=Vector((2342,27,-21));f=(target-pos).normalized();right=Vector((f.z,0,-f.x)).normalized()
for label,offset in [('native',0),('open-angle',-2)]:
 cam.location=transform(pos+right*offset);cam.rotation_euler=(transform(target)-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(H/('fullblock-'+label+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(H/'house2-native-camera-fullblock.blend'))
