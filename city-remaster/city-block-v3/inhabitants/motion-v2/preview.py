"""Render the exact exported animated vertices; not a game screenshot."""
from pathlib import Path
import bpy,json,math
import numpy as np
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent

def material(draw):
    name=draw['texture']
    mat=bpy.data.materials.get(name)
    if mat:return mat
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    p=nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.78
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(HERE/name));tex.interpolation='Linear'
    attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='native-linear-rgba'
    mult=nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1
    links.new(tex.outputs['Color'],mult.inputs[1]);links.new(attr.outputs['Color'],mult.inputs[2]);links.new(mult.outputs[0],p.inputs['Base Color'])
    return mat

def load_actor(sex,index):
    name='conversing-'+sex;meta=json.loads((HERE/(name+'.json')).read_text())
    values=np.fromfile(HERE/meta['binary'],dtype='<f4').reshape(meta['frame_count'],meta['vertex_count'],12)
    a=values[index]
    points=[(v[0],-v[2],v[1]) for v in a]
    faces=[(i,i+1,i+2) for i in range(0,len(a),3)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],faces);mesh.update()
    uv=mesh.uv_layers.new();colors=mesh.color_attributes.new(name='native-linear-rgba',type='FLOAT_COLOR',domain='CORNER')
    for i,v in enumerate(a):
        uv.data[i].uv=(v[6],1-v[7]);colors.data[i].color=(*v[8:11],1)
    for d in meta['draws']:
        mesh.materials.append(material(d));slot=len(mesh.materials)-1
        for p in mesh.polygons[d['first']//3:(d['first']+d['count'])//3]:p.material_index=slot;p.use_smooth=True
    mesh.normals_split_custom_set([(v[3],-v[5],v[4]) for v in a])
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    if sex=='male':obj.location=(.25,2.15,.058);obj.rotation_euler.z=math.atan2(1.2,-.9)
    else:obj.location=(1.45,3.05,.058);obj.rotation_euler.z=math.atan2(-1.2,.9)
    return obj

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40
    scene.world=bpy.data.worlds.new('neutral preview');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.17,.19,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.55
    for location,power,size in [((1,-2,5),600,5),((-2,3,4),450,4)]:
        data=bpy.data.lights.new('soft preview light','AREA');data.energy=power;data.size=size
        obj=bpy.data.objects.new('soft preview light',data);scene.collection.objects.link(obj);obj.location=location
        obj.rotation_euler=(Vector((1,2.5,1))-obj.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.058))
    plane=bpy.context.object;plane.name='preview floor at room elevation'
    mat=bpy.data.materials.new('neutral floor');mat.diffuse_color=(.18,.20,.21,1);plane.data.materials.append(mat)
    camera_data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',camera_data);scene.collection.objects.link(camera)
    camera.location=(2,-3.7,2.7);camera.rotation_euler=(Vector((.85,2.6,1.04))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO';camera_data.ortho_scale=3.6;scene.camera=camera
    scene.render.resolution_x=1280;scene.render.resolution_y=960;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    for i in (0,6,12,22):
        objects=[load_actor(s,i) for s in ('male','female')]
        scene.render.filepath=str(HERE/('pair-frame-%02d.png'%i));bpy.ops.render.render(write_still=True)
        if i==6:
            bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'pair-preview.blend'))
            camera.location=(-3.7,1.5,2.5);camera.rotation_euler=(Vector((.85,2.6,1.04))-camera.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(HERE/'pair-frame-06-side.png');bpy.ops.render.render(write_still=True)
            camera.location=(2,-3.7,2.7);camera.rotation_euler=(Vector((.85,2.6,1.04))-camera.location).to_track_quat('-Z','Y').to_euler()
        for obj in objects:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
    print('Exported-vertex pair previews complete; these are Blender renders, not native gameplay.',flush=True)

if __name__=='__main__':main()
