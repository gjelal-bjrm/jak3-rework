"""Blender room authors, in metres. +Z outside; the room extends toward -Z.

Floor is y=0; opening/window floor offset is applied by the runtime placement.
No game file is modified. Furniture and walls are actual meshes, not pictures.
"""
from pathlib import Path
import bpy, math, json, struct, hashlib
from mathutils import Vector

HERE=Path(__file__).resolve().parent
CITY=HERE.parents[1]
W,H,D=4.3,3.65,3.65
MATERIALS=[
    ('sunbaked plaster',(.61,.43,.25),.93,0),
    ('warm stone',(.38,.32,.24),.88,0),
    ('carved wood',(.24,.13,.060),.70,1),
    ('copper bindings',(.34,.18,.073),.43,0),
    ('ochre canvas',(.59,.31,.105),.92,2),
    ('deep teal canvas',(.12,.26,.22),.94,2),
    ('clay vessels',(.56,.23,.10),.82,0),
    ('dark rug',(.28,.13,.068),.98,2),
    ('rug border',(.63,.40,.15),.95,2),
    ('plant green',(.22,.29,.060),.62,0),
    ('dark bronze',(.12,.095,.065),.52,0),
    ('lamplight glass',(.94,.48,.12),.30,0),
]

def local(p):return (p[0],-p[2],p[1])
def material(index):return bpy.data.materials[MATERIALS[index][0]]
def finish(obj,name,mat):
    obj.name=name;obj.data.materials.append(material(mat));obj['material_index']=mat
    return obj
def cube(name,p,size,mat,bevel=.025,rot=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=local(p))
    o=bpy.context.object;o.dimensions=(size[0],size[2],size[1]);o.rotation_euler.z=rot
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('rounded construction edges','BEVEL');m.width=bevel;m.segments=3
        m=o.modifiers.new('weighted face normals','WEIGHTED_NORMAL');m.keep_sharp=True
    return finish(o,name,mat)
def ellipsoid(name,p,size,mat,rotate=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=local(p))
    o=bpy.context.object;o.scale=(size[0],size[2],size[1]);o.rotation_euler.z=rotate
    for f in o.data.polygons:f.use_smooth=True
    return finish(o,name,mat)
def rod(name,a,b,r,mat,vertices=12):
    av,bv=Vector(local(a)),Vector(local(b));d=bv-av
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d.length,location=(av+bv)*.5)
    o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return finish(o,name,mat)
def vase(name,p,height,radius,mat):
    profile=[(0,.54),(.08,.7),(.20,.94),(.43,1),(.65,.82),(.79,.58),(.87,.45),(.96,.45),(1,.54),(.985,.40),(.87,.34),(.73,.42),(.69,0)]
    verts=[];faces=[];n=24
    for y,r in profile:
        for i in range(n):
            a=i*math.tau/n;verts.append(local((p[0]+math.cos(a)*radius*r,p[1]+y*height,p[2]+math.sin(a)*radius*r)))
    for ring in range(len(profile)-1):
        for i in range(n):
            j=(i+1)%n;faces.append((ring*n+i,ring*n+j,(ring+1)*n+j,(ring+1)*n+i))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
    for f in mesh.polygons:f.use_smooth=True
    return finish(o,name,mat)
def cushion(name,p,size,mat,rotate=0):
    o=cube(name,p,size,mat,min(size)*.31,rotate)
    # Visible piping follows the cushion edges without substituting a flat map.
    for sign in(-1,1):
        rod(name+' stitched edge', (p[0]-size[0]*.39,p[1]+size[1]*.20,p[2]+sign*size[2]*.42),
            (p[0]+size[0]*.39,p[1]+size[1]*.20,p[2]+sign*size[2]*.42),.008,8)
    return o

