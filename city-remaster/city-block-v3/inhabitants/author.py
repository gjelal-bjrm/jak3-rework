"""Blender-authored native Spargus residents; never alters the installed game."""
from pathlib import Path
import bpy,math,json,struct,hashlib
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent

def digest(raw):return hashlib.sha256(raw).hexdigest()
def update():bpy.context.view_layer.update()
def aim(arm,name,direction):
    b=arm.pose.bones[name];update()
    rotation=(b.tail-b.head).rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4()
    b.matrix=Matrix.Translation(b.head)@rotation@Matrix.Translation(-b.head)@b.matrix;update()
def turn(arm,name,axis,angle):
    b=arm.pose.bones.get(name)
    if b:
        b.matrix=Matrix.Translation(b.head)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-b.head)@b.matrix;update()

def pose(arm,sex,kind,phase):
    arm.animation_data_clear()
    for b in arm.pose.bones:b.matrix_basis.identity()
    update()
    wave=math.sin(phase);slow=math.cos(phase)
    if kind=='sitting':
        # Seat contact is subsequently measured and exported in actor metres.
        main=arm.pose.bones['main'];matrix=main.matrix.copy();matrix.translation.z-=.79;main.matrix=matrix;update()
        for side,sign in [('L',1),('R',-1)]:
            ankle=arm.pose.bones[side+'ankle'].matrix.copy()
            aim(arm,side+'thigh',(sign*.11,-1,-.08))
            aim(arm,side+'knee',(0,-.55,-1))
            current=arm.pose.bones[side+'ankle'];ankle.translation=current.head;current.matrix=ankle;update()
        turn(arm,'chest','X',math.radians(5+.6*wave))
        for side,sign in [('L',1),('R',-1)]:
            aim(arm,side+'shoulder',(sign*.17,-.18,-1))
            aim(arm,side+'elbow',(-sign*.15,-1,-.40+.012*wave))
            turn(arm,side+'hand','X',math.radians(-9))
        turn(arm,'neck','Z',math.radians(-7+2.0*wave))
        turn(arm,'neck','X',math.radians(2+1.0*slow))
    else:
        # Both residents listen and gesture with one forearm; no waving loops.
        if sex=='male':
            aim(arm,'Lshoulder',(.21,.02,-1));aim(arm,'Lelbow',(-.18,-.36,-1))
            aim(arm,'Rshoulder',(-.22,-.05,-1));aim(arm,'Relbow',(.08,-1,.12+.07*wave))
        else:
            aim(arm,'Lshoulder',(.12,.03,-1));aim(arm,'Lelbow',(-.03,-.14,-1))
            aim(arm,'Rshoulder',(-.28,-.12,-1));aim(arm,'Relbow',(-.18,-1,.18+.08*wave))
        turn(arm,'chest','Z',math.radians(1.4*wave))
        turn(arm,'chest','X',math.radians(.5*slow))
        turn(arm,'neck','Z',math.radians(7+2.8*wave))
        turn(arm,'neck','X',math.radians(1.6*slow))
        turn(arm,'Rhand','Y',math.radians(4*wave))
    update()

def scene_setup():
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=32
    sc.world=bpy.data.worlds.new('Warm interior preview');sc.world.use_nodes=True
    sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.09,.11,.13,1)
    sc.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    for pos,power,size in [((3,-4,6),650,5),((-4,1,4),380,4)]:
        d=bpy.data.lights.new('softbox','AREA');d.energy=power;d.shape='DISK';d.size=size
        o=bpy.data.objects.new('softbox',d);sc.collection.objects.link(o);o.location=pos
        o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()
    camd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camd);sc.collection.objects.link(cam)
    cam.location=(4,-7,3.2);cam.rotation_euler=(Vector((0,-.15,1.3))-cam.location).to_track_quat('-Z','Y').to_euler()
    camd.type='ORTHO';camd.ortho_scale=3.8;sc.camera=cam
    sc.render.resolution_x=900;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
    sc.view_settings.view_transform='AgX'
    return sc

def textures(obj):
    (HERE/'textures').mkdir(exist_ok=True);result={}
    for i,mat in enumerate(obj.data.materials):
        images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
        assert images,mat.name
        image=images[0];name=''.join(c if c.isalnum()or c in '-_'else'_'for c in image.name)
        file=HERE/'textures'/(name+'.png')
        if image.packed_file and bytes(image.packed_file.data).startswith(b'\x89PNG'):
            raw=bytes(image.packed_file.data);file.write_bytes(raw)
        else:
            image.filepath_raw=str(file);image.file_format='PNG';image.save();raw=file.read_bytes()
        result[i]={'material':mat.name,'texture':'textures/'+file.name,'texture_sha256':digest(raw),
                   'size':list(image.size),'texture_filter':'linear_mipmap_linear','alpha_mode':'opaque'}
    return result

def evaluated(obj):
    deps=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(deps);mesh=ev.to_mesh();mesh.calc_loop_triangles()
    return ev,mesh

