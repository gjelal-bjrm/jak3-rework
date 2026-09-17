"""Second art pass: modeled leaf blades, hanging plants and layered throne details."""
import sys,json,math,random
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'models-v1'))
from blender_common import *
from mathutils.geometry import barycentric_transform
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
DATA=json.loads((HERE/'native-objects.json').read_text())['faces']

class Builder:
    def __init__(self,asset,keep=False):
        self.asset=asset;self.v=[];self.f=[];self.uv=[];self.mat=[]
        if keep:
            mesh=asset.obj.data
            self.v=[v.co.copy() for v in mesh.vertices]
            for p in mesh.polygons:
                self.f.append(tuple(p.vertices));self.mat.append(p.material_index)
                self.uv.append([tuple(mesh.uv_layers.active.data[l].uv) for l in p.loop_indices])
    def face(self,points,uv,material):
        start=len(self.v);self.v.extend(self.asset.local(p) for p in points)
        self.f.append(tuple(range(start,start+len(points))));self.uv.append(uv);self.mat.append(self.asset.materials.index(material))
    def tube(self,points,radius,material,sides=8,uvcentre=(.50,.18)):
        points=[Vector(p) for p in points];rows=[]
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            u=tangent.cross(Vector((0,0,1)))
            if u.length<.01:u=tangent.cross(Vector((0,1,0)))
            u.normalize();v=tangent.cross(u).normalized()
            r=radius[i] if isinstance(radius,list) else radius
            rows.append([p+r*(u*math.cos(j*2*math.pi/sides)+v*math.sin(j*2*math.pi/sides)) for j in range(sides)])
        for i in range(len(rows)-1):
            for j in range(sides):
                self.face([rows[i][j],rows[i][(j+1)%sides],rows[i+1][(j+1)%sides],rows[i+1][j]],
                    [(uvcentre[0]+x*.055,uvcentre[1]+y*.055) for x,y in ((0,0),(1,0),(1,1),(0,1))],material)
    def leaf(self,root,tip,width,normal,material,seed=0,steps=7):
        root,tip,normal=Vector(root),Vector(tip),Vector(normal).normalized();axis=tip-root
        side=axis.cross(normal).normalized();length=axis.length;rng=random.Random(seed)
        curl=length*rng.uniform(.09,.20);twist=rng.uniform(-.24,.24);rows=[]
        for i in range(steps+1):
            t=i/steps;c=root+axis*t+normal*(curl*math.sin(math.pi*t)-length*.11*t*t)
            c+=side*(twist*width*math.sin(math.pi*t))
            w=width*max(.012,math.sin(math.pi*t)**.75)*(1-.34*t)
            rows.append([c-side*w-normal*w*.16,c+normal*w*.10,c+side*w-normal*w*.16])
        for i in range(steps):
            for j in range(2):
                pts=[rows[i][j],rows[i+1][j],rows[i+1][j+1],rows[i][j+1]]
                uv=[(j/2,i/steps),(j/2,(i+1)/steps),((j+1)/2,(i+1)/steps),((j+1)/2,i/steps)]
                self.face(pts,uv,material)
    def box(self,lo,hi,material,uvcentre=(.35,.22)):
        lo,hi=Vector(lo),Vector(hi)
        ps=[Vector((x,y,z)) for z in (lo.z,hi.z) for y in (lo.y,hi.y) for x in (lo.x,hi.x)]
        for ids in ((0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)):
            self.face([ps[i] for i in ids],[(uvcentre[0]+x*.08,uvcentre[1]+y*.08) for x,y in ((0,0),(1,0),(1,1),(0,1))],material)
    def finish(self,smooth=True):
        # Shared vertices are essential: smooth shading cannot cross disconnected quads.
        vertices=[];remap=[];lookup={}
        for v in self.v:
            key=tuple(round(x,6) for x in v)
            if key not in lookup:lookup[key]=len(vertices);vertices.append(v)
            remap.append(lookup[key])
        faces=[tuple(remap[i] for i in f) for f in self.f]
        mesh=bpy.data.meshes.new(self.asset.obj.name+' authored');mesh.from_pydata(vertices,[],faces)
        for material in self.asset.obj.data.materials:mesh.materials.append(material)
        layer=mesh.uv_layers.new(name='UVMap')
        for p,uv,mat in zip(mesh.polygons,self.uv,self.mat):
            p.material_index=mat;p.use_smooth=smooth
            for li,st in zip(p.loop_indices,uv):layer.data[li].uv=st
        mesh.update();self.asset.obj.data=mesh