def scene(layout):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for name,rgb,rough,tex in MATERIALS:
        m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
        bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(*rgb,1)
        bsdf.inputs['Roughness'].default_value=rough
    cube('rear plaster wall',(0,H/2,-D),(W,H,.18),0,.06)
    cube('left plaster wall',(-W/2,H/2,-D/2),(.18,H,D),0,.06)
    cube('right plaster wall',(W/2,H/2,-D/2),(.18,H,D),0,.06)
    cube('ceiling',(0,H+.06,-D/2),(W,.17,D),0,.04)
    cube('floor',(0,-.09,-D/2),(W,.18,D+.05),1,.03)
    for x in(-1.65,-.82,0,.82,1.65):
        cube('roof timber',(x,H-.08,-D/2),(.17,.26,D),2,.04)
        for z in(-.35,-D+.4):cube('beam bronze strap',(x,H-.12,z),(.20,.28,.08),3,.008)
    for side in(-1,1):cube('wall foot course',(side*(W/2-.10),.13,-D/2),(.15,.26,D),1,.045)
    cube('woven rug',(0,.025,-1.75),(2.78,.035,1.70),7,.012)
    for x in(-1.29,1.29):cube('rug woven border',(x,.046,-1.75),(.10,.012,1.66),8,.004)
    for z in(-.98,-2.51):cube('rug woven border',(0,.046,z),(2.58,.012,.10),8,.004)
    for x in(-.8,0,.8):cube('rug diamond',(x,.052,-1.75),(.28,.01,.28),5,.01,math.pi/4)
    # Built-in side storage, with contents rather than a texture of shelves.
    for y in(.52,1.30,2.08):
        cube('storage shelf',(1.72,y,-2.74),(.65,.10,1.12),2,.025)
        for z in(-2.3,-3.13):cube('shelf bracket',(1.87,y-.17,z),(.24,.29,.08),3,.018)
        for i in range(2):vase('shelf clay jar',(1.60,y+.06,-2.44-i*.44),.34+i*.12,.12+i*.035,6)
    # Framed woven wall panel and clay items connect the room to Spargus.
    cube('wall textile',(0,2.14,-D+.12),(1.25,.9,.03),5,.015)
    for x in(-.65,.65):cube('textile side trim',(x,2.14,-D+.17),(.07,1.02,.07),2,.016)
    for y in(1.66,2.62):cube('textile top trim',(0,y,-D+.17),(1.36,.07,.07),2,.016)
    for x in(-.30,0,.30):cube('textile ochre lozenge',(x,2.14,-D+.16),(.15,.33,.02),8,.01)
    vase('floor water pot',(-1.72,.015,-2.72),.86,.34,6)
    vase('small floor jar',(-1.40,.015,-3.05),.54,.25,6)
    # Open pendant cage with glowing glass, no painted or static flame.
    rod('lamp suspension',(0,H-.2,-1.7),(0,2.70,-1.7),.018,10)
    ellipsoid('lamp glass',(0,2.62,-1.7),(.13,.17,.13),11)
    for i in range(6):
        a=i*math.tau/6;rod('lamp cage',(math.cos(a)*.17,2.47,-1.7+math.sin(a)*.17),
            (math.cos(a)*.17,2.78,-1.7+math.sin(a)*.17),.012,3)
    if layout=='lounge':
        cube('sofa timber frame',(-.3,.31,-2.55),(2.48,.28,.90),2,.085)
        for x in(-1.38,.78):
            for z in(-2.20,-2.89):rod('sofa carved legs',(x,.03,z),(x,.35,z),.068,2)
            cube('sofa arm',(x,.68,-2.55),(.19,.46,.94),2,.065)
        for i,x in enumerate((-1.00,-.28,.44)):
            cushion('sofa seat '+str(i),(x,.54,-2.49),(.71,.25,.72),4 if i%2 else 5,(i-1)*.015)
            cushion('sofa back '+str(i),(x,.99,-2.92),(.73,.72,.23),4 if i%2 else 5,(i-1)*.02)
        cube('sofa back timber',(-.28,.81,-3.03),(2.38,.80,.12),2,.035)
        cube('low table',(0,.52,-1.2),(1.33,.14,.68),2,.06)
        for x in(-.5,.5):
            for z in(-1.43,-.98):rod('table splayed legs',(x*1.1,.04,z),(x,.49,z),.048,2)
        vase('table cup',(.32,.60,-1.17),.19,.085,6)
        vase('table pitcher',(-.2,.60,-1.28),.30,.13,6)
    else:
        cube('wall bench',(-.40,.48,-3.05),(2.48,.20,.64),2,.06)
        cushion('bench cushion',(-.40,.64,-3.05),(2.28,.17,.56),5)
        cube('side conversation table',(1.1,.90,-1.45),(.88,.13,.66),2,.055)
        for x in(.78,1.40):
            for z in(-1.67,-1.22):rod('conversation table legs',(x,.02,z),(x,.87,z),.055,2)
        for x in(.95,1.25):vase('conversation cup',(x,.97,-1.46),.18,.075,6)
    return [o for o in bpy.context.scene.objects if o.type=='MESH']

