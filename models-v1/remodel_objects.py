"""Author faithful palace objects in Blender; emit native draw-preserving patches."""
import sys,json,math
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from blender_common import *
data=json.loads((HERE/'native-objects.json').read_text())['faces']
actors=json.loads((ROOT/'desert-remaster/palace-fire.json').read_text())['actors']
components=json.loads((HERE/'object-components.json').read_text())
patch={'description':'Blender palace object remodels; native positions, UV materials and visibility retained','remove':[],'add':[]}
reports=[]

def edit_bevel(asset,width,segments=3,protected=()):
    bm=bmesh.new();bm.from_mesh(asset.obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    protected_ids={asset.materials.index(name) for name in protected if name in asset.materials}
    bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(1.5),use_dissolve_boundaries=False,
        verts=list(bm.verts),edges=list(bm.edges),delimit={'MATERIAL','UV'})
    edges=[e for e in bm.edges if len(e.link_faces)==2 and e.calc_face_angle(0)>math.radians(16)
        and not any(f.material_index in protected_ids for f in e.link_faces)]
    bmesh.ops.bevel(bm,geom=edges,offset=width,segments=segments,profile=.6,affect='EDGES',clamp_overlap=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update();bm.to_mesh(asset.obj.data);bm.free()
    for p in asset.obj.data.polygons:p.use_smooth=False
    # BMesh interpolates loop UVs through the bevel. Keep those UV islands;
    # projecting an entire new quad to one old triangle folds the arch patterns.

def record_asset(asset,targets,label,preview=False):
    info={'object':label,'original_triangles':{},'new_triangles':{},'max_surface_distance_m':{}}
    for lod,faces in sorted(targets.items()):
        remove,add,distance=asset.records(faces)
        patch['remove'].extend(remove);patch['add'].extend(add)
        info['original_triangles'][lod]=len(faces);info['new_triangles'][lod]=len(add);info['max_surface_distance_m'][lod]=distance
    if preview:
        render_asset(asset.obj,HERE/(label+'-remodel.png'),view=(3,7,3) if label=='throne' else (4,-7,3))
        save_asset(asset.obj,label+'-remodel')
    reports.append(info);print(label,info['original_triangles'],info['new_triangles'],flush=True)

def targets_where(select):
    out=defaultdict(list)
    for f in data:
        if select(f):out[f['geom']].append(f)
    return out

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
mode=args[0] if args else 'brazier'
if mode=='brazier':
    for actor in actors:
        if actor['group']!='group-waspala-crucible-fire':continue
        centre=actor['trans_m'][:3]
        def select(f):
            return f['tree_type']=='tie' and f['proto']==11 and all(abs(v['p'][0]-centre[0])<2 and abs(v['p'][2]-centre[2])<2 for v in f['vertices'])
        targets=targets_where(select);reset();asset=NativeMesh('Brazier_'+str(actor['aid']),targets[0])
        # Rebuild the bowl as a continuous turned profile. Its final ring follows
        # the original polygonal fuel boundary exactly, so the fire remains seated.
        from collections import Counter
        coal=Counter(tuple(v['p']) for f in targets[0] if f['material']=='waspala-fire-coal' for v in f['vertices'])
        bottom=Vector(max(coal,key=coal.get));rim=[Vector(p) for p in coal if Vector(p)!=bottom]
        rimcentre=sum(rim,Vector())/len(rim);axis=(rimcentre-bottom).normalized()
        u=(rim[0]-rimcentre).normalized();v=axis.cross(u).normalized();u=v.cross(axis).normalized()
        ring=sorted([(math.atan2((p-rimcentre).dot(v),(p-rimcentre).dot(u))%(2*math.pi),p) for p in rim],key=lambda q:q[0])
        def rim_at(theta):
            for k,(angle,point) in enumerate(ring):
                next_angle,next_point=ring[(k+1)%len(ring)]
                if next_angle<=angle:next_angle+=2*math.pi
                t=theta if theta>=angle else theta+2*math.pi
                if angle<=t<=next_angle:return point.lerp(next_point,(t-angle)/(next_angle-angle))
            raise AssertionError(theta)
        bm=bmesh.new();bm.from_mesh(asset.obj.data)
        for face in bm.faces:face.select=False
        bowl_id=asset.materials.index('waspala-fire-holder01')
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==bowl_id],context='FACES')
        bmesh.ops.delete(bm,geom=[vv for vv in bm.verts if not vv.link_faces],context='VERTS')
        profile=[(.292,-.766),(.42,-.72),(.57,-.65),(.703,-.579),(.88,-.475),(1.08,-.313),
                 (1.22,-.17),(1.30,-.070),(1.311,-.035),(1.30,-.010),(1.275,.003),(1.235,.005),(1.18,0),(1.13,0)]
        # The eight raised ornaments followed the old flat bowl facets. Bend
        # them onto the new wall, retaining their thickness and original UVs.
        bowl_faces=[i for i,f in enumerate(asset.faces) if f['material']=='waspala-fire-holder01']
        old_bowl=BVHTree.FromPolygons(asset.vertices,[asset.triangles[i] for i in bowl_faces],all_triangles=True)
        ornament_id=asset.materials.index('waspala-fountain-bar')
        ornament_edges=[e for e in bm.edges if e.link_faces and all(f.material_index==ornament_id for f in e.link_faces)]
        bmesh.ops.subdivide_edges(bm,edges=ornament_edges,cuts=2,use_grid_fill=True)
        for vertex in bm.verts:
            if not any(f.material_index==ornament_id for f in vertex.link_faces):continue
            point=Vector(asset.world(vertex.co));q=point-rimcentre;height=q.dot(axis);radial=q-axis*height
            if radial.length<1e-6:continue
            radius=None
            for (r0,h0),(r1,h1) in zip(profile[:9],profile[1:10]):
                if h0<=height<=h1:radius=r0+(r1-r0)*(height-h0)/(h1-h0);break
            if radius is None:continue
            nearest,_,_,_=old_bowl.find_nearest(vertex.co)
            nq=Vector(asset.world(nearest))-rimcentre;old_radius=(nq-axis*nq.dot(axis)).length
            relief=max(.009,min(.065,radial.length-old_radius))
            vertex.co=asset.local(rimcentre+axis*height+radial.normalized()*(radius+relief))
        segments=64;rows=[]
        for ri,(radius,height) in enumerate(profile):
            row=[]
            for j in range(segments):
                theta=j*2*math.pi/segments;point=rimcentre+(u*math.cos(theta)+v*math.sin(theta))*radius+axis*height
                if ri==len(profile)-1:point=rim_at(theta)
                row.append(bm.verts.new(asset.local(point)))
            rows.append(row)
        for a,b in zip(rows,rows[1:]):
            for j in range(segments):
                face=bm.faces.new((a[j],a[(j+1)%segments],b[(j+1)%segments],b[j]));face.material_index=bowl_id;face.smooth=True;face.select=True
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update();bm.to_mesh(asset.obj.data);bm.free()
        asset.assign_uv(only_selected=True)
        # The original feet remain while the bowl is validated; the discarded
        # global bevel trial is never installed in the game.
        record_asset(asset,targets,'brazier-'+str(actor['aid']),actor['aid']==45101)