def write_patch(assets,name,report):
    patch={'description':'Second authored detail pass, full individual leaves and layered ornament','remove':[],'add':[]}
    for asset,targets in assets:
        for lod,faces in targets.items():
            remove,add,distance=asset.records(faces);patch['remove']+=remove;patch['add']+=add
        bpy.data.objects.remove(asset.obj,do_unlink=True)
    (HERE/(name+'-patch.json')).write_text(json.dumps(patch,separators=(',',':')))
    report.update(removed=len(patch['remove']),added=len(patch['add']))
    (HERE/(name+'-report.json')).write_text(json.dumps(report,indent=2));print(report,flush=True)

def targets_select(predicate):
    out=defaultdict(list)
    for f in DATA:
        if predicate(f):out[f['geom']].append(f)
    return out

def uv_point(faces,u,v):
    p=Vector((u,v,0));best=None
    for f in faces:
        uv=[Vector((*vv['uv'],0)) for vv in f['vertices']]
        q=closest_point_on_tri(p,*uv);distance=(q-p).length_squared
        if best is None or distance<best[0]:
            best=(distance,barycentric_transform(q,*uv,*[Vector(vv['p']) for vv in f['vertices']]))
    return best[1]

def foliage():
    groups=defaultdict(lambda:defaultdict(list))
    for f in DATA:
        if (f['tree_type']=='tie' and f['proto'] in (24,25,26)) or f['tree_type']=='shrub':
            groups[(f['tree_type'],f['tree'],f['proto'],f['instance'],f['material'])][f['geom']].append(f)
    reset();assets=[];counts=defaultdict(int);saved=set()
    # Read one freshly authored albedo for all modeled green blades.
    leafimage=bpy.data.images.load(str(HERE/'leaf-tissue-master.png'),check_existing=True);leafimage.pack()
    for key,targets in groups.items():
        typ,tree,proto,instance,material=key;faces=targets[0]
        asset=NativeMesh('Detailed_'+str(proto)+'_'+str(instance),faces);builder=Builder(asset)
        points=[Vector(v['p']) for f in faces for v in f['vertices']]
        lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
        size=hi-lo;centre=(lo+hi)*.5;rng=random.Random(instance+proto*900)
        if typ=='tie' and proto==26:
            root=uv_point(faces,.99365,.00781)
            # Thirteen separate blades instead of a textured rectangular fan.
            for i in range(13):
                theta=(i+.6)/13*math.pi*.5
                reach=min(.985/max(math.cos(theta),math.sin(theta)),rng.uniform(.98,1.19))
                tip=uv_point(faces,.99365-reach*math.cos(theta),.00781+reach*math.sin(theta))
                n=(uv_point(faces,.18,.1)-root).cross(uv_point(faces,.9,.8)-root).normalized()
                if n.y<0:n=-n
                builder.leaf(root,tip,(tip-root).length*rng.uniform(.027,.040),n,material,instance*19+i,9)
                counts['palm_blades']+=1
        elif typ=='tie' and proto==25:
            # Rounded petiole follows the existing branch centreline.
            axis=max(range(3),key=lambda a:size[a]);ordered=sorted(points,key=lambda p:p[axis]);a=sum(ordered[:6],Vector())/6;b=sum(ordered[-6:],Vector())/6
            path=[a.lerp(b,j/8)+Vector((0,math.sin(j/8*math.pi)*size.length*.06,0)) for j in range(9)]
            builder.tube(path,[max(.012,size.length*.04*(1-j/10)) for j in range(9)],material,8)
            counts['petioles']+=1
        elif typ=='tie' and proto==24:
            # Separate, tapered old fronds form the crown skirt, not an opaque curtain.
            for i in range(24):
                angle=2*math.pi*i/24;radial=Vector((math.cos(angle),0,math.sin(angle)))
                root=Vector((centre.x,hi.y-.08*size.y,centre.z))+radial*min(size.x,size.z)*.24
                tip=Vector((centre.x,lo.y+rng.uniform(0,.20)*size.y,centre.z))+radial*min(size.x,size.z)*rng.uniform(.36,.49)
                builder.leaf(root,tip,min(size.x,size.z)*.055,radial,material,i+instance,6)
            counts['crown_skirts']+=1
        else:
            # Shrub instances include the hanging greenery around the palace lamps.
            hanging=size.y>max(size.x,size.z)*.7 and centre.y>246
            stems=10 if hanging else 14
            for i in range(stems):
                angle=i*2.39996+rng.uniform(-.2,.2);radial=Vector((math.cos(angle),0,math.sin(angle)))
                base=Vector((centre.x,hi.y-.10*size.y if hanging else lo.y+.04*size.y,centre.z))
                base+=radial*min(size.x,size.z)*rng.uniform(.08,.24)
                end=base+radial*min(size.x,size.z)*rng.uniform(.24,.40)
                end.y=lo.y+rng.uniform(.02,.26)*size.y if hanging else lo.y+rng.uniform(.65,.95)*size.y
                path=[base.lerp(end,j/8)+radial*math.sin(j/8*math.pi)*min(size.x,size.z)*.12 for j in range(9)]
                builder.tube(path,[.007*(1-j/10) for j in range(9)],material,6,uvcentre=(.48,.2))
                for j in range(1,15):
                    t=j/15;root=base.lerp(end,t)+radial*math.sin(t*math.pi)*min(size.x,size.z)*.12
                    tangent=Vector((-radial.z,0,radial.x))*(1 if j%2 else -1)
                    leaflength=min(size.length*.23,.62)*rng.uniform(.75,1.15)
                    direction=(radial*.55+tangent*.65+Vector((0,-.45 if hanging else .65,0))).normalized()
                    builder.leaf(root,root+direction*leaflength,leaflength*.28,radial+Vector((0,.7,0)),material,instance*73+i*9+j,6)
                    counts['shrub_leaves']+=1
            counts['hanging_plants' if hanging else 'shrubs']+=1
        builder.finish()
        if proto!=25 and proto!=24:
            for mat in asset.obj.data.materials:
                for node in mat.node_tree.nodes:
                    if node.type=='TEX_IMAGE':node.image=leafimage
        category='palm' if proto==26 and typ=='tie' else ('hanging' if typ=='shrub' else 'other')
        if category not in saved and category!='other':
            render_asset(asset.obj,HERE/(category+'-v2.png'),view=(3,-6,3));
            bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(category+'-v2.blend')));saved.add(category)
        assets.append((asset,targets))
        if len(assets)%70==0:print('Plants built',len(assets),dict(counts),flush=True)
    write_patch(assets,'foliage',dict(counts))

