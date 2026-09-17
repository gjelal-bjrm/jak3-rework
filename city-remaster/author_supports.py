"""Author the 14 complete market timber supports, arms and 28 iron links.

Reconstructs swept, hewn timber and forged joinery from native attachment
locations, rather than subdividing the original square beams. No deployment.
Run with Blender --background --python city-remaster/author_supports.py.
"""
from pathlib import Path
import sys,json,math,hashlib
import bpy,bmesh,numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'models-v1'))
from blender_common import NativeMesh,reset,render_asset
OUT=HERE/'supports';OUT.mkdir(exist_ok=True)
SOURCE=json.loads((HERE/'market-block-native.json').read_text())
WOOD='wascity-wood-plain';METAL='wascity-metal-dirty';LINK='city-port-bigpipe-ring-side'
NAMES={WOOD:'market-support-wood-v1',METAL:'market-support-metal-v1',LINK:'market-support-metal-v1'}

def points(faces):
    return np.unique(np.round(np.array([v['p'] for f in faces for v in f['vertices']]),5),axis=0)

def frame(axis):
    a=Vector(axis).normalized();ref=Vector((0,1,0)) if abs(a.y)<.9 else Vector((1,0,0))
    b=a.cross(ref).normalized();return a,b,a.cross(b).normalized()

class Builder:
    def __init__(self,native):self.native=native;self.vertices=[];self.faces=[];self.uvs=[];self.mats=[]
    def face(self,ps,uv,mat):
        n=len(self.vertices);self.vertices.extend(self.native.local(p) for p in ps)
        self.faces.append(list(range(n,n+len(ps))));self.uvs.append(uv);self.mats.append(self.native.materials.index(mat))
    def plate(self,outline,axis,thickness,mat):
        axis=Vector(axis).normalized();front=[Vector(p)+axis*thickness*.5 for p in outline];back=[Vector(p)-axis*thickness*.5 for p in outline]
        uv=[(i/(len(outline)-1),i%2) for i in range(len(outline))]
        self.face(front,uv,mat);self.face(list(reversed(back)),list(reversed(uv)),mat)
        for i in range(len(outline)):
            j=(i+1)%len(outline);self.face([front[i],back[i],back[j],front[j]],[(0,0),(0,.08),(1,.08),(1,0)],mat)
    def tube(self,centres,radii,mat,sides=16,grain=False,irregular=0):
        centres=[Vector(x) for x in centres];rings=[];distance=[0]
        for i,c in enumerate(centres):
            if i:distance.append(distance[-1]+(c-centres[i-1]).length)
            tangent=centres[min(i+1,len(centres)-1)]-centres[max(0,i-1)]
            a,u,v=frame(tangent);ring=[]
            for j in range(sides):
                theta=2*math.pi*j/sides
                r=radii[i]*(1+irregular*(.62*math.sin(theta*3+.7)+.38*math.sin(theta*7+i*.15)))
                ring.append(c+(u*math.cos(theta)+v*math.sin(theta))*r)
            rings.append(ring)
        for i in range(len(rings)-1):
            for j in range(sides):
                k=(j+1)%sides
                uv=[(distance[i]/2,j/sides),(distance[i]/2,(j+1)/sides),(distance[i+1]/2,(j+1)/sides),(distance[i+1]/2,j/sides)]
                self.face([rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j]],uv,mat)
        for i,rev in [(0,True),(len(rings)-1,False)]:
            for j in range(sides):
                k=(j+1)%sides;p=[centres[i],rings[i][j],rings[i][k]];uv=[(.5,.5),(.5+.45*math.cos(2*math.pi*j/sides),.5+.45*math.sin(2*math.pi*j/sides)),(.5+.45*math.cos(2*math.pi*k/sides),.5+.45*math.sin(2*math.pi*k/sides))]
                if rev:p.reverse();uv.reverse()
                self.face(p,uv,mat)
    def torus(self,centre,axis,major,minor,mat,n=24,m=8,rough=.014):
        centre=Vector(centre);a,u,v=frame(axis);rings=[]
        for i in range(n):
            t=2*math.pi*i/n;d=u*math.cos(t)+v*math.sin(t);r=major*(1+rough*math.sin(3*t+.4))
            rings.append([centre+d*(r+minor*math.cos(2*math.pi*j/m))+a*minor*math.sin(2*math.pi*j/m) for j in range(m)])
        for i in range(n):
            for j in range(m):
                self.face([rings[i][j],rings[(i+1)%n][j],rings[(i+1)%n][(j+1)%m],rings[i][(j+1)%m]],[(i/n,j/m),((i+1)/n,j/m),((i+1)/n,(j+1)/m),(i/n,(j+1)/m)],mat)
    def finish(self):
        mesh=bpy.data.meshes.new(self.native.obj.name+' authored');mesh.from_pydata(self.vertices,[],self.faces);mesh.update()
        for material in self.native.obj.data.materials:mesh.materials.append(material)
        uv=mesh.uv_layers.new(name='UVMap')
        for p,coords,mat in zip(mesh.polygons,self.uvs,self.mats):
            p.material_index=mat;p.use_smooth=True
            for loop,st in zip(p.loop_indices,coords):uv.data[loop].uv=(st[0],1-st[1])
        self.native.obj.data=mesh
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00003)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()

