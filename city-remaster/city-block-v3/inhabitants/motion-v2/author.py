"""Two native Spargus inhabitants: planted, alternating eight-second dialogue.

Run in Blender 5.2, in background. All outputs stay in motion-v2. The previous
actors and the game are never modified. Native mesh topology/materials are kept.
"""
from pathlib import Path
import bpy,math,json,struct,hashlib,importlib.util,shutil
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent
BEFORE=HERE/'before'
spec=importlib.util.spec_from_file_location('native_actor_author',SOURCE/'author.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
native.HERE=HERE
FRAMES=32
DURATION=8.0

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def smooth(a,b,t):
    x=max(0,min(1,(t-a)/(b-a)))
    return x*x*(3-2*x)
def pulse(a,b,c,d,t):return smooth(a,b,t)*(1-smooth(c,d,t))
def reset(arm):
    arm.animation_data_clear()
    for b in arm.pose.bones:b.matrix_basis.identity()
    native.update()

def leg(arm,side,target):
    """Analytic two-bone support with fixed foot matrix; no mesh stretching."""
    thigh=arm.pose.bones[side+'thigh'];knee=arm.pose.bones[side+'knee']
    ankle=arm.pose.bones[side+'ankle']
    hip=thigh.head.copy();dest=target.translation.copy()
    l1=(knee.head-hip).length;l2=(ankle.head-knee.head).length
    axis=dest-hip;distance=axis.length;axis.normalize()
    assert distance<l1+l2,('unreachable foot',side,distance,l1+l2)
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    pole=Vector((0,-1,0));pole-=axis*pole.dot(axis);pole.normalize()
    bend=hip+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    native.aim(arm,side+'thigh',bend-hip)
    native.aim(arm,side+'knee',dest-arm.pose.bones[side+'knee'].head)
    # Preserve both contact location and the sole's original horizontal plane.
    arm.pose.bones[side+'ankle'].matrix=target.copy();native.update()

def conversation(arm,sex,t,scale,feet):
    reset(arm)
    p=math.tau*t/DURATION
    male=sex=='male'
    speak=pulse(.25,.85,2.85,3.65,t) if male else pulse(4.15,4.85,6.9,7.7,t)
    accent=(pulse(1.0,1.3,1.5,1.9,t)*.16+pulse(2.1,2.3,2.5,2.8,t)*.11) if male else (pulse(5.0,5.25,5.45,5.85,t)*.13+pulse(6.15,6.35,6.5,6.85,t)*.14)
    secondary=pulse(1.5,1.9,2.25,2.8,t)*.42 if male else pulse(4.65,5.05,5.7,6.5,t)*.50
    shift=(.017 if male else .022)*math.sin(p+(.25 if male else 2.35))
    root=arm.pose.bones['main'];m=root.matrix.copy()
    m.translation+=Vector((shift/scale,(-.008*speak+.003*math.sin(2*p))/scale,(-.014+.002*math.cos(2*p))/scale))
    root.matrix=m;native.update()
    native.turn(arm,'hips','Y',math.radians(.7*math.sin(p)))
    native.turn(arm,'hips','Z',math.radians(.6*math.sin(p+.4)))
    for side in ('L','R'):leg(arm,side,feet[side])
    chest_yaw=math.radians((1.5 if male else -1.5)*speak+.6*math.sin(p))
    native.turn(arm,'chest','Z',chest_yaw)
    native.turn(arm,'chest','Y',math.radians(-.8*math.sin(p+(.25 if male else 2.35))))
    native.turn(arm,'chest','X',math.radians(.6*math.sin(2*p)+1.0*speak))
    # Upper arms remain near the body. Forearms rise for a phrase, then return
    # fully to a soft resting bend; hands are never held out as a permanent pose.
    for side,sign in (('L',1),('R',-1)):
        gesture=speak if side=='R' else secondary
        native.aim(arm,side+'shoulder',(sign*(.16+.13*gesture),-.06-.12*gesture,-1))
        outward=sign*(.06+.18*gesture)
        forward=-.19-1.00*gesture-(accent if side=='R' else 0)
        down=-1+.84*gesture+(accent*.25 if side=='R' else 0)
        native.aim(arm,side+'elbow',(outward,forward,down))
        native.turn(arm,side+'hand','Z',math.radians(sign*(3*gesture+7*accent)))
        native.turn(arm,side+'hand','X',math.radians(-3*gesture+3*math.sin(2*p)*gesture))
    # Native head is attached to neck (female has no separate head bone).
    # Small eye-line correction for height difference and response nods.
    nod=(pulse(4.8,5.05,5.15,5.45,t)+.7*pulse(6.35,6.55,6.65,6.9,t)) if male else (pulse(1.1,1.3,1.4,1.7,t)+.65*pulse(2.35,2.55,2.65,2.95,t))
    native.turn(arm,'neck','Z',-chest_yaw+math.radians(1.3*math.sin(p+.7)))
    native.turn(arm,'neck','X',math.radians((3 if male else -3)+3.5*nod+.65*math.sin(2*p)))
    native.turn(arm,'neck','Y',math.radians((.8 if male else -1.2)*math.sin(p+.4)))
    native.update()
    return {'speaking_envelope':speak,'weight_shift_m':shift,'listening_nod':nod}

def author(sex):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE/(sex+'-selected.glb')))
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    obj=next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('wlander-'))
    for o in list(bpy.data.objects):
        if o not in (arm,obj):bpy.data.objects.remove(o,do_unlink=True)
    reset(arm)
    ev,mesh=native.evaluated(obj)
    height=max(v.co.z for v in mesh.vertices)-min(v.co.z for v in mesh.vertices)
    ev.to_mesh_clear();scale=(2 if sex=='male' else 1.9)/height
    feet={}
    for side,sign in (('L',1),('R',-1)):
        m=arm.pose.bones[side+'ankle'].matrix.copy()
        m.translation+=Vector((sign*(.015 if sex=='male' else .025)/scale,sign*-.025/scale,0))
        feet[side]=m
    mats=native.textures(obj)
    for face in obj.data.polygons:face.use_smooth=True
    name='conversing-'+sex;frames=[];rig=[];joints=[];bounds=[];envelopes=[];draws=None;zoffset=None
    for i in range(FRAMES+1):
        envelopes.append(conversation(arm,sex,i*DURATION/FRAMES,scale,feet))
        rig.append({b.name:b.matrix_basis.copy() for b in arm.pose.bones})
        if zoffset is None:
            ev,mesh=native.evaluated(obj);zoffset=-min(v.co.z for v in mesh.vertices);ev.to_mesh_clear()
        records,ranges=native.frame_vertices(obj,scale,zoffset)
        if draws is None:draws=ranges
        assert ranges==draws
        if frames:assert all(a[6:]==b[6:] for a,b in zip(frames[0],records))
        if i==FRAMES:
            seam=max((Vector(a[:3])-Vector(b[:3])).length for a,b in zip(frames[0],records))
            assert seam<.00001,seam
            break
        frames.append(records)
        bounds.append([[min(v[a] for v in records) for a in range(3)],[max(v[a] for v in records) for a in range(3)]])
        names=('hips','Lknee','Rknee','Lhand','Rhand','Lankle','Rankle','Lball','Rball','neck')
        joints.append({n:[arm.pose.bones[n].head.x*scale,(arm.pose.bones[n].head.z+zoffset)*scale,-arm.pose.bones[n].head.y*scale] for n in names})
    raw=b''.join(struct.pack('<12f',*v) for f in frames for v in f)
    (HERE/(name+'.bin')).write_bytes(raw)
    for d in draws:d.update(mats[d.pop('material_index')])
    old=json.loads((BEFORE/(name+'.json')).read_text())
    report={**old,'version':2,'binary_sha256':hashlib.sha256(raw).hexdigest(),'frame_count':FRAMES,'duration_seconds':DURATION,
      'sample_times':[i/FRAMES for i in range(FRAMES)],'bounds_by_frame':bounds,'joint_positions_by_frame':joints,
      'source_manifest':'provenance.json','dialogue_timeline':envelopes[:FRAMES],
      'phase_contract':'Both residents use identical phase in seconds. Male speaks first half; female second half. Do not add an opposite phase offset.',
      'loop_seam_max_error_m':seam,'draws':draws,'native_game_validation':False,
      'feet':'Both native sole frames stay fixed via analytic two-bone leg support; skin topology and limb lengths unchanged.'}
    assert report['vertex_count']==len(frames[0])
    (HERE/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    # Editable rig records precisely the exported authored samples.
    arm.animation_data_clear()
    for i,matrices in enumerate(rig):
        for bone in arm.pose.bones:
            bone.rotation_mode='QUATERNION';bone.matrix_basis=matrices[bone.name]
            bone.keyframe_insert(data_path='location',frame=1+i*6)
            bone.keyframe_insert(data_path='rotation_quaternion',frame=1+i*6)
            bone.keyframe_insert(data_path='scale',frame=1+i*6)
    scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=193;scene.render.fps=24;scene.frame_set(1)
    scene['actor_export_metres_scale']=scale;scene['actor_export_source_zoffset']=zoffset
    scene['preview_notice']='Editable native rig. Runtime output uses Y-up metres. Rendered comparison is in pair-preview.blend.'
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(name+'.blend')))
    print('AUTHORED',name,len(frames[0]),FRAMES,'seam',seam,flush=True)
    return report

