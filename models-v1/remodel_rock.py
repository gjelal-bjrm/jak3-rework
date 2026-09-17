"""Run in Blender. Remodel a native rock and export an explicit FR3 patch."""
from pathlib import Path
import bpy,bmesh,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import closest_point_on_tri

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
data=json.loads((HERE/'native-rocks.json').read_text())
component=json.loads((HERE/'rock-components.json').read_text())[0]
source=[data['faces'][i] for i in component['face_indices']]
origin=Vector(component['centre'])
def to_blender(p):
    q=Vector(p)-origin;return Vector((q.x,-q.z,q.y))
def to_game(p):return list(origin+Vector((p.x,p.z,-p.y)))
def signature(face):
    return (face['material'],tuple(sorted(tuple(round(x*1000) for x in v['p']) for v in face['vertices'])))

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
materials=sorted({f['material'] for f in source})
vertices=[];triangles=[];lookup={}
for face in source:
    tri=[]
    for v in face['vertices']:
        k=tuple(round(x*1000) for x in v['p'])
        if k not in lookup:lookup[k]=len(vertices);vertices.append(to_blender(v['p']))
        tri.append(lookup[k])
    triangles.append(tri)
mesh=bpy.data.meshes.new('Native rock source');mesh.from_pydata(vertices,[],triangles);mesh.update()
original=bpy.data.objects.new('Original_40_triangles',mesh);bpy.context.collection.objects.link(original)
for name in materials:
    material=bpy.data.materials.new(name);material.use_nodes=True
    tex=material.node_tree.nodes.new('ShaderNodeTexImage')
    page=next(f['page'] for f in source if f['material']==name)
    texture_path=ROOT/'data/custom_assets/jak3/texture_replacements'/page/(name+'.png')
    if not texture_path.exists():texture_path=ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/textures'/page/(name+'.png')
    tex.image=bpy.data.images.load(str(texture_path));tex.image.pack()
    shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.82
    material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
    mesh.materials.append(material)
uv=mesh.uv_layers.new(name='UVMap')
for polygon,face in zip(mesh.polygons,source):
    polygon.material_index=materials.index(face['material'])
    for loop,v in zip(polygon.loop_indices,face['vertices']):uv.data[loop].uv=(v['uv'][0],1-v['uv'][1])
original.hide_render=True;original.hide_set(True)
reworked=bpy.data.objects.new('Palace_rock_remodel',mesh.copy());bpy.context.collection.objects.link(reworked)
bpy.context.view_layer.objects.active=reworked;reworked.select_set(True)
bm=bmesh.new();bm.from_mesh(reworked.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(2),use_dissolve_boundaries=False,
    verts=list(bm.verts),edges=list(bm.edges),delimit={'MATERIAL','UV'})
edges=[edge for edge in bm.edges if len(edge.link_faces)==2 and edge.calc_face_angle(0)>math.radians(17)]
bmesh.ops.bevel(bm,geom=edges,offset=.10,segments=4,profile=.65,affect='EDGES',clamp_overlap=True)
bmesh.ops.triangulate(bm,faces=list(bm.faces))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(reworked.data);bm.free()
for polygon in reworked.data.polygons:polygon.use_smooth=True
reworked.data.update()

bvh=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
lod_faces={}
for face in data['faces']:
    if face['tree_type']=='tie' and face['geom']<3:lod_faces[(face['geom'],signature(face))]=face
patch={'description':'Blender rounded rock, original silhouette envelope and UV materials',
       'origin':list(origin),'remove':[],'add':[]}
for face in source:
    for geom in range(3):
        other=lod_faces[(geom,signature(face))]
        patch['remove'].append({**{k:other[k] for k in ('tree_type','geom','tree','draw','group','stream_index')},
            'original_positions':[v['p'] for v in other['vertices']]})
max_distance=0
def weights(p,triangle):
    a,b,c=[vertices[i] for i in triangle]
    p=closest_point_on_tri(p,a,b,c);u=b-a;v=c-a;w=p-a
    aa=u.dot(u);ab=u.dot(v);bb=v.dot(v);wa=w.dot(u);wb=w.dot(v)
    denominator=aa*bb-ab*ab
    bweight=(bb*wa-ab*wb)/denominator;cweight=(aa*wb-ab*wa)/denominator
    return [1-bweight-cweight,bweight,cweight]
for polygon in reworked.data.polygons:
    point=sum((reworked.data.vertices[i].co for i in polygon.vertices),Vector())/3
    candidate_ids=[i for i,f in enumerate(source) if f['material']==materials[polygon.material_index]]
    material_bvh=BVHTree.FromPolygons(vertices,[triangles[i] for i in candidate_ids],all_triangles=True)
    _,_,local_index,_=material_bvh.find_nearest(point);source_index=candidate_ids[local_index]
    face=source[source_index]
    for geom in range(3):
        other=lod_faces[(geom,signature(face))]
        record={k:other[k] for k in ('tree_type','geom','tree','draw','group')};record['vertices']=[]
        source_colors={tuple(round(x*1000) for x in v['p']):v['color'] for v in other['vertices']}
        indices=[source_colors[tuple(round(x*1000) for x in v['p'])] for v in face['vertices']]
        for vi,loop in zip(polygon.vertices,polygon.loop_indices):
            vertex=reworked.data.vertices[vi]
            _,_,colour_local,_=material_bvh.find_nearest(vertex.co);colour_source=candidate_ids[colour_local]
            colour_face=source[colour_source];colour_other=lod_faces[(geom,signature(colour_face))]
            color_lookup={tuple(round(x*1000) for x in v['p']):v['color'] for v in colour_other['vertices']}
            indices=[color_lookup[tuple(round(x*1000) for x in v['p'])] for v in colour_face['vertices']]
            weight=weights(vertex.co,triangles[colour_source])
            st=reworked.data.uv_layers.active.data[loop].uv
            texcoord=[st.x,1-st.y]
            normal=vertex.normal.normalized()
            record['vertices'].append({'p':to_game(vertex.co),'uv':texcoord,
                'normal':[normal.x,normal.z,-normal.y],'color_indices':indices,'color_weights':weight})
            max_distance=max(max_distance,bvh.find_nearest(vertex.co)[3])
        patch['add'].append(record)
assert max_distance<.16,max_distance
(HERE/'rock-test-patch.json').write_text(json.dumps(patch))
report={'original_triangles':len(source),'new_triangles':len(reworked.data.polygons),
        'max_surface_distance_m':max_distance,'native_LODs':[0,1,2],'origin':list(origin),
        'collisions':'original collision surface retained; native contact test pending'}
(HERE/'rock-test-report.json').write_text(json.dumps(report,indent=2))
reworked['native_origin']=list(origin);reworked['max_surface_distance_m']=max_distance
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'palace-rock-test.blend'))
bpy.ops.export_scene.gltf(filepath=str(HERE/'palace-rock-test.glb'),export_format='GLB',use_selection=True,
    export_materials='EXPORT',export_yup=True)
print(json.dumps(report))