elif mode=='planter':
    pots=[c for c in components if c['tree_type']=='tie' and c['proto']==27 and 'waspala-column-plate' in c['materials']]
    for number,pot in enumerate(pots):
        centre=pot['centre'];radius=max(pot['max'][0]-pot['min'][0],pot['max'][2]-pot['min'][2])*.5
        instance=data[pot['face_indices'][0]]['instance']
        def select(f):
            return f['tree_type']=='tie' and f['proto']==27 and f['instance']==instance and f['material']=='waspala-column-plate'
        targets=targets_where(select);reset();asset=NativeMesh('Planter_'+str(number),targets[0])
        height=pot['max'][1]-pot['min'][1]
        # Continuous ceramic shoulder, rounded rolled lip and an inset inner rim.
        # Ratios are measured on the original eight-ring meridian.
        profile=[(.636,0),(.905,.1786),(1,.4048),(.96,.6667),(.784,.8571),(.843,.9286),(.784,1),(.725,.9286)]
        def catmull(a,b,c,d,t):return .5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
        rows=[]
        for i in range(len(profile)-1):
            a=Vector(profile[max(0,i-1)]);b=Vector(profile[i]);c=Vector(profile[i+1]);d=Vector(profile[min(len(profile)-1,i+2)])
            for step in range(4):
                p=catmull(a,b,c,d,step/4);rows.append((min(p.x,1),max(0,min(1,p.y))))
        rows.append(profile[-1]);segments=48;verts=[];faces=[]
        for r,h in rows:
            for j in range(segments):
                theta=2*math.pi*j/segments
                # Subtle turned-clay grooves are geometry, bounded inside the original pot.
                rr=radius*r*(1-.0025*math.sin(h*math.pi*28)**2)
                verts.append(asset.local([centre[0]+rr*math.cos(theta),pot['min'][1]+height*h,centre[2]+rr*math.sin(theta)]))
        for row in range(len(rows)-1):
            for j in range(segments):
                k=row*segments+j;n=row*segments+(j+1)%segments;faces.append((k,k+segments,n+segments,n))
        mesh=bpy.data.meshes.new('Turned ceramic');mesh.from_pydata(verts,[],faces);mesh.materials.append(asset.obj.data.materials[0]);mesh.update();asset.obj.data=mesh
        for p in mesh.polygons:p.use_smooth=True
        asset.assign_uv()
        record_asset(asset,targets,'planter-'+str(number),abs(centre[0]-2014.9878)<.05 and abs(centre[2]+420.1931)<.05)
