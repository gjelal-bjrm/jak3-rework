"""Author complete market palms from native anchors; never read/write live FR3s.

Run with Blender --background --python city-remaster/palms/author.py.
Patch positions/normals are world-space, Y-up metres. The bridge preserves each
native TIE_WIND matrix, wind_index and stiffness and performs the inverse transform.
"""
import json, math, random, sys, hashlib
from pathlib import Path
from collections import defaultdict
import bpy
from mathutils import Vector, Matrix

HERE=Path(__file__).resolve().parent; CITY=HERE.parent; ROOT=CITY.parent
sys.path.insert(0,str(ROOT/'models-v1'))
from blender_common import NativeMesh, reset

NATIVE=json.loads((CITY/'market-plants-native.json').read_text())
MAP=json.loads((CITY/'market-plants-map.json').read_text())
FACEMAP=defaultdict(list)
for face in NATIVE['faces']:
    if face['tree_type'] in ('tie','tie_wind'):
        FACEMAP[(face['tree_type'],face['instance'],face['geom'])].append(face)
INVMAP={(i['tree_type'],i['instance'],i['geom']):i for i in NATIVE['instance_inventory']}
LEAF_TEXTURE='market-palm-leaf-v1'
LEAF_IMAGE=ROOT/'models-v2/leaf-tissue-1024.png'
TRUNK_TEXTURE='market-palm-trunk-v1'
TRUNK_IMAGE=ROOT/'terrain-v1/masters/waspala-palmtree-trunk-01.png'
ORIGIN=Vector((1767,28,-335))

def lerp(a,b,t):return a*(1-t)+b*t
def smooth(t):return t*t*(3-2*t)
def native_matrix(inv):
    return Matrix([[inv['matrix_columns'][c][r] for c in range(3)] for r in range(3)])

