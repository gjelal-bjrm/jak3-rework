"""Rebuild both animated market awnings: tailored canvas, seams, fringe and anchors."""
import bpy, math, json, random, hashlib, sys, struct
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'active/jak3/data/decompiler_out/jak3/levels/wascityb'
TEXTURE=HERE/'awning-canvas-hd.png'
reports=[]
PANEL_JOINS=(.18,.36,.64,.82)


def glb(path):
    raw=path.read_bytes();size=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+size]),bytearray(raw[28+size:])


def values(document,binary,index):
    accessor=document['accessors'][index];view=document['bufferViews'][accessor['bufferView']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[accessor['type']]
    fmt='<'+{5121:'B',5123:'H',5125:'I',5126:'f'}[accessor['componentType']]*width
    offset=view.get('byteOffset',0)+accessor.get('byteOffset',0);stride=view.get('byteStride',struct.calcsize(fmt))
    return [struct.unpack_from(fmt,binary,offset+i*stride)for i in range(accessor['count'])]


def restore_native_skin_order(path,reference):
    document,binary=glb(path);source,_=glb(reference)
    original_names=[source['nodes'][n]['name']for n in source['skins'][0]['joints']]
    skin=document['skins'][0];old_nodes=skin['joints'][:]
    old_names=[document['nodes'][n]['name']for n in old_nodes]
    assert set(original_names)==set(old_names)
    old_to_new={i:original_names.index(name)for i,name in enumerate(old_names)}
    skin['joints']=[old_nodes[old_names.index(name)]for name in original_names]
    accessor=document['accessors'][skin['inverseBindMatrices']];view=document['bufferViews'][accessor['bufferView']]
    offset=view.get('byteOffset',0)+accessor.get('byteOffset',0);stride=view.get('byteStride',64)
    matrices=[bytes(binary[offset+i*stride:offset+i*stride+64])for i in range(len(old_names))]
    for i,name in enumerate(original_names):binary[offset+i*stride:offset+i*stride+64]=matrices[old_names.index(name)]
    done=set()
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            index=primitive['attributes']['JOINTS_0']
            if index in done:continue
            done.add(index);accessor=document['accessors'][index];view=document['bufferViews'][accessor['bufferView']]
            assert accessor['componentType']==5121 and accessor['type']=='VEC4'
            offset=view.get('byteOffset',0)+accessor.get('byteOffset',0);stride=view.get('byteStride',4)
            for i in range(accessor['count']):
                for j in range(4):binary[offset+i*stride+j]=old_to_new[binary[offset+i*stride+j]]
    encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    binary+=b'\0'*((-len(binary))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+
                     struct.pack('<II',len(encoded),0x4e4f534a)+encoded+
                     struct.pack('<II',len(binary),0x004e4942)+binary)
    return {'source_joint_order':original_names,'blender_joint_order':old_names,'joint_attributes_and_inverse_bind_rows_remapped':True}


def exported_color_report(path):
    document,binary=glb(path);result=[]
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            attrs=primitive['attributes']
            assert 'COLOR_0' in attrs and 'COLOR_1' not in attrs, 'Native importer requires the authored layer as COLOR_0'
            index=attrs['COLOR_0'];accessor=document['accessors'][index]
            scale={5121:255.,5123:65535.,5126:1.}[accessor['componentType']]
            rgba=[tuple(c/scale for c in row)for row in values(document,binary,index)]
            lo=[min(c[i]for c in rgba)for i in range(4)];hi=[max(c[i]for c in rgba)for i in range(4)]
            assert max(hi[:3])<.75 and min(lo[:3])>.20, 'Unexpected white or black vertex colour'
            assert lo[3]==hi[3]==1., 'Canvas opacity changed'
            if primitive['material']==0:assert hi[0]-lo[0]>.05, 'Canvas lost its crevice variation'
            result.append({'material':primitive['material'],'attribute':'COLOR_0','min_linear':lo,'max_linear':hi,
                           'component_type':accessor['componentType'],'normalized':accessor.get('normalized',False)})
    return result


def author(lod):
    control=f'wascity-awning-b-lod{lod}'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig_reference=SOURCE/'wascity-awning-b-lod0.glb'
    bpy.ops.import_scene.gltf(filepath=str(rig_reference))
    old=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.vertex_groups)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    old.data.calc_loop_triangles()
    old_triangles=[tuple(t.vertices) for t in old.data.loop_triangles]
    old_points=[v.co.copy() for v in old.data.vertices]
    used=sorted({i for t in old_triangles for i in t})
    # Use the LOD0 authored boundary reference for both silhouettes, not any unused accessor vertices.
    ref=json.loads((HERE/'awning-source-inspection.json').read_text())['meshes'][0]
    reference={int(i):Vector(v['co']) for i,v in ref['vertices'].items()}
    weights=[{old.vertex_groups[g.group].name:g.weight for g in v.groups}for v in old.data.vertices]
    if lod==1:
        # waswide-obs.gc defskelgroup shares the LOD0 joint group, but LOD1 only
        # uploads/uses native matrices 3..7. Preserve its own five-joint weights.
        native,binary=glb(SOURCE/(control+'.glb'));primitive=native['meshes'][0]['primitives'][0]
        attributes={name:values(native,binary,index)for name,index in primitive['attributes'].items()}
        old_points=[Vector((p[0],-p[2],p[1]))for p in attributes['POSITION']]
        joint_names=[b.name for b in rig.data.bones]
        indices=[row[0]for row in values(native,binary,primitive['indices'])]
        used=set(indices)
        # The shared accessor also holds unrelated controls and their different joints.
        weights=[({joint_names[j]:w for j,w in zip(js,ws)if w>1e-6}if i in used else{})
                 for i,(js,ws)in enumerate(zip(attributes['JOINTS_0'],attributes['WEIGHTS_0']))]
        old_triangles=[tuple(indices[i:i+3])for i in range(0,len(indices),3)]
    bvh=BVHTree.FromPolygons(old_points,old_triangles,all_triangles=True)
    old_color=old.data.color_attributes[0]
    color_mean=[sum(c.color[k]for c in old_color.data)/len(old_color.data)for k in range(4)]
    cloth=old.data.materials[0].copy();cloth.name='wascity-awning-b-canvas-hd'
    tex=bpy.data.images.load(str(TEXTURE),check_existing=True)
    for node in cloth.node_tree.nodes:
        if node.type=='TEX_IMAGE':node.image=tex
    bs=cloth.node_tree.nodes.get('Principled BSDF')
    if bs:bs.inputs['Roughness'].default_value=.92
    cloth.surface_render_method='DITHERED'
    # Small constant swatches are material definitions, not replacement photo textures.
    bronze=bpy.data.materials.new('wascity-awning-b-forged-bronze');bronze.use_nodes=True
    metal_image=bpy.data.images.new('awning-bronze-swatch',width=2,height=2,alpha=True)
    metal_image.pixels=[.25,.14,.055,1.]*4;metal_image.file_format='PNG';metal_image.pack()
    node=bronze.node_tree.nodes.new('ShaderNodeTexImage');node.image=metal_image
    bronze.node_tree.links.new(node.outputs['Color'],bronze.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    bronze.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.65
    bronze.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.42
    materials=[cloth,bronze]
    for material in materials:
        material_nodes=material.node_tree.nodes
        # Use a minimal preview graph; export below explicitly names COLOR_0,
        # since automatic material-node recognition can produce a white layer.
        material_nodes.clear()
        output=material_nodes.new('ShaderNodeOutputMaterial')
        principled=material_nodes.new('ShaderNodeBsdfPrincipled')
        principled.inputs['Roughness'].default_value=.92 if material==cloth else .42
        principled.inputs['Metallic'].default_value=0. if material==cloth else .65
        material.node_tree.links.new(principled.outputs[0],output.inputs['Surface'])
        texture_node=material_nodes.new('ShaderNodeTexImage');texture_node.image=tex if material==cloth else metal_image
        vertex_color=material_nodes.new('ShaderNodeVertexColor');vertex_color.layer_name='COLOR_0'
        multiply=material_nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1.
        material.node_tree.links.new(texture_node.outputs['Color'],multiply.inputs[1])
        material.node_tree.links.new(vertex_color.outputs['Color'],multiply.inputs[2])
        material.node_tree.links.new(multiply.outputs[0],principled.inputs['Base Color'])
    vertices=[];faces=[];uvs=[];colors=[];pins=[];matids=[];part_counts={}

    def vertex(co,uv=(.5,.5),shade=1.,pin=None):
        vertices.append(tuple(co));uvs.append(uv);pins.append(pin)
        # Match the original olive palette despite the generated canvas being slightly warmer.
        # Sunlit native shots were too yellow/bright. Retain the same bitmap and
        # muted olive family; temper luminance and the warm red bias in vertices.
        tint=(1.04,1.18,1.30)
        colors.append(tuple(min(.98,color_mean[i]*shade*.86*tint[i])for i in range(3))+(color_mean[3],))
        return len(vertices)-1

    def face(ids,material=0):faces.append(tuple(ids));matids.append(material)

    def curve_at(ids,t):
        points=[reference[i]for i in ids]
        # Chord-length Catmull-Rom boundaries soften the old polygonal outline.
        distances=[0.]
        for a,b in zip(points,points[1:]):distances.append(distances[-1]+(b-a).length)
        target=max(0.,min(1.,t))*distances[-1]
        segment=min(len(points)-2,next((i for i in range(len(points)-1)if target<=distances[i+1]),len(points)-2))
        q=(target-distances[segment])/max(distances[segment+1]-distances[segment],1e-8)
        a,b,c,d=points[max(0,segment-1)],points[segment],points[segment+1],points[min(len(points)-1,segment+2)]
        return .5*((2*b)+(-a+c)*q+(2*a-5*b+4*c-d)*q*q+(-a+3*b-3*c+d)*q*q*q)

    # A thin-plate height fit respects all original tension points, while the
    # new domain and wrinkle field provide genuinely new curved surface geometry.
    xy=np.array([[v.x,v.y]for v in reference.values()]);height=np.array([v.z for v in reference.values()])
    dist=np.linalg.norm(xy[:,None,:]-xy[None,:,:],axis=2)
    kernel=dist*dist*np.log(np.maximum(dist,1e-10))
    affine=np.column_stack([np.ones(len(xy)),xy])
    system=np.block([[kernel+np.eye(len(xy))*1e-7,affine],[affine.T,np.zeros((3,3))]])
    coef=np.linalg.solve(system,np.concatenate([height,np.zeros(3)]))
    def tension_fold(u,v):
        # Broad folds fan out from a tied corner. Their world-sized widths read
        # from the street; all contributions vanish on the pinned boundaries.
        result=0.
        for cu,cv in ((0,0),(1,0),(0,1),(1,1)):
            dx,dy=abs(u-cu)*9.,abs(v-cv)*3.6
            edge=min(dx/.24,1.)*min(dy/.20,1.)
            for angle,amplitude in ((.24,.13),(.62,-.115),(1.04,.10)):
                along=dx*math.cos(angle)+dy*math.sin(angle)
                across=-dx*math.sin(angle)+dy*math.cos(angle)
                if 0.<along<2.85:
                    taper=math.sin(math.pi*along/2.85)**1.25
                    result+=amplitude*edge*taper*math.exp(-(across/(.16+.052*along))**2)
        return result

    def cloth_shade(u,v,side):
        # Small crevice attenuation, tied to the actual folds/overlap edges.
        crease=min(max(-side*tension_fold(u,v)/.10,0.),1.)
        seam=max(math.exp(-((u-(s+.012))/.006)**2)for s in PANEL_JOINS)
        edge=math.exp(-(min(u,1-u)*9./.095)**2)+math.exp(-(min(v,1-v)*3.6/.095)**2)
        return max(.78,1.-.09*crease-.10*seam-.055*min(edge,1.))*(1. if side==1 else .92)

    def point(u,v,offset=0.):
        front=curve_at([14,29,15,16,28,17],u)
        back=curve_at([4,23,22,21,20,18],u)
        left=curve_at([14,13,6,5,4],v)
        right=curve_at([17,10,9,0,18],v)
        corners=(1-u)*(1-v)*reference[14]+u*(1-v)*reference[17]+(1-u)*v*reference[4]+u*v*reference[18]
        co=(1-v)*front+v*back+(1-u)*left+u*right-corners
        delta=np.linalg.norm(xy-np.array([co.x,co.y]),axis=1)
        z=float(np.dot(delta*delta*np.log(np.maximum(delta,1e-10)),coef[:len(xy)])+coef[-3]+coef[-2]*co.x+coef[-1]*co.y)
        envelope=math.sin(math.pi*u)*math.sin(math.pi*v)
        z+=envelope*(.055*math.sin(u*math.pi*8+1.1*math.sin(v*math.pi*2))+.028*math.sin(v*math.pi*5+u*2))
        z+=tension_fold(u,v)
        co.z=z+offset
        return co

    def tube(name,points,radius,sides=5,material=0,shade=1.,pin=None,closed=False):
        start=len(faces);rings=[]
        for i,co in enumerate(points):
            tangent=points[(i+1)%len(points)]-points[(i-1)%len(points)] if closed else points[min(i+1,len(points)-1)]-points[max(0,i-1)]
            tangent.normalize();normal=tangent.cross(Vector((0,0,1)))
            if normal.length<.01:normal=tangent.cross(Vector((0,1,0)))
            normal.normalize();other=tangent.cross(normal).normalized()
            rings.append([vertex(co+radius*(math.cos(2*math.pi*j/sides)*normal+math.sin(2*math.pi*j/sides)*other),
                                 (i*.07,j/sides),shade,pin)for j in range(sides)])
        for i in range(len(points) if closed else len(points)-1):
            a,b=rings[i],rings[(i+1)%len(points)]
            for j in range(sides):face((a[j],a[(j+1)%sides],b[(j+1)%sides],b[j]),material)
        if not closed:face(tuple(reversed(rings[0])),material);face(rings[-1],material)
        part_counts[name]=part_counts.get(name,0)+len(faces)-start

    nu,nv=(56,18)if lod==0 else(28,10)
    grids=[]
    for side in (1,-1):
        grid=[]
        for j in range(nv+1):
            row=[]
            for i in range(nu+1):
                u,v=i/nu,j/nv
                row.append(vertex(point(u,v,side*.012),(u*2.4,v),cloth_shade(u,v,side)))
            grid.append(row)
        for j in range(nv):
            for i in range(nu):
                ids=(grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i])
                face(ids if side==1 else tuple(reversed(ids)))
        grids.append(grid)
    border=[(i,0)for i in range(nu+1)]+[(nu,j)for j in range(1,nv+1)]+[(i,nv)for i in range(nu-1,-1,-1)]+[(0,j)for j in range(nv-1,0,-1)]
    for k,(i,j) in enumerate(border):
        ni,nj=border[(k+1)%len(border)];face((grids[0][j][i],grids[1][j][i],grids[1][nj][ni],grids[0][nj][ni]))
    part_counts['curved_double_sided_canvas']=len(faces)
    # A continuous rolled edge has actual circular thickness.
    boundary=[point(i/nu,j/nv,.003)for i,j in border]
    tube('rolled_perimeter_hem',boundary,.055,6 if lod==0 else 4,shade=.84,closed=True)
    # Overlapping canvas is visible from above AND from the playable street.
    # The step, tucked edge and double stitch replace the old thin seam cords.
    for u in PANEL_JOINS:
        for side in (1,-1):
            strip=[];start=len(faces)
            for j in range(nv+1):
                v=j/nv
                row=[]
                for du,rise,shade in ((-.010,.017,.93),(-.006,.043,.99),(.006,.047,1.02),(.010,.018,.81)):
                    row.append(vertex(point(u+du,v,side*rise),((u+du)*2.4,v),shade*(1. if side==1 else .92)))
                strip.append(row)
            for j in range(nv):
                for i in range(3):
                    ids=(strip[j][i],strip[j][i+1],strip[j+1][i+1],strip[j+1][i])
                    face(ids if side==1 else tuple(reversed(ids)))
            part_counts['stepped_panel_overlaps']=part_counts.get('stepped_panel_overlaps',0)+len(faces)-start
            for j in range(1,17 if lod==0 else 10):
                v=j/(17 if lod==0 else 10)
                tube('two_sided_cross_stitches',[point(u-.0048,v-.004,side*.054),point(u+.0048,v+.004,side*.054)],
                     .010 if lod==0 else .011,3,shade=1.09 if side==1 else 1.02)
    if lod==0:
        for v in (.022,.978):
            for side in (1,-1):
                for j in range(1,35):
                    u=j/35
                    tube('hem_lock_stitches',[point(u-.0025,v-.006,side*.030),point(u+.0025,v+.006,side*.030)],.009,3,shade=1.04)
    # Short irregular fringe follows the hem and keeps the original suspended silhouette.
    fringe_count=44 if lod==0 else 24
    rng=random.Random(731)
    for i in range(fringe_count):
        u=(i+.5)/fringe_count
        if u<.06 or u>.94:continue
        w=.35/fringe_count;length=.07+rng.random()*.12
        a,b=point(u-w,0,-.005),point(u+w,0,-.005)
        c,d=b+Vector((.015,-.025,-length)),a+Vector((.03,-.025,-length*.86))
        top=[vertex(p,(u*2.4,t),.96)for p,t in [(a,0),(b,0),(c,.1),(d,.1)]]
        bottom=[vertex(p-Vector((0,0,.010)),(u*2.4,t),.90)for p,t in [(a,0),(b,0),(c,.1),(d,.1)]]
        face(top);face(tuple(reversed(bottom)))
        for edge in range(4):
            after=(edge+1)%4;face((top[edge],bottom[edge],bottom[after],top[after]))
    part_counts['fringe_tabs']=sum(.06<=(i+.5)/fringe_count<=.94 for i in range(fringe_count))
    # Four leather-like canvas reinforcement tabs, bronze grommets and real knotted ties.
    for u,v in ((0,0),(1,0),(0,1),(1,1)):
        center=point(u,v,.025)
        du=.045 if u==0 else -.045;dv=.085 if v==0 else -.085
        patch=[point(u,v,.046),point(u+du,v,.046),point(u+du*.8,v+dv,.046),point(u,v+dv,.046)]
        face([vertex(p,(.35+q*.04,.35),.84,'main')for q,p in enumerate(patch)])
        # Corner positions are natively main-weighted and remain fixed under the bouncer.
        ring=[center+Vector((math.cos(t)*.080,math.sin(t)*.080,.015))for t in [2*math.pi*i/(16 if lod==0 else 10)for i in range(16 if lod==0 else 10)]]
        tube('forged_corner_rings',ring,.018,6 if lod==0 else 4,material=1,shade=.9,pin='main',closed=True)
        direction=Vector(((-1 if u==0 else 1)*.15,(-1 if v==0 else 1)*.07,.04))
        rope=[center+direction*t+Vector((0,0,-.035*math.sin(math.pi*t)))for t in [i/10 for i in range(11)]]
        tube('knotted_anchor_cord',rope,.022,5 if lod==0 else 4,shade=.74,pin='main')
        for h in range(3 if lod==0 else 2):
            knot=[center+direction*.47+Vector((math.cos(t)*.033,math.sin(t)*.033,h*.021-.023))for t in [2*math.pi*i/10 for i in range(10)]]
            tube('binding_turns',knot,.010,4,shade=.78,pin='main',closed=True)

    mesh=bpy.data.meshes.new(control+'-tailored-mesh');mesh.from_pydata(vertices,[],faces);mesh.materials.clear()
    assert not mesh.validate(), 'Authored mesh requires cleanup'
    for m in materials:mesh.materials.append(m)
    mesh.update();new=bpy.data.objects.new(control,mesh);bpy.context.collection.objects.link(new)
    layer=mesh.uv_layers.new(name='UVMap');col=mesh.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
    for p in mesh.polygons:
        p.material_index=matids[p.index];p.use_smooth=True
        for loop in p.loop_indices:
            vi=mesh.loops[loop].vertex_index;layer.data[loop].uv=uvs[vi];col.data[loop].color=colors[vi]
    for g in old.vertex_groups:new.vertex_groups.new(name=g.name)
    influence_count={}
    for i,co in enumerate(vertices):
        if pins[i]:blend={pins[i]:1.}
        else:
            hit,normal,index,distance=bvh.find_nearest(Vector(co));tri=old_triangles[index]
            bary=barycentric_transform(hit,*[old_points[k]for k in tri],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
            blend={}
            for k,w in zip(tri,bary):
                for name,value in weights[k].items():blend[name]=blend.get(name,0)+max(0.,w)*value
            blend=dict(sorted(blend.items(),key=lambda p:p[1],reverse=True)[:3]);total=sum(blend.values());blend={k:v/total for k,v in blend.items()if v>1e-6}
            total=sum(blend.values());blend={k:v/total for k,v in blend.items()}
        for name,w in blend.items():new.vertex_groups[name].add([i],w,'REPLACE');influence_count[name]=influence_count.get(name,0)+1
    new.parent=old.parent;modifier=new.modifiers.new('Native eleven-joint canvas bouncer','ARMATURE');modifier.object=rig
    new['enable_custom_weights']=1
    bpy.data.objects.remove(old,do_unlink=True);new.name=control
    mesh.calc_loop_triangles()
    lo=[min(v[i]for v in vertices)for i in range(3)];hi=[max(v[i]for v in vertices)for i in range(3)]
    report={'control':control,'revision':'readable-two-sided-tailoring-v2','source_triangles':len(old_triangles),'authored_triangles':len(mesh.loop_triangles),
        'authored_vertices':len(vertices),'indexed_bounds_blender_z_up':[lo,hi],'joint_names':[b.name for b in rig.data.bones],
        'weighted_vertex_counts':influence_count,'weights':'Closest original triangle barycentric interpolation, three normalized influences; fixed anchor rings/cords use native main',
        'parts':part_counts,'texture':str(TEXTURE),'texture_size':list(tex.size),'native_visual_validation':False,
        'form_changes':{'main_grid_unchanged':[nu,nv],'corner_fan_fold_amplitudes_m':[.13,-.115,.10],
            'fan_fold_length_m':2.85,'rolled_hem_radius_m':.055,'overlap_width_parametric':.020,
            'overlap_relief_from_sheet_m':.035,'both_faces_tailored':True,
            'crevice_tint_reduction_max':.22,'canvas_luminance_factor':.86,'olive_vertex_rgb':[1.04,1.18,1.30]}}
    bpy.ops.object.select_all(action='DESELECT');new.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=new
    bpy.ops.export_scene.gltf(filepath=str(HERE/(control+'.glb')),export_format='GLB',use_selection=True,
                             export_animations=False,export_apply=False,export_extras=True,export_all_influences=False,
                             export_vertex_color='NAME',export_vertex_color_name='COLOR_0',export_all_vertex_colors=False)
    report['skin_order']=restore_native_skin_order(HERE/(control+'.glb'),rig_reference)
    report['exported_colors']=exported_color_report(HERE/(control+'.glb'))
    if lod==1:
        assert set(influence_count)=={'main','centerc','centerd','leftb','rightb'}
        report['shared_rig_evidence']='waswide-obs.gc:723 defskelgroup skel-wascity-awning-b; LOD0 joint group, LOD1 native matrices 3..7'
    c=Vector([(lo[i]+hi[i])/2 for i in range(3)]);size=max(hi[i]-lo[i]for i in range(3))
    bpy.ops.object.camera_add(location=c+Vector((1.15,-1.60,1.20))*size)
    camera=bpy.context.object;camera.rotation_euler=(c-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=size*1.38
    scene=bpy.context.scene;scene.camera=camera
    for xyz,power in [((1,-1,2),90),((-1,-.5,1),40),((0,2,2),70)]:
        bpy.ops.object.light_add(type='AREA',location=c+Vector(xyz)*size)
        light=bpy.context.object;light.data.energy=power*size*size;light.data.size=size*2;light.rotation_euler=(c-light.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Neutral');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.16,1)
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1200;scene.render.resolution_y=850;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(HERE/(control+'-preview.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(control+'.blend')))
    bpy.ops.render.render(write_still=True)
    camera.location=c+Vector((.65,-1.60,-.85))*size
    camera.rotation_euler=(c-camera.location).to_track_quat('-Z','Y').to_euler()
    # Studio inspection needs a lower fill; it is not exported or saved as a
    # scene/game light, and does not alter the authored vertex colours.
    bpy.ops.object.light_add(type='AREA',location=c+Vector((-.6,-1.3,-1.5))*size)
    underside_fill=bpy.context.object;underside_fill.data.energy=70*size*size;underside_fill.data.size=size*1.6
    underside_fill.rotation_euler=(c-underside_fill.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(HERE/(control+'-underside-preview.png'))
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(underside_fill,do_unlink=True)
    camera.location=c+Vector((1.15,-1.60,1.20))*size
    camera.rotation_euler=(c-camera.location).to_track_quat('-Z','Y').to_euler()
    if lod==0:
        # A bounded authoring test checks attachment continuity; this is not native animation approval.
        for name,amount in [('centerc',.18),('centerd',-.10),('centerb',.12),('centera',.08)]:
            rig.pose.bones[name].location.z=amount
        bpy.context.view_layer.update()
        evaluated=new.evaluated_get(bpy.context.evaluated_depsgraph_get());deformed=evaluated.to_mesh()
        displacements=[(deformed.vertices[i].co-Vector(vertices[i])).length for i in range(len(vertices))]
        report['synthetic_bouncer_test']={'max_displacement_m':max(displacements),
            'fixed_anchor_max_displacement_m':max(displacements[i]for i,p in enumerate(pins)if p=='main'),
            'native_animation_validation':False}
        evaluated.to_mesh_clear()
        assert report['synthetic_bouncer_test']['fixed_anchor_max_displacement_m']<1e-5
        scene.render.filepath=str(HERE/(control+'-bouncer-preview.png'));bpy.ops.render.render(write_still=True)
        for bone in rig.pose.bones:bone.location=(0,0,0)
        bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(control+'.blend')))
    reports.append(report);print(json.dumps(report),flush=True)
    (HERE/(control+'-author-report.json')).write_text(json.dumps(report,indent=2))


for lod in ((0,)if '--lod0-only' in sys.argv else(0,1)):author(lod)
(HERE/'awning-author-report.json').write_text(json.dumps(reports,indent=2))
