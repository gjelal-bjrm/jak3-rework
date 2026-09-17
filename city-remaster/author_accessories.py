"""Author five genuinely rebuilt market props in the proven native Merc rig.

No game deployment. Run with Blender --background --python this_file.py.
The final mesh is indexed, consolidated once per material, in the source frame.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'active/jak3/data/decompiler_out/jak3/levels/wascityb'
TAU=math.tau
BOUNDS={
 'market-crate-lod0':((-1.32793045,-.90257776,-.70546305),(1.32793045,.99594784,.77808428)),
 'market-basket-a-lod0':((-1.39655018,-1.39655018,0),(1.39655018,1.39655018,4.03447819)),
 'market-basket-b-lod0':((-1.43211448,-1.42092609,-.02237679),(1.42092609,1.40973771,1.21953499)),
 'market-sack-a-lod0':((-1.15893722,-.73951232,0),(1.11478722,.77262485,2.81456184)),
 'market-sack-b-lod0':((-1.02339125,-.76754344,0),(1.02339125,.88308764,2.10455465)),
}
DESCRIPTIONS={
 'market-crate-lod0':'Individually fitted thick boards, worn chamfers, inset lid, corner battens, diagonal bracing, recessed wooden joinery pegs.',
 'market-basket-a-lod0':'Hand-thrown curved hollow jar, thick rolled mouth, recessed foot, turning rings and a separate crossed rope cradle following the belly.',
 'market-basket-b-lod0':'Round shallow basket with interleaved three-dimensional reeds, bound rim, concave woven body and individually oriented rice grains.',
 'market-sack-a-lod0':'Open sack with asymmetrically slumped shoulders, three deep curved folds converging on the seams, an inclined rolled mouth, stitched seams and recessed level ochre contents.',
 'market-sack-b-lod0':'Soft filled sack with three deep folds converging into a leaning tied neck, asymmetric compressed belly, a slouched open cloth tail, double rope ligature, knot and stitched seam.',
}

class Builder:
    def __init__(self):self.v=[];self.f=[];self.uv=[];self.mat=[];self.col=[];self.smooth=[]
    def add(self,verts,faces,uv,mat,col=.47,smooth=True):
        offset=len(self.v);self.v.extend(verts);self.uv.extend(uv)
        for face in faces:
            self.f.append(tuple(offset+i for i in face));self.mat.append(mat);self.col.append(col);self.smooth.append(smooth)
    def surface(self,fn,nu,nv,mat,col=.47):
        verts=[];uv=[];faces=[]
        for k in range(nv+1):
            for j in range(nu+1):
                u=j/nu;v=k/nv;verts.append(fn(u,v));uv.append((u,v))
        for k in range(nv):
            for j in range(nu):
                a=k*(nu+1)+j;faces.append((a,a+1,a+nu+2,a+nu+1))
        self.add(verts,faces,uv,mat,col)
    def tube(self,points,radius,mat,col=.45,sides=5,closed=False,flat=1.):
        pts=[Vector(p) for p in points]
        if closed:pts.append(pts[0].copy())
        verts=[];uv=[];faces=[];arc=0.
        for i,p in enumerate(pts):
            before=pts[i-1] if i else (pts[-2] if closed else p)
            after=pts[i+1] if i+1<len(pts) else (pts[1] if closed else p)
            tangent=(after-before).normalized()
            normal=Vector((p.x,p.y,0))
            if normal.length<.01 or abs(tangent.dot(normal.normalized()))>.96:normal=Vector((0,0,1))
            side=tangent.cross(normal).normalized();normal=side.cross(tangent).normalized()
            if i:arc+=(p-pts[i-1]).length
            for j in range(sides):
                angle=TAU*j/sides
                verts.append(p+radius*(side*math.cos(angle)+normal*math.sin(angle)*flat))
                uv.append((arc*.8,j/sides))
        for i in range(len(pts)-1):
            for j in range(sides):
                a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
        if not closed:
            faces.append(tuple(reversed(range(sides))));faces.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
        self.add(verts,faces,uv,mat,col)
    def ellipsoid(self,center,scale,mat,seed=0,nu=8,nv=4,col=.48):
        rng=random.Random(seed);angle=rng.random()*TAU;co=Vector(center)
        def fn(u,v):
            a=TAU*u;b=math.pi*v
            x=math.cos(a)*math.sin(b)*scale[0];y=math.sin(a)*math.sin(b)*scale[1]
            return co+Vector((x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle),math.cos(b)*scale[2]))
        self.surface(fn,nu,nv,mat,col)

def smooth_profile(keys,z):
    for i in range(len(keys)-1):
        if z<=keys[i+1][0]:
            t=max(0,(z-keys[i][0])/(keys[i+1][0]-keys[i][0]));t=t*t*(3-2*t)
            return keys[i][1]*(1-t)+keys[i+1][1]*t
    return keys[-1][1]

def material_from(source,name,image_path=None):
    mat=source.copy();mat.name=name
    if image_path:
        image=bpy.data.images.load(str(image_path),check_existing=True)
        for n in mat.node_tree.nodes:
            if n.type=='TEX_IMAGE':n.image=image
    bs=mat.node_tree.nodes.get('Principled BSDF')
    if bs:
        bs.inputs['Roughness'].default_value=.86
        if 'Specular IOR Level' in bs.inputs:bs.inputs['Specular IOR Level'].default_value=.0
    return mat

def jar(b):
    profile=[(0,.85),(.07,.98),(.18,1.04),(.4,1.13),(.8,1.22),(1.35,1.29),(1.9,1.29),(2.25,1.16),(2.55,.94),(2.85,.68),(3.08,.55),(3.4,.54),(3.68,.61),(3.88,.74),(3.97,.76)]
    # Exterior and interior are one continuous shell, with a round mouth, not a capped cylinder.
    rings=[(z,smooth_profile(profile,z)) for z in [i*3.97/30 for i in range(31)]]
    rings += [(4.015,.73),(4.035,.675),(4.015,.625),(3.96,.60),(3.8,.57),(3.55,.48),(3.3,.46),(3.08,.47),(2.85,.60),(2.55,.85),(2.25,1.06),(1.9,1.17),(1.35,1.17),(.8,1.08),(.35,.89),(.25,.45),(.25,.001)]
    verts=[];uv=[];faces=[];segments=48
    for k,(z,r) in enumerate(rings):
        for j in range(segments+1):
            a=TAU*j/segments
            wobble=1+.013*math.sin(3*a+.4*z)+.007*math.sin(7*a-2*z)
            throwing=.007*math.sin(z*34)*math.sin(math.pi*min(z/4,1))
            verts.append(((r+throwing)*wobble*math.cos(a),(r+throwing)*wobble*math.sin(a),z+.008*math.sin(3*a)*min(z,1)))
            uv.append((j/segments,z/4))
    for k in range(len(rings)-1):
        for j in range(segments):
            a=k*(segments+1)+j;faces.append((a,a+1,a+segments+2,a+segments+1))
    b.add(verts,faces,uv,0,.48)
    # Actual crossed cords stand proud of the ceramic. Radius follows the jar.
    for direction in (-1,1):
        for strand in range(10):
            points=[]
            for k in range(29):
                t=k/28;z=.19+t*1.65;a=TAU*strand/10+direction*t*1.8
                r=smooth_profile(profile,z)+.042+.012*math.sin(t*18+strand*math.pi)
                points.append((r*math.cos(a),r*math.sin(a),z))
            b.tube(points,.032,1,.45+(strand%3)*.01,sides=5)
    for z in (.19,.27,1.79,1.87):
        r=smooth_profile(profile,z)+.048
        b.tube([(r*math.cos(TAU*j/64),r*math.sin(TAU*j/64),z) for j in range(64)],.041,1,.46,sides=6,closed=True)
    for z,r in ((.065,.98),(.16,1.035),(3.81,.685)):
        b.tube([(r*math.cos(TAU*j/48),r*math.sin(TAU*j/48),z) for j in range(48)],.025,0,.49,sides=5,closed=True)

def basket(b):
    def radius(z):return .96+.36*math.sin(min(z/1.12,1)*math.pi*.5)
    # A thin dark weave liner is recessed behind the interlaced structural reeds.
    b.surface(lambda u,v:((radius(v*1.08)-.026)*math.cos(TAU*u),(radius(v*1.08)-.026)*math.sin(TAU*u),.04+v*1.08),48,8,0,.34)
    for row in range(10):
        z=.09+row*.107;points=[]
        for j in range(65):
            a=TAU*j/64;r=radius(z)+.027*math.cos(a*20/2+row*math.pi)
            points.append((r*math.cos(a),r*math.sin(a),z+.009*math.sin(a*3+row)))
        b.tube(points,.045,0,.42+row%3*.012,sides=4,flat=.58)
    for col in range(20):
        a=TAU*col/20;points=[]
        for j in range(23):
            z=.03+j/22*1.12;r=radius(z)+.035*math.cos((z-.09)/.107*math.pi+col*math.pi)
            points.append((r*math.cos(a),r*math.sin(a),z))
        b.tube(points,.031,0,.45,sides=4,flat=.65)
    for z,rad in ((1.095,.072),(1.185,.040),(.04,.040)):
        r=radius(min(z,1.12))
        b.tube([(r*math.cos(TAU*j/64),r*math.sin(TAU*j/64),z+.007*math.sin(TAU*j/64*3)) for j in range(64)],rad,0,.46,sides=6,closed=True)
    # A shallow grain mound, topped by distinct non-identical kernels; the old
    # flat rice polygon cannot supply this silhouette or close-up parallax.
    b.surface(lambda u,v:(math.cos(TAU*u)*v*1.25,math.sin(TAU*u)*v*1.25,1.08+.055*(1-v*v)),48,5,1,.46)
    rng=random.Random(817)
    for k in range(100):
        a=rng.random()*TAU;r=1.20*math.sqrt((k+.5)/100)
        x=r*math.cos(a);y=r*math.sin(a);z=1.085+.052*(1-(r/1.25)**2)
        b.ellipsoid((x,y,z),(.065+rng.random()*.025,.029,.018+rng.random()*.012),1,k,nu=6,nv=3,col=.45+rng.random()*.065)

def sack_fold_field(a,t,closed):
    """Three broad compression folds; no repeated fluted cylinder pattern."""
    if not .055<t<1.0:return 0.,0.
    envelope=math.sin(math.pi*(t-.055)/.945)**.8
    # The fold paths bend into the actual side seam or the gathered neck.
    centres=([-.28+.55*(1-t),-2.20-.50*(1-t),1.50+.35*(1-t)] if closed else
             [-.28-.60*(1-t),math.pi-.28+.38*(1-t),-1.82+.48*(1-t)])
    delta=0.;occlusion=0.
    for k,centre in enumerate(centres):
        distance=math.atan2(math.sin(a-centre),math.cos(a-centre))
        width=(.19,.24,.17)[k]*(1.15-.35*t)
        depression=math.exp(-(distance/width)**2)
        shoulder=math.exp(-((distance-width*1.35)/(width*.7))**2)
        depth=(.17,.13,.15)[k] if closed else (.15,.12,.14)[k]
        delta+=envelope*(-depth*depression+.045*shoulder)
        occlusion=max(occlusion,depression*envelope)
    return delta,occlusion

def sack_surface(b,closed):
    height=1.66 if closed else 2.62
    keys=([(0,.56),(.08,.77),(.28,.96),(.55,1.0),(.83,.93),(1.07,.81),(1.28,.64),(1.46,.36),(1.6,.145),(1.66,.14)] if closed else
          [(0,.52),(.08,.72),(.35,.96),(.8,1.04),(1.35,1.0),(1.95,.84),(2.35,.74),(2.62,.72)])
    def point(a,z,offset=0):
        t=z/height;r=smooth_profile(keys,z)
        lowfold=.033*math.sin(6*a+3*t)+.028*math.sin(9*a-8*t)*math.exp(-((t-.12)/.16)**2)
        gathering=(.038 if closed else .024)*math.cos(14*a+2*t)*(t**3)
        macrofold,_=sack_fold_field(a,t,closed)
        # The lower half yields to the load on one side; the opposite shoulder
        # remains fuller. Preserve the foot, then soften the upper silhouette.
        fullness=.075*math.sin(a+.9)*math.sin(math.pi*t)**1.4
        r=max(.015,r+lowfold*.65+gathering*.65+macrofold+fullness+offset)
        x=r*math.cos(a)+.06*math.sin(t*3.3)*t;y=.72*r*math.sin(a)+.03*math.sin(t*6)
        z+=.024*math.sin(3*a+1)*math.sin(math.pi*t)
        return Vector((x,y,z))
    b.surface(lambda u,v:point(TAU*u,v*height),80,40,0,.45)
    # Recessed bottom, closed to the ground, with a slightly rolled fabric seam.
    b.surface(lambda u,v:(math.cos(TAU*u)*v*.57,math.sin(TAU*u)*v*.40,.012),48,2,0,.37)
    for side in (-.28,math.pi-.28):
        seam=[point(side,.08+(height-.12)*i/35,.012) for i in range(36)]
        b.tube(seam,.012,0,.41,sides=4)
        for k in range(16 if closed else 24):
            z=.12+(height-.25)*(k+.5)/(16 if closed else 24)
            p0=point(side-.028,z-.018,.025);p1=point(side+.028,z+.018,.025)
            b.tube([p0,p1],.0085,1,.48,sides=4)
    if closed:
        # A loose fan of gathered cloth above the knot, with a visible thickness
        # and irregular rim. Folds converge on the tie rather than a cone spike.
        def fan(u,v,inside=False):
            a=TAU*u;r=.14+.25*v+.036*math.sin(9*a+.6)*v
            if inside:r-=.023
            z=height+.43*v+(.047*math.sin(3*a)+.026*math.sin(7*a))*v*v
            return (r*math.cos(a)+.043,.72*r*math.sin(a)-.014,z)
        b.surface(lambda u,v:fan(u,v),48,8,0,.47)
        b.surface(lambda u,v:fan(1-u,1-v,True),48,6,0,.38)
        b.tube([fan(j/72,1) for j in range(72)],.011,0,.47,sides=4,closed=True)
        for z in (1.605,1.66):
            b.tube([(.172*math.cos(TAU*j/40)+.042,.128*math.sin(TAU*j/40)-.013,z+.008*math.sin(TAU*j/40*3)) for j in range(40)],.028,1,.46,sides=6,closed=True)
        # A compact rope knot, one loop and two gravity-hanging tails.
        b.ellipsoid((.16,-.125,1.632),(.077,.062,.064),1,nu=10,nv=6,col=.47)
        b.tube([(.19+.12*math.sin(math.pi*t),-.14-.035*math.sin(TAU*t),1.64-.20*math.sin(math.pi*t)) for t in [j/28 for j in range(29)]],.018,1,.46,sides=5)
        for side in (-1,1):
            b.tube([(.19+side*.055*t,-.15-.026*math.sin(t*math.pi),1.60-.30*t) for t in [j/12 for j in range(13)]],.016,1,.46,sides=5)
    else:
        # Substantial folded mouth, irregularly sagged like folded heavy cloth.
        for dz,rad,col in ((0,.074,.48),(-.078,.042,.43)):
            b.tube([point(TAU*j/96,height)+Vector((0,0,dz+.043*math.sin(TAU*j/96*3))) for j in range(96)],rad,0,col,sides=8,closed=True)
        b.surface(lambda u,v:point(TAU*(1-u),height-v*.38,-.06),48,7,0,.35)
        b.surface(lambda u,v:(math.cos(TAU*u)*v*.65+.045,.72*math.sin(TAU*u)*v*.65,2.60+.09*(1-v*v)+.008*math.sin(12*TAU*u)*v),48,7,2,.48)
        rng=random.Random(161)
        for k in range(28):
            a=rng.random()*TAU;r=.60*math.sqrt(rng.random())
            b.ellipsoid((r*math.cos(a)+.045,.72*r*math.sin(a),2.61+.09*(1-(r/.65)**2)),(.045,.035,.018),2,k,nu=6,nv=3,col=.46+rng.random()*.045)
    # Pose the cloth, seams, stitches and cords together, so they remain attached.
    # The foot is fixed in this authoring frame; the final native fit keeps Y=0.
    vertex_material={i:mat for face,mat in zip(b.f,b.mat) for i in face}
    for fi,(face,mat) in enumerate(zip(b.f,b.mat)):
        if mat==0:
            co=sum((Vector(b.v[i]) for i in face),Vector())/len(face)
            _,occlusion=sack_fold_field(math.atan2(co.y/.72,co.x),co.z/height,closed)
            # Local cavity shade keeps the real fold readable with native Merc
            # lighting. It scales RGB uniformly and cannot change the cloth hue.
            b.col[fi]*=1-.20*occlusion
    for i,original in enumerate(b.v):
        co=Vector(original);t=max(0.,min(1.,co.z/height));ease=t*t*(3-2*t)
        foot_gate=max(0.,min(1.,(co.z-.10)/.20));foot_gate=foot_gate*foot_gate*(3-2*foot_gate)
        co.x+=foot_gate*ease*(.15 if closed else -.10)
        co.y-=foot_gate*ease*(.065 if closed else .035)
        if closed:
            # The loose cloth above the knot falls to one side; the ligature
            # itself follows the same leaning neck as the folded sack body.
            co.x+=max(0.,co.z-height)*.38
            co.z-=foot_gate*.065*math.sin(math.pi*t)*(1+math.sin(math.atan2(co.y/.72,co.x)-.7))*.5
        else:
            mouth_gate=max(0.,min(1.,(t-.62)/.38));mouth_gate=mouth_gate*mouth_gate*(3-2*mouth_gate)
            if vertex_material[i]==2:
                # Loose goods stay level and safely below the lowered cloth lip.
                co.z-=.19
            else:co.z+=mouth_gate*(.18*original[0]-.045*original[1])
        b.v[i]=co

def crate_parts(material):
    parts=[];rng=random.Random(322)
    def timber(name,p,dimensions,rot=None,bevel=.025):
        bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=name;o.dimensions=dimensions
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if rot:o.rotation_euler=rot
        o.data.materials.append(material)
        mod=o.modifiers.new('Worn real timber bevel','BEVEL');mod.width=bevel;mod.segments=3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        uv=o.data.uv_layers.active
        strip=.2+rng.random()*.6
        for f in o.data.polygons:
            axes=sorted(range(3),key=lambda a:abs(f.normal[a]))[:2];a,bb=sorted(axes,key=lambda a:dimensions[a],reverse=True)
            for li in f.loop_indices:
                co=o.data.vertices[o.data.loops[li].vertex_index].co
                uv.data[li].uv=(co[a]/dimensions[a]*.88+.5,co[bb]/dimensions[bb]*.18+strip)
        color=o.data.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
        brightness=.415+rng.random()*.04
        for c in color.data:c.color=(brightness,brightness,brightness,1)
        parts.append(o);return o
    # The source is a closed crate, with the same broad top supporting stacking.
    for y in (-.77,.77):
        for row in range(3):
            timber('Thick horizontal side board',(0,y,-.40+row*.40),(2.46,.105,.388),bevel=.021)
    for x in (-1.18,1.18):
        for row in range(3):
            timber('Fitted end board',(x,0,-.40+row*.40),(.11,1.57,.388),bevel=.021)
    for x in (-1.24,1.24):
        for y in (-.81,.81):
            timber('Full corner batten',(x,y,.02),(.15,.18,1.38),bevel=.026)
    for row in range(5):
        y=-.62+row*.31
        timber('Recessed individually fitted lid',(0,y,.604),(2.36,.302,.12),bevel=.017)
        timber('Real floorboard',(0,y,-.615),(2.35,.302,.11),bevel=.014)
    for x in (-.92,.92):
        timber('Lid cross brace',(x,0,.704),(.20,1.60,.10),bevel=.022)
    for y in (-.86,.86):
        timber('Mortised lower stretcher',(0,y,-.565),(2.48,.11,.16),bevel=.024)
        # A single solid diagonal, retaining the spare visual language of Jak.
        timber('Diagonal tension brace',(0,y,.065),(2.30,.095,.145),(0,-.30,0),bevel=.02)
        for x in (-1.03,1.03):
            for z in (-.50,.48):
                bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=.034,depth=.018,location=(x,y+math.copysign(.065,y),z),rotation=(math.pi/2,0,0))
                p=bpy.context.object;p.name='Recessed wooden peg';p.data.materials.append(material)
                uv=p.data.uv_layers.active
                for loop in uv.data:loop.uv=(.52,.47)
                col=p.data.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
                for c in col.data:c.color=(.37,.37,.37,1)
                parts.append(p)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    o=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return o

def render_preview(name,new,rig):
    pts=[new.matrix_world@v.co for v in new.data.vertices];lo=Vector([min(p[a] for p in pts) for a in range(3)]);hi=Vector([max(p[a] for p in pts) for a in range(3)])
    c=(lo+hi)/2;size=max(hi-lo)
    bpy.ops.object.camera_add(location=c+Vector((1.3,-1.7,1.15))*size)
    cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size*1.52
    scene=bpy.context.scene;scene.camera=cam
    for xyz,power,scale in [((1,-1,2),60,3),((-1,-.5,1),28,3),((0,2,2),55,2)]:
        bpy.ops.object.light_add(type='AREA',location=c+Vector(xyz)*size)
        light=bpy.context.object;light.data.energy=power*size*size;light.data.shape='DISK';light.data.size=scale*size;light.rotation_euler=(c-light.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('Neutral authoring inspection');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.16,1)
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1000;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(HERE/(name+'-authored.png'));scene.view_settings.view_transform='AgX'
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(name+'.blend')))
    bpy.ops.render.render(write_still=True)

def run(name):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(SOURCE/(name+'.glb')))
    old=next(o for o in bpy.context.scene.objects if o.type=='MESH');rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    originals={m.name:m for m in old.data.materials};source_triangles=len(old.data.polygons)
    if name=='market-crate-lod0':
        mats=[material_from(old.data.materials[0],'market-crate-wood-hd',HERE/'wood-hd.png')];new=crate_parts(mats[0])
    else:
        b=Builder()
        if name=='market-basket-a-lod0':
            mats=[material_from(originals['city-mark-clay-pot-01'],'market-jar-clay-hd',HERE/'market-clay-hd.png'),material_from(originals['city-mark-rope-mesh-01'],'market-jar-fibre-cords-hd',HERE/'market-cotton-hd.png')];jar(b)
        elif name=='market-basket-b-lod0':
            mats=[material_from(originals['city-mark-basket2'],'market-reed-fibres-hd',HERE/'wood-hd.png'),material_from(originals['city-mark-rice-01'],'market-rice-hd',HERE/'market-rice-hd.png')];basket(b)
        else:
            cloth=originals['city-mark-cotton-32x32'];tie=originals.get('city-mark-rope-01',originals['city-mark-cotton-wrap'])
            mats=[material_from(cloth,'market-sack-cotton-hd',HERE/'market-cotton-hd.png'),material_from(tie,'market-sack-cord-hd',HERE/'wood-hd.png')]
            if name=='market-sack-a-lod0':mats.append(material_from(originals['city-mark-clay-pot-01'],'market-ochre-contents-hd',HERE/'market-clay-hd.png'))
            sack_surface(b,name=='market-sack-b-lod0')
        data=bpy.data.meshes.new(name+'-authored-geometry');data.from_pydata(b.v,[],b.f);data.update();new=bpy.data.objects.new(name+'-new',data);bpy.context.collection.objects.link(new)
        for mat in mats:data.materials.append(mat)
        uv=data.uv_layers.new(name='UVMap');col=data.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
        for fi,face in enumerate(data.polygons):
            face.material_index=b.mat[fi];face.use_smooth=b.smooth[fi]
            shade=b.col[fi]
            for li in face.loop_indices:
                vi=data.loops[li].vertex_index;coord=b.uv[vi]
                if name=='market-basket-b-lod0' and b.mat[fi]==1:
                    # Planar projection preserves grain scale across the centre.
                    coord=(.5+b.v[vi][0]/2.60,.5+b.v[vi][1]/2.60)
                elif name=='market-sack-a-lod0' and b.mat[fi]==2:
                    coord=(.5+b.v[vi][0]/1.40,.5+b.v[vi][1]/1.10)
                elif name.startswith('market-sack-') and b.mat[fi]==0:
                    coord=(coord[0]*2.3,coord[1]*1.6)
                uv.data[li].uv=coord;col.data[li].color=(shade,shade,shade,1.)
        # Recalculate connected face orientation, keeping actual holes and mouth.
        bm=bmesh.new();bm.from_mesh(data)
        # UV sphere poles and radial centres must not leave zero-area triangles.
        bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.000001)
        bmesh.ops.dissolve_degenerate(bm,dist=.00000001,edges=bm.edges)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(data);bm.free()
    # Match the native INDEXED bounds, not Blender's imported helper vertices.
    points=[v.co.copy() for v in new.data.vertices];lo=Vector([min(p[a] for p in points) for a in range(3)]);hi=Vector([max(p[a] for p in points) for a in range(3)])
    target_lo,target_hi=map(Vector,BOUNDS[name])
    for v in new.data.vertices:
        v.co=Vector([target_lo[a]+(v.co[a]-lo[a])/(hi[a]-lo[a])*(target_hi[a]-target_lo[a]) for a in range(3)])
    for group in old.vertex_groups:new.vertex_groups.new(name=group.name)
    new.vertex_groups['main'].add(list(range(len(new.data.vertices))),1.,'REPLACE');new.parent=old.parent
    mod=new.modifiers.new('Native Merc skin','ARMATURE');mod.object=rig
    bpy.data.objects.remove(old,do_unlink=True);new.name=name
    new['authored_features']=DESCRIPTIONS[name]
    new.data.calc_loop_triangles();triangles=len(new.data.loop_triangles)
    assert triangles<=15000,(name,triangles)
    bpy.ops.object.select_all(action='DESELECT');new.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=new
    bpy.ops.export_scene.gltf(filepath=str(HERE/(name+'.glb')),export_format='GLB',use_selection=True,export_animations=False,export_apply=False,export_extras=True)
    report={'control':name,'source_triangles':source_triangles,'authored_triangles':triangles,'vertices':len(new.data.vertices),'materials':[m.name for m in new.data.materials],'bounds_blender':[list(target_lo),list(target_hi)],'joints':[g.name for g in new.vertex_groups],'weights':'All main, matching original source. Native armature retained.','features':DESCRIPTIONS[name],'deployed':False,'native_visual_validation':False}
    (HERE/(name+'-author-report.json')).write_text(json.dumps(report,indent=2))
    render_preview(name,new,rig);print(json.dumps(report),flush=True)
    return report

names=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(BOUNDS)
reports=[run(name) for name in names]
report_path=HERE/'accessories-author-report.json'
previous={r['control']:r for r in json.loads(report_path.read_text())} if report_path.exists() else {}
previous.update({r['control']:r for r in reports})
report_path.write_text(json.dumps([previous[n] for n in BOUNDS if n in previous],indent=2))