class Author:
    def __init__(self,kind,instance,lod):
        self.kind=kind;self.instance=instance;self.lod=lod
        self.faces=FACEMAP[(kind,instance,lod)];self.inv=INVMAP[(kind,instance,lod)]
        self.matrix=native_matrix(self.inv);self.anchor=Vector(self.inv['origin_m'])
        self.asset=NativeMesh(f'MarketPalm_{kind}_{instance}_LOD{lod}',self.faces,origin=ORIGIN)
        self.material=self.asset.materials[0]
        self.points=[];self.polygons=[];self.uvs=[];self.smooth=[]
        self.local_points=list({tuple(round(v,5) for v in self.matrix.inverted()@(Vector(q['p'])-self.anchor)) for f in self.faces for q in f['vertices']})
        self.local_points=[Vector(p) for p in self.local_points]
        self.texture=None

    def world(self,p):return self.anchor+self.matrix@Vector(p)

    def face(self,ps,uv,smooth_shading=True):
        start=len(self.points)
        self.points.extend(self.asset.local(self.world(p)) for p in ps)
        self.polygons.append(tuple(range(start,start+len(ps))))
        self.uvs.append(uv);self.smooth.append(smooth_shading)

    def tube(self,path,radii,sides=6,uv_repeat=1):
        rows=[]
        for i,p in enumerate(path):
            tangent=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
            side=tangent.cross(Vector((0,1,0)))
            if side.length<.01:side=tangent.cross(Vector((0,0,1)))
            side.normalize();other=tangent.cross(side).normalized()
            rows.append([p+(side*math.cos(2*math.pi*j/sides)+other*math.sin(2*math.pi*j/sides))*radii[i] for j in range(sides)])
        for i in range(len(rows)-1):
            for j in range(sides):
                self.face([rows[i][j],rows[i][(j+1)%sides],rows[i+1][(j+1)%sides],rows[i+1][j]],[(j/sides,i/(len(rows)-1)*uv_repeat),((j+1)/sides,i/(len(rows)-1)*uv_repeat),((j+1)/sides,(i+1)/(len(rows)-1)*uv_repeat),(j/sides,(i+1)/(len(rows)-1)*uv_repeat)])

    def blade(self,root,tip,width,normal,seed,steps,fold=.18,uv_box=(0,0,1,1)):
        root,tip,normal=Vector(root),Vector(tip),Vector(normal).normalized()
        axis=tip-root;side=axis.cross(normal).normalized();length=axis.length
        rng=random.Random(seed);curl=rng.uniform(.035,.095)*length
        twist=rng.uniform(-.24,.24)*width;rows=[]
        for i in range(steps+1):
            t=i/steps
            c=root+axis*t+normal*(math.sin(math.pi*t)*curl-.05*length*t*t)
            c+=side*math.sin(math.pi*t)*twist
            w=max(.001,width*math.sin(math.pi*(.045+.955*t))**.8)*(1-.3*t)
            if i==steps:w=.0005
            rows.append([c-side*w-normal*w*fold,c+normal*w*.13,c+side*w-normal*w*fold])
        u0,v0,u1,v1=uv_box
        for i in range(steps):
            for j in range(2):
                ps=[rows[i][j],rows[i+1][j],rows[i+1][j+1],rows[i][j+1]]
                uv=[(lerp(u0,u1,j/2),lerp(v0,v1,i/steps)),(lerp(u0,u1,j/2),lerp(v0,v1,(i+1)/steps)),(lerp(u0,u1,(j+1)/2),lerp(v0,v1,(i+1)/steps)),(lerp(u0,u1,(j+1)/2),lerp(v0,v1,i/steps))]
                self.face(list(reversed(ps)),list(reversed(uv)))

    def finish(self):
        # Weld adjacent rows so smooth normals can cross the authored surface.
        verts=[];indices=[];lookup={}
        for p in self.points:
            key=tuple(round(v,6) for v in p)
            if key not in lookup:lookup[key]=len(verts);verts.append(p)
            indices.append(lookup[key])
        mesh=bpy.data.meshes.new(self.asset.obj.name+'_authored')
        mesh.from_pydata(verts,[],[tuple(indices[i] for i in f) for f in self.polygons]);mesh.update()
        for m in self.asset.obj.data.materials:mesh.materials.append(m)
        uv=mesh.uv_layers.new(name='UVMap')
        for polygon,st,is_smooth in zip(mesh.polygons,self.uvs,self.smooth):
            polygon.use_smooth=is_smooth
            for li,pair in zip(polygon.loop_indices,st):uv.data[li].uv=(pair[0],1-pair[1])
        self.asset.obj.data=mesh
        if self.texture:
            old=mesh.materials[0];mat=old.copy();mat.name=self.texture
            image=bpy.data.images.load(str(LEAF_IMAGE if self.texture==LEAF_TEXTURE else TRUNK_IMAGE),check_existing=True);image.pack()
            for n in mat.node_tree.nodes:
                if n.type=='TEX_IMAGE':n.image=image
            mesh.materials[0]=mat
        else:
            mat=mesh.materials[0].copy();mesh.materials[0]=mat
            # PS2 alpha 128 is opaque in game. Match it in diagnostic Blender.
            if 'beard' in self.material:
                shader=mat.node_tree.nodes.get('Principled BSDF')
                tex=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE')
                scale=mat.node_tree.nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=2
                mat.node_tree.links.new(tex.outputs['Alpha'],scale.inputs[0]);mat.node_tree.links.new(scale.outputs[0],shader.inputs['Alpha'])
        shader=mesh.materials[0].node_tree.nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value=.86
        shader.inputs['Specular IOR Level'].default_value=.18
        self.asset.obj['native_instance']=self.instance
        self.asset.obj['native_type']=self.kind
        self.asset.obj['native_matrix_columns']=json.dumps(self.inv['matrix_columns'])
        for key in ('wind_index','stiffness'):
            if key in self.inv:self.asset.obj[key]=self.inv[key]
        self.asset.obj['geom']=self.lod
        self.asset.obj['patch_coordinates']='world Y-up metres'
        mesh.calc_loop_triangles()
        return len(mesh.loop_triangles)

    def records(self):
        remove,add,distance=self.asset.records(self.faces)
        for record in remove+add:record['instance']=self.instance
        for record in add:
            for vertex in record['vertices']:
                # Closest-point barycentrics can undershoot zero by 1e-5 in
                # float32. A convex palette interpolation is required in FR3.
                weights=[max(0,min(1,w)) for w in vertex['color_weights']]
                total=sum(weights);vertex['color_weights']=[w/total for w in weights]
        if self.texture:
            for record in add:record['texture']=self.texture
        return remove,add,distance