def export(objects,layout):
    verts=[];draws=[];deps=bpy.context.evaluated_depsgraph_get()
    for o in sorted(objects,key=lambda x:(x['material_index'],x.name)):
        e=o.evaluated_get(deps);m=e.to_mesh();m.calc_loop_triangles();start=len(verts)
        for tri in m.loop_triangles:
            for vi,li in zip(tri.vertices,tri.loops):
                p=e.matrix_world@m.vertices[vi].co
                n=e.matrix_world.to_3x3().inverted().transposed()@m.corner_normals[li].vector;n.normalize()
                q=(p.x,p.z,-p.y);normal=(n.x,n.z,-n.y)
                # Procedural local metre UV, continuous over each material.
                uv=(q[0]*.7+q[2]*.23,q[1]*.7+q[2]*.6)
                verts.append((*q,*normal,*uv,1.,1.,1.,1.))
        count=len(verts)-start;mi=o['material_index']
        if draws and draws[-1]['material']==mi:draws[-1]['count']+=count
        else:draws.append({'first':start,'count':count,'material':mi})
        e.to_mesh_clear()
    binary=HERE/(layout+'.bin')
    with binary.open('wb')as f:
        for row in verts:f.write(struct.pack('<12f',*row))
    meta={'schema':'city-room-mesh-v1','units':'metres','floor_y':0,'dimensions':[W,H,D],
          'binary':binary.name,'stride_floats':12,'vertex_count':len(verts),'draws':draws,
          'materials':[{'name':n,'color':list(c),'roughness':r,'texture_kind':t,'emissive':n=='lamplight glass'}for n,c,r,t in MATERIALS],
          'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
    (HERE/(layout+'.json')).write_text(json.dumps(meta,indent=2)+'\n')

def preview(layout):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.world.color=(.13,.13,.13);scene.render.resolution_x=1000;scene.render.resolution_y=1000
    scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
    camdata=bpy.data.cameras.new('street view through opening');cam=bpy.data.objects.new('street view through opening',camdata)
    scene.collection.objects.link(cam);cam.location=local((-.15,1.8,5.5))
    target=Vector(local((0,1.45,-1.8)));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.lens=38;scene.camera=cam
    for name,p,color,power,size in [('window daylight',(0,2,2.2),(1.,.84,.61),750,4),('warm room lamp',(0,2.8,-1.6),(1.,.62,.27),140,1.2)]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
        o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=local(p)
        o.rotation_euler=(Vector(local((0,1,-2)))-o.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(HERE/(layout+'-preview.png'));bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(layout+'.blend')))

for layout in('lounge','conversation'):
    objects=scene(layout);export(objects,layout);preview(layout)
print('Authored room furniture and visible interiors; no runtime files changed.',flush=True)