def throne():
    reset();targets=targets_select(lambda f:f['tree_type']=='tfrag' and f['material'].startswith('waspala-throne') and f['material']!='waspala-throne-floor')
    asset=NativeMesh('Throne layered craftsmanship',targets[0])
    bm=bmesh.new();bm.from_mesh(asset.obj.data)
    bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(1.5),use_dissolve_boundaries=False,verts=list(bm.verts),edges=list(bm.edges),delimit={'MATERIAL','UV'})
    edges=[e for e in bm.edges if len(e.link_faces)==2 and e.calc_face_angle(0)>math.radians(18)]
    bmesh.ops.bevel(bm,geom=edges,offset=.032,segments=3,affect='EDGES',clamp_overlap=True)
    bm.to_mesh(asset.obj.data);bm.free();b=Builder(asset,keep=True)
    wood='waspala-throne-back-02';metal='waspala-throne-back-03';leather='waspala-throne-cushion';base='waspala-throne-base'
    cx=2001.1325;cy=246.859;front=-413.70
    # Layered bronze mouldings follow the characteristic wide throne arch.
    for rx,ry,z,r in ((3.09,3.87,front-.035,.046),(2.87,3.63,front-.075,.052),(2.27,2.81,front-.085,.039)):
        path=[Vector((cx+rx*math.cos(a*math.pi/72),cy+ry*math.sin(a*math.pi/72),z)) for a in range(73)]
        b.tube(path,r,metal,10,uvcentre=(.38,.22))
    # Deep bronze rays read as separate carved elements at gameplay distance.
    for i in range(15):
        angle=(i+1)*math.pi/16
        centre=Vector((cx+2.55*math.cos(angle),cy+3.18*math.sin(angle),front-.085))
        radial=Vector((math.cos(angle),1.22*math.sin(angle),0)).normalized();side=Vector((-radial.y,radial.x,0))
        shape=[centre-radial*.32,centre+side*.11,centre+radial*.32,centre-side*.11]
        nose=centre+Vector((0,0,-.105))
        for j in range(4):b.face([shape[j],shape[(j+1)%4],nose],[(.32,.23),(.46,.25),(.39,.31)],metal)
    # Cushion with deliberately visible soft volume, diamond tufting, stitched piping.
    corners=[Vector(p) for p in ((2000.484,247.453,-414.845),(2001.578,247.453,-414.845),(2000.219,249.312,-414.719),(2001.843,249.312,-414.719))]
    nx,ny=32,42;rows=[]
    for j in range(ny+1):
        t=j/ny;row=[]
        for i in range(nx+1):
            u=i/nx;p=corners[0].lerp(corners[1],u).lerp(corners[2].lerp(corners[3],u),t)
            puff=max(0,math.sin(math.pi*u)*math.sin(math.pi*t))**.45
            diamond=abs(math.sin((u*3+t*4)*math.pi)*math.sin((u*3-t*4)*math.pi))
            p.z-=.045+.23*puff+.04*diamond*puff;row.append(p)
        rows.append(row)
    for j in range(ny):
        for i in range(nx):b.face([rows[j][i],rows[j][i+1],rows[j+1][i+1],rows[j+1][i]],[(i/nx,j/ny),((i+1)/nx,j/ny),((i+1)/nx,(j+1)/ny),(i/nx,(j+1)/ny)],leather)
    border=rows[0]+[r[-1] for r in rows[1:]]+list(reversed(rows[-1][:-1]))+[r[0] for r in reversed(rows[1:-1])]+[rows[0][0]]
    b.tube([p+Vector((0,0,-.024)) for p in border],.020,metal,7,uvcentre=(.38,.24))
    for j in range(1,4):
        for i in range(1,4):
            p=rows[round(j*ny/4)][round(i*nx/4)]+Vector((0,0,-.007))
            b.tube([p,p+Vector((0,0,-.03))],[.029,.022],metal,10)
    # Full seat upholstery and a perimeter seam replace the visually bare seat.
    sx0,sx1,sz0,sz1=2000.39,2001.66,-415.60,-414.90
    for j in range(16):
        for i in range(24):
            points=[];uv=[]
            for u,v in ((i/24,j/16),((i+1)/24,j/16),((i+1)/24,(j+1)/16),(i/24,(j+1)/16)):
                h=.09+.12*max(0,math.sin(math.pi*u)*math.sin(math.pi*v))**.5
                points.append(Vector((sx0+(sx1-sx0)*u,247.30+h,sz0+(sz1-sz0)*v)));uv.append((u,v))
            b.face(points,uv,leather)
    perimeter=[(sx0,247.39,sz0),(sx1,247.39,sz0),(sx1,247.39,sz1),(sx0,247.39,sz1),(sx0,247.39,sz0)]
    b.tube(perimeter,.021,metal,8)
    for x in (2000.25,2001.78):
        # Bronze bindings on each armrest plus a substantial layered front cap.
        for z in (-415.58,-415.23,-414.91):
            b.box((x-.184,247.565,z-.045),(x+.184,247.735,z+.045),metal)
        b.box((x-.20,247.56,-415.79),(x+.20,247.76,-415.66),metal)
    # Crossbar and small repeated relief facets on the seat apron.
    b.box((2000.34,247.12,-415.71),(2001.69,247.23,-415.60),wood)
    for x,z in ((2000.24,-415.51),(2001.80,-415.51),(2000.38,-414.82),(2001.65,-414.82)):
        foot=Vector((x,246.42,z));top=Vector((2001.03+(x-2001.03)*.83,247.20,z+.06))
        b.tube([foot,foot.lerp(top,.15),foot.lerp(top,.85),top],[.105,.13,.11,.15],base,10)
        b.tube([foot+Vector((0,.015,0)),foot+Vector((0,.09,0))],.128,metal,10)
    for i in range(9):
        x=2000.44+i*.143;y=247.17;z=-415.73
        b.face([(x-.045,y,z),(x,y+.06,z),(x+.045,y,z),(x,y-.05,z)],[(.32,.22),(.37,.27),(.42,.22),(.37,.17)],metal)
    b.finish(False)
    # Smooth only upholstery; keep crisp intentional facets in bronze decoration.
    for p in asset.obj.data.polygons:p.use_smooth=asset.materials[p.material_index]==leather or (asset.materials[p.material_index]==metal and len(p.vertices)==4)
    render_asset(asset.obj,HERE/'throne-v2.png',view=(2,7,2.5),resolution=1200)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'throne-v2.blend'))
    bpy.ops.object.select_all(action='DESELECT');asset.obj.select_set(True);bpy.context.view_layer.objects.active=asset.obj
    bpy.ops.export_scene.gltf(filepath=str(HERE/'throne-v2.glb'),export_format='GLB',use_selection=True)
    write_patch([(asset,targets)],'throne',{'mouldings':3,'bronze_relief_rays':15,'padded_seat':True,'tufted_back':True,'armrest_bindings':6})

mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'throne'
throne() if mode=='throne' else foliage()