def trunk(a):
    a.texture=TRUNK_TEXTURE
    # Nine irregular native rings define the actual curved trunk and root flare.
    # New section and individually raised palm scars replace the old octagon.
    ps=sorted(a.local_points,key=lambda p:p.y)
    rings=[ps[i:i+8] for i in range(0,len(ps),8)]
    centres=[sum(r,Vector())/len(r) for r in rings]
    radii=[sum(math.hypot(p.x-c.x,p.z-c.z) for p in r)/len(r) for r,c in zip(rings,centres)]
    y0,y1=centres[0].y,centres[-1].y
    def frame(t):
        y=lerp(y0,y1,t);k=next((i for i in range(len(centres)-1) if centres[i+1].y>=y),len(centres)-2)
        q=max(0,min(1,(y-centres[k].y)/(centres[k+1].y-centres[k].y)))
        return centres[k].lerp(centres[k+1],smooth(q)),lerp(radii[k],radii[k+1],smooth(q))
    row_count=(52,36,24,14)[a.lod];sides=(20,16,12,8)[a.lod];rows=[]
    for i in range(row_count+1):
        t=i/row_count;c,r=frame(t);row=[]
        for j in range(sides):
            angle=2*math.pi*j/sides
            relief=.027*math.sin(angle*11+t*4)+.018*math.sin(angle*17-t*7)
            collar=.045*math.sin(t*math.pi*58)**6
            rr=r*(1+relief)+collar*(.25+.75*t)
            row.append(c+Vector((math.cos(angle)*rr,0,math.sin(angle)*rr)))
        rows.append(row)
    for i in range(row_count):
        for j in range(sides):
            a.face([rows[i][j],rows[i+1][j],rows[i+1][(j+1)%sides],rows[i][(j+1)%sides]],[(j/sides*3,7*i/row_count),(j/sides*3,7*(i+1)/row_count),((j+1)/sides*3,7*(i+1)/row_count),((j+1)/sides*3,7*i/row_count)])
    # Raised diamond scars are genuine separate bark volume, not subdivision.
    if a.lod<3:
        nr=(31,22,12)[a.lod];ns=(8,7,5)[a.lod]
        for k in range(nr):
            t=.14+.84*(k+.5)/nr;c,r=frame(t)
            for j in range(ns):
                angle=(j+(k%2)*.5)*2*math.pi/ns
                radial=Vector((math.cos(angle),0,math.sin(angle)));side=Vector((-radial.z,0,radial.x))
                p=c+radial*(r+.012);half_w=r*math.pi/ns*.88;half_h=(y1-y0)/nr*.41
                outline=[p+Vector((0,half_h,0)),p+side*half_w,p-Vector((0,half_h*.65,0)),p-side*half_w]
                nose=p+radial*(.023 if a.lod==0 else .018)+Vector((0,-half_h*.12,0))
                for m in range(4):a.face([outline[m],outline[(m+1)%4],nose],[(.24,.12),(.72,.16),(.48,.64)],True)
    # Native root flare remains broad; eight organic ribs deepen its silhouette.
    if a.lod<2:
        for j in range(8):
            angle=j*math.pi/4+.12;radial=Vector((math.cos(angle),0,math.sin(angle)))
            path=[];r=[]
            for k in range(8):
                t=.01+.17*k/7;c,radius=frame(t);path.append(c+radial*radius*.92);r.append(.16*(1-k/8))
            a.tube(path,r,5,1)
    return {'bark_scars':0 if a.lod==3 else nr*ns,'curved_native_rings':len(rings)}