def frame_vertices(obj,scale,zoffset):
    ev,mesh=evaluated(obj);records=[];ranges=[]
    colors=mesh.color_attributes.get('Color') or mesh.color_attributes.active_color
    uv=mesh.uv_layers.active.data
    for material in range(len(obj.data.materials)):
        start=len(records)
        for triangle in mesh.loop_triangles:
            if triangle.material_index!=material:continue
            for vi,li in zip(triangle.vertices,triangle.loops):
                point=ev.matrix_world@mesh.vertices[vi].co
                normal=(ev.matrix_world.to_3x3()@mesh.corner_normals[li].vector).normalized()
                tex=uv[li].uv
                col=tuple(2*x for x in colors.data[li if colors.domain=='CORNER'else vi].color)if colors else(1,1,1,2)
                # Blender Z-up, forward -Y -> runtime Y-up, forward +Z.
                records.append((point.x*scale,(point.z+zoffset)*scale,-point.y*scale,
                                normal.x,normal.z,-normal.y,tex.x,1-tex.y,*col))
        if len(records)>start:ranges.append({'material_index':material,'first':start,'count':len(records)-start})
    ev.to_mesh_clear();return records,ranges

def main():
    results=[]
    for sex,kind in [('male','sitting'),('male','conversing'),('female','conversing')]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(HERE/(sex+'-selected.glb')))
        arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
        obj=next(o for o in bpy.data.objects if o.type=='MESH'and o.name.startswith('wlander-'))
        for o in list(bpy.data.objects):
            if o not in (arm,obj):bpy.data.objects.remove(o,do_unlink=True)
        arm.animation_data_clear()
        for b in arm.pose.bones:b.matrix_basis.identity()
        update()
        # Original source models are already in metres, approximately 3 m high.
        ev,mesh=evaluated(obj);standing_height=max(v.co.z for v in mesh.vertices)-min(v.co.z for v in mesh.vertices);ev.to_mesh_clear()
        scale=(2.0 if sex=='male'else 1.9)/standing_height
        for p in obj.data.polygons:p.use_smooth=True
        mats=textures(obj)
        name=kind+'-'+sex;all_frames=[];bounds=[];pose_joint_reports=[];rig_frames=[];zoffset=None;draws=None
        for i in range(4):
            pose(arm,sex,kind,i*math.tau/4)
            rig_frames.append({b.name:b.matrix_basis.copy()for b in arm.pose.bones})
            if zoffset is None:
                ev,mesh=evaluated(obj);zoffset=-min(v.co.z for v in mesh.vertices);ev.to_mesh_clear()
            records,ranges=frame_vertices(obj,scale,zoffset)
            if draws is None:draws=ranges
            assert draws==ranges
            if all_frames:assert all(a[6:]==b[6:]for a,b in zip(all_frames[0],records))
            all_frames.append(records)
            bounds.append([[min(v[a]for v in records)for a in range(3)],[max(v[a]for v in records)for a in range(3)]])
            pose_joint_reports.append({n:[b.head.x*scale,(b.head.z+zoffset)*scale,-b.head.y*scale]
                for n in ('hips','Lknee','Rknee','Lhand','Rhand','Lankle','Rankle','neck')if(b:=arm.pose.bones.get(n))})
        data=b''.join(struct.pack('<12f',*r)for frame in all_frames for r in frame)
        (HERE/(name+'.bin')).write_bytes(data)
        for draw in draws:draw.update(mats[draw.pop('material_index')])
        report={'name':name,'version':1,'binary':name+'.bin','binary_sha256':digest(data),
          'source_manifest':'source-manifest.json','source_sex':sex,'kind':kind,
          'coordinate_system':'right-handed X right, Y up, Z forward; metres; lowest sole at Y=0',
          'stride_bytes':48,'attributes':{'position':[0,3],'normal':[12,3],'uv':[24,2],'color':[32,4]},
          'vertex_color_contract':'linear vertex COLOR_0 multiplied by native GLB baseColorFactor=2; RGB normally 0..1, alpha=2 compensates native texture alpha 128/255; multiply albedo * vertex RGBA directly, then lighting',
          'primitive':'triangles','vertex_count':len(all_frames[0]),'frame_count':4,
          'frame_stride_bytes':len(all_frames[0])*48,'duration_seconds':5.6 if kind=='sitting'else 4.8,
          'sample_times':[0,.25,.5,.75],'loop':True,'interpolation':'cyclic linear positions; normalize blended normals; UV/color constant',
          'standing_height_m':2.0 if sex=='male'else 1.9,'source_height_m':standing_height,'source_to_metres_scale':scale,
          'bounds_by_frame':bounds,'draws':draws,'joint_positions_by_frame':pose_joint_reports,
          'native_game_validation':False}
        if kind=='sitting':
            h=pose_joint_reports[0]['hips'];report['seat']={'center_m':[h[0],h[1]-.06,h[2]],'recommended_cushion_top_m':h[1]-.06,
              'recommended_cushion_depth_m':.58,'recommended_cushion_width_m':.85,'forward':'+Z'}
        (HERE/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
        # Store editable rig with actual authored keyposes, not flattened props.
        arm.animation_data_clear()
        for i in range(5):
            for b in arm.pose.bones:
                b.matrix_basis=rig_frames[i%4][b.name]
                b.keyframe_insert(data_path='location',frame=1+i*24)
                b.keyframe_insert(data_path='rotation_quaternion',frame=1+i*24)
                b.keyframe_insert(data_path='scale',frame=1+i*24)
        sc=scene_setup();sc.frame_end=97;sc.frame_set(1)
        sc.render.filepath=str(HERE/(name+'-preview.png'));bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(name+'.blend')))
        results.append({k:report[k]for k in ('name','binary','vertex_count','frame_count','binary_sha256','bounds_by_frame')})
    (HERE/'actors.json').write_text(json.dumps({'actors':results,'format':'actor metadata JSON + float32 little-endian 48-byte vertices, four frames'},indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
