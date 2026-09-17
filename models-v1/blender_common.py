"""Native coordinates, UVs, materials and diagnostic renders for Blender assets."""
from pathlib import Path
import bpy,bmesh,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import closest_point_on_tri
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent

def reset():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def load_material(name,page):
    if name in bpy.data.materials:return bpy.data.materials[name]
    material=bpy.data.materials.new(name);material.use_nodes=True
    path=ROOT/'data/custom_assets/jak3/texture_replacements'/page/(name+'.png')
    if not path.exists():path=ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/textures'/page/(name+'.png')
    texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(path),check_existing=True)
    texture.image.pack();shader=material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.6
    material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
    if 'leaf' in name or 'beard' in name:
        material.node_tree.links.new(texture.outputs['Alpha'],shader.inputs['Alpha'])
    return material

class NativeMesh:
    def __init__(self,name,faces,origin=None):
        self.faces=faces
        points=[Vector(v['p']) for f in faces for v in f['vertices']]
        self.origin=Vector(origin) if origin is not None else Vector([(min(p[a] for p in points)+max(p[a] for p in points))*.5 for a in range(3)])
        self.materials=sorted({f['material'] for f in faces});self.vertices=[];self.triangles=[];weld={}
        for f in faces:
            triangle=[]
            for v in f['vertices']:
                key=tuple(round(x*1000) for x in v['p'])
                if key not in weld:weld[key]=len(self.vertices);self.vertices.append(self.local(v['p']))
                triangle.append(weld[key])
            self.triangles.append(triangle)
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.vertices,[],self.triangles);mesh.update()
        self.obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(self.obj)
        for name in self.materials:mesh.materials.append(load_material(name,next(f['page'] for f in faces if f['material']==name)))
        uv=mesh.uv_layers.new(name='UVMap')
        for polygon,face in zip(mesh.polygons,faces):
            polygon.material_index=self.materials.index(face['material'])
            for loop,v in zip(polygon.loop_indices,face['vertices']):uv.data[loop].uv=(v['uv'][0],1-v['uv'][1])
        self.bvh=BVHTree.FromPolygons(self.vertices,self.triangles,all_triangles=True)
        self.obj['native_origin']=list(self.origin)

    def local(self,p):
        q=Vector(p)-self.origin;return Vector((q.x,-q.z,q.y))
    def world(self,p):return list(self.origin+Vector((p.x,p.z,-p.y)))

    def weights(self,p,index):
        a,b,c=[self.vertices[i] for i in self.triangles[index]]
        p=closest_point_on_tri(p,a,b,c);u=b-a;v=c-a;w=p-a
        aa=u.dot(u);ab=u.dot(v);bb=v.dot(v);wa=w.dot(u);wb=w.dot(v);denom=aa*bb-ab*ab
        if abs(denom)<1e-12:return [1,0,0]
        bw=(bb*wa-ab*wb)/denom;cw=(aa*wb-ab*wa)/denom
        return [1-bw-cw,bw,cw]

    def assign_uv(self,only_selected=False):
        self.obj.data.update()
        uv=self.obj.data.uv_layers.active
        if uv is None:uv=self.obj.data.uv_layers.new(name='UVMap')
        surfaces={}
        for material in self.materials:
            ids=[i for i,f in enumerate(self.faces) if f['material']==material]
            surfaces[material]=(BVHTree.FromPolygons(self.vertices,[self.triangles[i] for i in ids],all_triangles=True),ids)
        for polygon in self.obj.data.polygons:
            if only_selected and not polygon.select:continue
            point=sum((self.obj.data.vertices[i].co for i in polygon.vertices),Vector())/len(polygon.vertices)
            surface,ids=surfaces[self.materials[polygon.material_index]]
            for loop,vi in zip(polygon.loop_indices,polygon.vertices):
                co=self.obj.data.vertices[vi].co
                _,_,mi,_=surface.find_nearest(co.lerp(point,.00001));index=ids[mi];face=self.faces[index]
                weight=self.weights(co,index)
                st=[sum(weight[i]*face['vertices'][i]['uv'][axis] for i in range(3)) for axis in range(2)]
                uv.data[loop].uv=(st[0],1-st[1])

    def records(self,target_faces):
        target=NativeMesh.__new__(NativeMesh);target.faces=target_faces;target.origin=self.origin
        target.vertices=[];target.triangles=[]
        for face in target_faces:
            start=len(target.vertices);target.vertices.extend(self.local(v['p']) for v in face['vertices']);target.triangles.append([start,start+1,start+2])
        bvh=BVHTree.FromPolygons(target.vertices,target.triangles,all_triangles=True)
        by_material={}
        for material in self.materials:
            ids=[i for i,f in enumerate(target_faces) if f['material']==material]
            if ids:by_material[material]=(BVHTree.FromPolygons(target.vertices,[target.triangles[i] for i in ids],all_triangles=True),ids)
        remove=[{**{k:f[k] for k in ('tree_type','geom','tree','draw','group','stream_index')},'original_positions':[v['p'] for v in f['vertices']]} for f in target_faces]
        add=[];maximum=0
        self.obj.data.calc_loop_triangles()
        for triangle in self.obj.data.loop_triangles:
            coords=[self.obj.data.vertices[i].co for i in triangle.vertices]
            centre=sum(coords,Vector())/3
            material=self.materials[triangle.material_index]
            if material in by_material:
                material_bvh,ids=by_material[material];_,_,mi,_=material_bvh.find_nearest(centre);index=ids[mi]
            else:_,_,index,_=bvh.find_nearest(centre)
            face=target_faces[index]
            record={k:face[k] for k in ('tree_type','geom','tree','draw','group')};record['vertices']=[]
            for vi,co,loop in zip(triangle.vertices,coords,triangle.loops):
                # Colour belongs to the vertex position, not to the nearest face
                # at the new triangle's centre. The latter creates visible seams
                # when a retopologized triangle spans several original faces.
                if material in by_material:
                    material_bvh,ids=by_material[material];_,_,mi,_=material_bvh.find_nearest(co);ci=ids[mi]
                else:_,_,ci,_=bvh.find_nearest(co)
                colour_face=target_faces[ci];weights=target.weights(co,ci)
                uv=self.obj.data.uv_layers.active.data[loop].uv
                normal=self.obj.data.vertices[vi].normal if self.obj.data.polygons[triangle.polygon_index].use_smooth else triangle.normal
                record['vertices'].append({'p':self.world(co),'uv':[uv.x,1-uv.y],
                    'normal':[normal.x,normal.z,-normal.y],
                    'color_indices':[v['color'] for v in colour_face['vertices']],'color_weights':weights})
                if 'rgba' in colour_face['vertices'][0]:
                    record['vertices'][-1]['rgba']=[round(sum(weights[k]*colour_face['vertices'][k]['rgba'][c] for k in range(3))) for c in range(3)]
                maximum=max(maximum,bvh.find_nearest(co)[3])
            add.append(record)
        return remove,add,maximum

