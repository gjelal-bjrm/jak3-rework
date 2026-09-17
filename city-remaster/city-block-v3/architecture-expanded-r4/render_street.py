"""Full native street geometry previews; albedo work lighting, no runtime."""
from pathlib import Path
import json,sys,math,bpy
from mathutils import Vector
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'models-v1'));from blender_common import NativeMesh,reset
def read(p):return json.loads(Path(p).read_text())
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
p=read(H/'wascitya-patch.json');removed={key(f) for f in p['remove']}
for w in read(H/'new-window-specs.json'):
 s=read(H/('native-'+w['region']+'.json'));lookup={(f['geom'],f['tree'],f['draw'],f['group']):f for f in s['faces'] if f['tree_type']=='tie'}
 fs=[f for f in s['faces'] if f['geom']==0 and key(f) not in removed]
 for f in p['add']:
  if f['geom']!=0:continue
  k=(f['geom'],f['tree'],f['draw'],f['group'])
  if k not in lookup:continue
  c=sum((Vector(v['p']) for v in f['vertices']),Vector())/3
  if (c-Vector(w['center'])).length>55:continue
  t=lookup[k];fs.append({**f,'material':t['material'],'page':t['page']})
 reset();native=NativeMesh(w['region']+' full street context',fs,origin=w['center'])
 for m in native.obj.data.materials:
  shader=m.node_tree.nodes.get('Principled BSDF');tex=next(n for n in m.node_tree.nodes if n.type=='TEX_IMAGE');m.node_tree.links.new(tex.outputs['Color'],shader.inputs['Emission Color']);shader.inputs['Emission Strength'].default_value=.85
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard';scene.world.color=(.5,.5,.5)
 data=bpy.data.cameras.new('Street camera');cam=bpy.data.objects.new('Street camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.angle=math.radians(75)
 cam.location=native.local(w['street_camera']);target=native.local(w['center']);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();data.clip_end=250
 scene.render.filepath=str(H/('street-'+w['region']+'.png'));bpy.ops.render.render(write_still=True)