def timber_sections(faces):
    p=points(faces);centre=p.mean(axis=0);_,_,axes=np.linalg.svd(p-centre,full_matrices=False);axis=axes[0]
    if axis[1]<0:axis=-axis
    ts=(p-centre)@axis
    # Five authored cross sections; two post cap centres join the end rings.
    means=np.linspace(ts.min(),ts.max(),5)
    for iteration in range(40):
        labels=np.argmin(abs(ts[:,None]-means),axis=1)
        new=np.array([ts[labels==i].mean() if np.any(labels==i) else means[i] for i in range(5)])
        if np.max(abs(new-means))<1e-8:break
        means=new
    centres=[];radii=[]
    for i in np.argsort(means):
        group=p[labels==i];c=group.mean(axis=0);off=group-c;rad=np.linalg.norm(off-np.outer(off@axis,axis),axis=1)
        # Ignore cap centre when measuring the section. Convert square corner
        # radius to a rounded hewn section of similar visible width.
        r=float(np.median(rad[rad>max(rad)*.5]))*.80
        centres.append(c);radii.append(r)
    return np.array(centres),np.array(radii)

def sample_curve(centres,radii,steps):
    cp=np.vstack([centres[0],centres,centres[-1]]);out=[];rs=[]
    for i in range(len(centres)-1):
        a,b,c,d=cp[i:i+4]
        for k in range(steps):
            t=k/steps
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
            rs.append(radii[i]*(1-t)+radii[i+1]*t)
    out.append(centres[-1]);rs.append(radii[-1])
    # Small end bevels, preserving the endpoints and maximum length.
    out.insert(1,np.array(out[0])*.92+np.array(out[1])*.08);rs.insert(1,rs[0]);rs[0]*=.87
    out.insert(-1,np.array(out[-1])*.92+np.array(out[-2])*.08);rs.insert(-1,rs[-1]);rs[-1]*=.86
    return out,rs

def curve_nearest(point,curve,radii):
    point=Vector(point);best=None
    for i in range(len(curve)-1):
        a=Vector(curve[i]);d=Vector(curve[i+1])-a
        if d.length_squared<1e-12:continue
        t=max(0,min(1,(point-a).dot(d)/d.length_squared));q=a+d*t;distance=(point-q).length
        if best is None or distance<best[0]:best=(distance,q,d.normalized(),radii[i]*(1-t)+radii[i+1]*t)
    return best[1:]