def crown(a):
    a.texture=LEAF_TEXTURE
    # Each original wind component is a pair of opposing long arching fronds.
    # The original envelope supplies length, arch and droop; folioles are new.
    count=(25,17,11,7)[a.lod];steps=(4,4,3,2)[a.lod]
    stats={'rachises':2,'individual_leaflets':0}
    # The native cards started below their attachment. Retain that overlap with
    # a crown heart so the animated fronds cannot appear to float above the trunk.
    a.tube([Vector((0,-1.45,0)),Vector((0,-.6,0)),Vector((0,0,0)),Vector((0,.25,0))],[.43,.49,.29,.12],(10,8,6,5)[a.lod])
    for sign in (-1,1):
        vertices=[p for p in a.local_points if p.z*sign>-.1]
        length=max(p.z*sign for p in vertices)
        def centre(t):
            z=length*t*sign
            # Retain the strong drooping silhouette distinctive to these palms.
            ys=[p.y for p in vertices if abs(p.z-z)<max(.9,length*.13)]
            if not ys:
                nearest=sorted(vertices,key=lambda p:abs(p.z-z))[:5];ys=[p.y for p in nearest]
            # Fit a smooth arch rather than following jagged card rows.
            end=[p.y for p in sorted(vertices,key=lambda p:-p.z*sign)[:6]]
            droop=sum(end)/len(end)
            y=1.75*math.sin(math.pi*t)-abs(droop)*t**2.35
            return Vector((.1*math.sin(t*math.pi),y,z))
        path=[centre(i/((16,12,8,5)[a.lod])) for i in range((16,12,8,5)[a.lod]+1)]
        a.tube(path,[max(.018,.10*(1-i/(len(path)-1))+.012) for i in range(len(path))],(7,6,5,4)[a.lod])
        for k in range(count):
            t=.07+.89*(k+.35)/count;root=centre(t)
            for side in (-1,1):
                rng=random.Random(a.instance*991+k*31+side)
                # Feather width tapers toward both root and drooping tip.
                reach=(1.62 if sign>0 else 1.48)*math.sin(math.pi*t)**.42*(1-.34*t)
                reach*=rng.uniform(.90,1.08)
                tip=root+Vector((side*reach,-reach*rng.uniform(.18,.42),sign*(.22+.50*t)))
                # Small stagger makes the paired leaves feel grown, not combed.
                tip.z+=rng.uniform(-.10,.10)
                width=(.255,.31,.39,.48)[a.lod]*math.sin(math.pi*t)**.25
                a.blade(root,tip,width,(0,1,-sign*.15),a.instance*701+k*13+side,steps,fold=.18)
                stats['individual_leaflets']+=1
        # A single tapered continuation closes the frond tip naturally.
        a.blade(centre(.93),centre(1.015),.11,(0,1,0),sign+11,steps,fold=.16)
    return stats

def beard(a):
    ps=a.local_points;top=max(p.y for p in ps);bottom=min(p.y for p in ps)
    upper=[p for p in ps if p.y>top-.5];c=sum(upper,Vector())/len(upper)
    bottom_radius=sum(math.hypot(p.x,p.z) for p in ps if p.y<bottom+2)/max(1,len([p for p in ps if p.y<bottom+2]))
    strands=(23,17,11,7)[a.lod];steps=(6,4,3,2)[a.lod]
    for j in range(strands):
        rng=random.Random(a.instance*1009+j);angle=2*math.pi*(j+.16*rng.random())/strands
        radial=Vector((math.cos(angle),0,math.sin(angle)));side=Vector((-radial.z,0,radial.x))
        root=Vector((c.x,top-.1,c.z))+radial*.84
        tip=Vector((c.x,lerp(bottom,top,rng.uniform(.01,.15)),c.z))+radial*bottom_radius*rng.uniform(.80,1.04)
        tip+=side*rng.uniform(-.20,.20)
        # The source texture supplies the green-to-dry transition; narrow safe
        # UV windows avoid copying its old rectangular silhouette onto new leaves.
        u=.36+(j%3)*.045
        a.blade(root,tip,(.32,.39,.48,.62)[a.lod],radial,a.instance*53+j,steps,fold=.28,uv_box=(u,.05,u+.045,.76))
    return {'separate_dry_fronds':strands}