def render_asset(obj,path,view=(4,-7,3),resolution=1000):
    for other in bpy.context.scene.objects:other.hide_render=other!=obj
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.render.resolution_x=resolution;scene.render.resolution_y=resolution;scene.render.resolution_percentage=100
    scene.world.color=(.16,.16,.16);scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    centre=sum(points,Vector())/8;size=max(max(p[a] for p in points)-min(p[a] for p in points) for a in range(3))
    camdata=bpy.data.cameras.new('Asset camera');camera=bpy.data.objects.new('Asset camera',camdata);scene.collection.objects.link(camera)
    camera.location=centre+Vector(view).normalized()*size*2.2;camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler()
    camdata.type='ORTHO';camdata.ortho_scale=size*1.25;scene.camera=camera
    lamps=[]
    for direction,power,scale in [((-3,-4,6),1200,4),((4,1,4),900,3),((0,4,5),1300,3)]:
        lightdata=bpy.data.lights.new('Asset softbox','AREA');lightdata.energy=power*size*size/16;lightdata.shape='DISK';lightdata.size=size*scale/3
        light=bpy.data.objects.new('Asset softbox',lightdata);scene.collection.objects.link(light);light.location=centre+Vector(direction)*size/3
        light.rotation_euler=(centre-light.location).to_track_quat('-Z','Y').to_euler();lamps.append(light)
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    for item in [camera,*lamps]:bpy.data.objects.remove(item,do_unlink=True)

def save_asset(obj,name):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(name+'.blend')))
    bpy.ops.export_scene.gltf(filepath=str(HERE/(name+'.glb')),export_format='GLB',use_selection=True,export_yup=True)