def components(faces):
    coords={};parents=[]
    def find(a):
        while parents[a]!=a:parents[a]=parents[parents[a]];a=parents[a]
        return a
    for f in faces:
        ids=[]
        for v in f['vertices']:
            key=tuple(round(x,4) for x in v['p'])
            if key not in coords:coords[key]=len(parents);parents.append(len(parents))
            ids.append(coords[key])
        for a in ids[1:]:parents[find(a)]=find(ids[0])
    grouped={}
    for p,i in coords.items():grouped.setdefault(find(i),[]).append(p)
    return [np.array(x) for x in grouped.values()]

def make(native,geom,proto):
    b=Builder(native);sides=[16,12,10,8][geom];steps=[7,5,3,2][geom]
    if proto in (19,20):
        wood=[f for f in native.faces if f['material']==WOOD]
        centres,radii=timber_sections(wood);curve,rs=sample_curve(centres,radii,steps)
        b.tube(curve,rs,WOOD,sides,grain=True,irregular=.035)
        if proto==19:
            for pts in components([f for f in native.faces if f['material']==METAL]):
                c,tangent,wood_radius=curve_nearest(pts.mean(axis=0),curve,rs)
                axis,u,v=frame(tangent);projection=(pts-np.array(c))@np.array(axis);half=max(.035,(projection.max()-projection.min())*.5)
                # Collars grip the rebuilt timber, with flared rolled edges.
                radius=wood_radius+.022;profile=[(-half,.97),(-half+.014,1.02),(-half*.5,1.02),(0,1.02),(half*.5,1.02),(half-.014,1.02),(half,.97)]
                collar=[curve_nearest(c+axis*x,curve,rs) for x,r in profile]
                b.tube([p[0] for p in collar],[(p[2]+.023)*r for p,(x,r) in zip(collar,profile)],METAL,sides)
                for p in [collar[0],collar[-1]]:b.torus(p[0],p[1],p[2]+.025,.012,METAL,sides,6,0)
                if geom<3:
                    for j in range(4):
                        d=u*math.cos(j*math.pi/2+.3)+v*math.sin(j*math.pi/2+.3);base=Vector(c)+d*radius
                        b.tube([base,base+d*.025,base+d*.031],[.026,.026,.019],METAL,8)
            # The original upper fitting projects away from the shaft. A
            # centered collar alone leaves the awning arm floating. Rebuild
            # a forked iron bracket and socket to the unchanged arm anchor.
            arm_for_post={501:515,502:516,504:517,503:518,505:519,506:520,507:521,508:522,509:523,511:524,512:525,510:526,513:527,514:528}
            instance=native.faces[0]['instance'];arm_faces=[f for f in SOURCE['faces'] if f['tree_type']=='tie' and f['tree']==1 and f['geom']==0 and f['instance']==arm_for_post[instance]]
            arm_centres,arm_radii=timber_sections(arm_faces)
            end=min([0,-1],key=lambda i:(Vector(arm_centres[i])-curve_nearest(arm_centres[i],curve,rs)[0]).length)
            anchor=Vector(arm_centres[end]);inner=Vector(arm_centres[1 if end==0 else -2]);along=(inner-anchor).normalized()
            post,up,post_radius=curve_nearest(anchor,curve,rs);reach=anchor-post;side=up.cross(reach).normalized();arm_radius=arm_radii[end]
            attach=post+reach.normalized()*(post_radius*.72)
            # Two thick cheek plates carry the load, leaving an open central
            # fork around the socket, with a visible transverse retaining pin.
            outline=[attach-up*.27,anchor-up*.12,anchor+along*.19-up*.06,anchor+along*.19+up*.11,attach+up*.20]
            for sign in [-1,1]:b.plate([p+side*(arm_radius*.67)*sign for p in outline],side,.040,METAL)
            b.tube([anchor-along*.045,anchor,anchor+along*.21,anchor+along*.235],[arm_radius+.015,arm_radius+.025,arm_radius+.025,arm_radius+.012],METAL,sides)
            pin=anchor+along*.10
            b.tube([pin-side*(arm_radius+.045),pin+side*(arm_radius+.045)],[.039,.039],METAL,8)
    else:
        pts=points(native.faces);centre=pts.mean(axis=0);_,_,axes=np.linalg.svd(pts-centre,full_matrices=False);axis=axes[-1]
        off=pts-centre;ax=off@axis;rad=np.linalg.norm(off-np.outer(ax,axis),axis=1)
        major=(rad.max()+rad.min())*.5;minor=max(float(abs(ax).max()),float((rad.max()-rad.min())*.5))
        b.torus(centre,axis,major,minor,LINK,[32,24,16,12][geom],[10,8,6,6][geom])
    b.finish()
    if proto==19:
        # Rounded cross sections and bevels must not lift the original feet.
        # Match their lowest native contact exactly, blending within 20 cm;
        # upper collars, beam ends and attachment points do not move.
        original_min=min(v['p'][1] for f in native.faces if f['material']==WOOD for v in f['vertices'])
        minimum=min(v.co.z+native.origin.y for v in native.obj.data.vertices)
        delta=minimum-original_min
        if delta>0:
            for v in native.obj.data.vertices:
                weight=max(0,min(1,(minimum+.20-(v.co.z+native.origin.y))/.20))
                v.co.z-=delta*weight
            native.obj.data.update()
    return b