def preview(objects,name,close=False):
    scene=bpy.context.scene
    for obj in scene.objects:obj.hide_render=obj not in objects
    scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.render.resolution_x=1400;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.world.color=(.10,.12,.15)
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.45
    coords=[obj.matrix_world@Vector(v) for obj in objects for v in obj.bound_box]
    lo=Vector([min(p[i] for p in coords) for i in range(3)]);hi=Vector([max(p[i] for p in coords) for i in range(3)])
    centre=(lo+hi)*.5;size=max(hi-lo)
    if close:centre.z=27;size=23
    camera_data=bpy.data.cameras.new('Palm inspection camera');camera=bpy.data.objects.new('Palm inspection camera',camera_data);scene.collection.objects.link(camera)
    camera.location=centre+Vector((1.0,-2.4,.42 if close else .65)).normalized()*size*2.4
    camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=size*(1.15 if close else 1.42);scene.camera=camera
    lamps=[]
    for vec,energy in [((-3,-4,6),1400),((4,1,4),900),((0,4,5),1100)]:
        data=bpy.data.lights.new('Palm inspection softbox','AREA');data.energy=energy*size*size/16;data.shape='DISK';data.size=size
        lamp=bpy.data.objects.new(data.name,data);scene.collection.objects.link(lamp);lamp.location=centre+Vector(vec)*size/3;lamp.rotation_euler=(centre-lamp.location).to_track_quat('-Z','Y').to_euler();lamps.append(lamp)
    scene.render.filepath=str(HERE/name);bpy.ops.render.render(write_still=True)
    for obj in [camera,*lamps]:bpy.data.objects.remove(obj,do_unlink=True)

def main():
    HERE.mkdir(exist_ok=True);reset();patch={'description':'Complete sculpted market palms: worked trunk bark, arching rachises, separate curved leaflets and dry fronds; native wind anchors preserved','remove':[],'add':[],'new_textures':[]}
    report={'source':'market-plants-native.json','source_sha256':hashlib.sha256((CITY/'market-plants-native.json').read_bytes()).hexdigest(),'native_wind_preserved_by_bridge':True,'assets':[],'native_visual_validation':False,'live_files_written':False}
    lod0=[]
    for palm in MAP['palms']:
        for part in palm['parts_geom0']:
            kind,instance=part['tree_type'],part['instance']
            for lod in range(4):
                a=Author(kind,instance,lod)
                if kind=='tie':details=trunk(a)
                elif 'leaf' in a.material:details=crown(a)
                else:details=beard(a)
                tris=a.finish();remove,add,distance=a.records();patch['remove']+=remove;patch['add']+=add
                report['assets'].append({'kind':kind,'instance':instance,'lod':lod,'removed':len(remove),'triangles':tris,'details':details,'max_native_surface_distance_m':distance,'matrix_columns':a.inv['matrix_columns'],'wind_index':a.inv.get('wind_index'),'stiffness':a.inv.get('stiffness')})
                a.asset.obj.hide_render=lod!=0;a.asset.obj.hide_set(lod!=0)
                if lod==0:lod0.append(a.asset.obj)
                print(kind,instance,'LOD',lod,'triangles',tris,flush=True)
    # Dedicated approved tissue texture: never replace the shared leaf atlas.
    tissue=ROOT/'models-v2/leaf-tissue.rgba'
    assert tissue.stat().st_size==1024*1024*4
    trunk_rgba=HERE/'trunk-tissue.rgba'
    assert trunk_rgba.stat().st_size==887*1774*4
    patch['new_textures']=[{'name':LEAF_TEXTURE,'page':'remaster-market-plants','width':1024,'height':1024,'rgba_file':str(tissue.resolve())},{'name':TRUNK_TEXTURE,'page':'remaster-market-plants','width':887,'height':1774,'rgba_file':str(trunk_rgba.resolve())}]
    report['texture_reference']=LEAF_TEXTURE;report['texture_sha256']=hashlib.sha256(tissue.read_bytes()).hexdigest()
    report['removed']=len(patch['remove']);report['added']=len(patch['add'])
    report['triangles_by_lod']={str(lod):sum(a['triangles'] for a in report['assets'] if a['lod']==lod) for lod in range(4)}
    (HERE/'palms-patch.json').write_text(json.dumps(patch,separators=(',',':')))
    (HERE/'palms-report.json').write_text(json.dumps(report,indent=2))
    preview(lod0,'palms-complete.png');preview([obj for obj in lod0 if obj['native_type']=='tie_wind'],'palms-crowns.png',True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'market-palms.blend'))
    print(json.dumps({'removed':report['removed'],'added':report['added'],'triangles_by_lod':report['triangles_by_lod']},indent=2),flush=True)

if __name__=='__main__':main()