def main():
    # Capture once before first publication. Subsequent re-authoring must read
    # this immutable baseline, never the currently installed descendant.
    BEFORE.mkdir(exist_ok=True)
    for sex in ('male','female'):
        for ext in ('.bin','.json'):
            filename='conversing-'+sex+ext
            if not (BEFORE/filename).exists():shutil.copy2(SOURCE/filename,BEFORE/filename)
    reports=[author(sex) for sex in ('male','female')]
    provenance={'version':2,'scope':'Only conversing-male and conversing-female; staged, not installed.',
      'author':'author.py','author_sha256':sha(Path(__file__)),'native_topology_preserved':True,
      'predecessor_files':{},'candidate_files':{},'sources':{},
      'native_game_validation':False,
      'room_transform_recommendation':{'male':{'position':[.25,.058,-2.15],'yaw_radians':math.atan2(1.2,-.9)},
        'female':{'position':[1.45,.058,-3.05],'yaw_radians':math.atan2(-1.2,.9)},
        'phase_seconds':'same for both','duration_seconds':DURATION}}
    for report in reports:
        name=report['name']
        for ext in ('.json','.bin'):
            filename=name+ext
            provenance['predecessor_files'][filename]=sha(BEFORE/filename)
            provenance['candidate_files'][filename]=sha(HERE/filename)
        provenance['sources'][report['source_sex']+'-selected.glb']=sha(SOURCE/(report['source_sex']+'-selected.glb'))
        for draw in report['draws']:
            provenance['candidate_files'][draw['texture']]=sha(HERE/draw['texture'])
    (HERE/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('DONE motion-v2 staged only',flush=True)

if __name__=='__main__':main()