def main():
    reset();faces=[f for f in SOURCE['faces'] if f['tree_type']=='tie' and f['tree']==1 and ((f['proto']==19 and 501<=f['instance']<=514) or (f['proto']==20 and 515<=f['instance']<=528) or (f['proto']==21 and 533<=f['instance']<=560))]
    patch={'level':'wascityb','preserve_bvh':True,'remove':[],'add':[]};report=[];keep=[]
    for instance in sorted({f['instance'] for f in faces}):
        high=[f for f in faces if f['instance']==instance and f['geom']==0]
        proto=high[0]['proto'];native=NativeMesh(f'Market support {instance}',high)
        if instance==511:render_asset(native.obj,OUT/'post-original.png',view=(5,-8,3),resolution=900)
        for mat in native.obj.data.materials:
            node=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');asset=HERE/('support-wood-hd.png' if mat.name==WOOD else 'support-metal-hd.png')
            node.image=bpy.data.images.load(str(asset),check_existing=True);node.image.pack()
        for geom in range(4):
            target=[f for f in faces if f['instance']==instance and f['geom']==geom]
            if not target:continue
            make(native,geom,proto);remove,add,distance=native.records(target)
            for record,triangle in zip(add,native.obj.data.loop_triangles):
                record['texture']=NAMES[native.materials[triangle.material_index]]
            patch['remove'].extend(remove);patch['add'].extend(add)
            report.append({'instance':instance,'proto':proto,'lod':geom,'old_triangles':len(remove),'new_triangles':len(add),'max_surface_offset_m':distance})
            if geom==0:
                authored=native.obj.copy();authored.data=native.obj.data.copy();bpy.context.collection.objects.link(authored);authored.name+= ' LOD0';keep.append(authored)
                if instance in (511,524,552):render_asset(authored,OUT/(f'support-{instance}.png'),view=(5,-8,3),resolution=1100)
        bpy.data.objects.remove(native.obj,do_unlink=True)
    # Store models at native-relative origin for exact reimport and inspection.
    for obj in keep:obj.hide_render=False;obj.location=Vector(obj['native_origin']);obj.location=(obj.location.x,-obj.location.z,obj.location.y)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'market-supports.blend'))
    (OUT/'patch.json').write_text(json.dumps(patch,separators=(',',':')))
    (OUT/'author-report.json').write_text(json.dumps({'source_export_sha256':hashlib.sha256((HERE/'market-block-native.json').read_bytes()).hexdigest(),'instances':56,'posts':14,'arms':14,'rings':28,'geometry':report,'total_old_triangles':len(patch['remove']),'total_new_triangles':len(patch['add']),'status':'Authored only; native integration pending'},indent=2))
    print('SUPPORTS_DONE',len(patch['remove']),len(patch['add']))

if __name__=='__main__':main()