elif mode=='throne':
    targets=targets_where(lambda f:f['tree_type']=='tfrag' and f['material'].startswith('waspala-throne') and f['material'] not in ('waspala-throne-floor','waspala-throne-cushion'))
    reset();asset=NativeMesh('Throne sculpted frame',targets[0]);edit_bevel(asset,.025,3)
    record_asset(asset,targets,'throne',True)
    targets=targets_where(lambda f:f['tree_type']=='tfrag' and f['material']=='waspala-throne-cushion')
    asset=NativeMesh('Throne padded leather',targets[0]);corners=[Vector(p) for p in (
        (2000.484008789,247.453109741,-414.843963623),(2001.577758789,247.453109741,-414.843963623),
        (2000.218505859,249.312271118,-414.718841553),(2001.843261719,249.312271118,-414.718841553))]
    verts=[];faces=[];nx=20;ny=28
    for y in range(ny+1):
        vv=y/ny
        for x in range(nx+1):
            uu=x/nx;point=corners[0].lerp(corners[1],uu).lerp(corners[2].lerp(corners[3],uu),vv)
            puff=(max(0,math.sin(math.pi*uu)*math.sin(math.pi*vv)))**.6
            point.z-=.18*puff
            point.z+=.008*math.sin(uu*43+vv*9)*puff*(abs(uu-.5)*2)**8
            verts.append(asset.local(point))
    for y in range(ny):
        for x in range(nx):
            k=y*(nx+1)+x;faces.append((k,k+1,k+nx+2,k+nx+1))
    mesh=bpy.data.meshes.new('Padded leather surface');mesh.from_pydata(verts,[],faces);mesh.materials.append(asset.obj.data.materials[0]);mesh.update();asset.obj.data=mesh
    for polygon in mesh.polygons:polygon.use_smooth=True
    asset.assign_uv();record_asset(asset,targets,'throne-cushion',True)
    # Rivets already have independent meshes. Round their machined edges too.
    targets=targets_where(lambda f:f['tree_type']=='tie' and f['proto']==18)
    asset=NativeMesh('Throne rivets',targets[0]);edit_bevel(asset,.012,3)
    record_asset(asset,targets,'throne-rivets')
else:raise ValueError(mode)
(HERE/(mode+'-patch.json')).write_text(json.dumps(patch,separators=(',',':')))
(HERE/(mode+'-report.json')).write_text(json.dumps(reports,indent=2))
print('Saved',mode,len(patch['remove']),'->',len(patch['add']),flush=True)
