"""Blender reconstruction of repeated Spargus hollow metal window frames.

Retains native glass/envmap and dark recess faces, openings, anchors and palette.
Adds a rolled reveal, projecting sculpted sill, outer-edge bevels and fasteners.
Writes per-level patches only. No native import, compilation or deployment.
"""
from pathlib import Path
from collections import defaultdict,Counter
import sys,json,math,hashlib
import bpy,bmesh,numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'models-v1'))
from blender_common import NativeMesh,reset,render_asset
MAT='wascity-metal-segments'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def matrix(row):return np.array(row['matrix_columns'],float)[:3,:3].T,np.array(row['origin_m'],float)
def unique(fs):return np.unique(np.round(np.array([v['p']for f in fs for v in f['vertices']]),5),axis=0)

def make_template(fs,row,geom,label,preview=False,reference_aperture=None):
    a,o=matrix(row);inv=np.linalg.inv(a)
    local=[{**f,'vertices':[{**v,'p':((np.array(v['p'])-o)@inv.T).tolist()}for v in f['vertices']]}for f in fs]
    native=NativeMesh(label,local,origin=(0,0,0));obj=native.obj
    pts=unique(local);half=max(abs(pts[:,0]));low,high=pts[:,1].min(),pts[:,1].max()
    # The native four inner corners are the narrowest columns of this frame.
    candidates=pts[abs(pts[:,0])<half*.43]
    by,bty=float(candidates[:,1].min()),float(candidates[:,1].max())
    bottom=candidates[abs(candidates[:,1]-by)<.025];top=candidates[abs(candidates[:,1]-bty)<.025]
    corners=np.array([[top[:,0].min(),bty,top[:,2].max()],
                      [top[:,0].max(),bty,top[:,2].max()],
                      [bottom[:,0].max(),by,bottom[:,2].max()],
                      [bottom[:,0].min(),by,bottom[:,2].max()]])
    assert bty-by>1.0 and corners[1,0]-corners[0,0]>.15
    if geom==3 and reference_aperture is not None:
        # Native far LOD omits the inner front rim, but its sill remains in the
        # same place as the close LOD rather than following the rear plane.
        corners[:,2]=np.array(reference_aperture)[:,2]
    if preview:render_asset(obj,HERE/(label+'-before.png'),view=(4,-7,2),resolution=900)
    # Bevel only external edges. Inner opening anchors and connected edges stay exact.
    if geom<3:
        bm=bmesh.new();bm.from_mesh(obj.data);edges=[]
        for e in bm.edges:
            if not e.is_manifold:continue
            inner=False
            for v in e.verts:
                p=np.array(native.world(v.co));inner |= abs(p[0])<half*.45 and by-.04<p[1]<bty+.04
            if not inner and abs(e.calc_face_angle(0))>.22:edges.append(e)
        bmesh.ops.bevel(bm,geom=edges,offset=[.075,.055,.040,0][geom],segments=[3,2,1,1][geom],affect='EDGES',clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
        # Acute lower mitres can make Blender's bevel extend behind/below the
        # original frame. Confine the carved body to its measured native box.
        for v in obj.data.vertices:
            v.co=native.local(np.clip(native.world(v.co),pts.min(axis=0),pts.max(axis=0)))
    vertices=[list(v.co)for v in obj.data.vertices];faces=[list(p.vertices)for p in obj.data.polygons]
    smooth=[False]*len(faces)
    def polygon(points,soft=False):
        start=len(vertices);vertices.extend(list(native.local(p))for p in points)
        faces.append(list(range(start,len(vertices))));smooth.append(soft)
    # A stepped sill remains below the unchanged aperture, within the native
    # outer footprint, with a broad bevel and a downward drip groove.
    width=min(half*.75,max(abs(corners[2:,0]))+.53)
    front=min(float(pts[:,2].max())-.025,float(corners[2,2])+.11)
    cross=[(by-.13,front-.045),(by-.17,front),(by-.29,front),
           (by-.38,front-.075),(by-.38,front-.19),(by-.32,front-.23),
           (by-.32,-.22),(by-.13,-.22)]
    if geom==3:cross=[cross[i]for i in(0,2,4,6)]
    rings=[[[x,y,z]for y,z in cross]for x in(-width,width)]
    polygon(rings[0][::-1]);polygon(rings[1])
    for i in range(len(cross)):
        j=(i+1)%len(cross);polygon([rings[0][i],rings[0][j],rings[1][j],rings[1][i]])
    if geom<2:
        # Rolled rim outside the original aperture. The path never narrows it.
        expanded=corners.copy()
        expanded[:,0]+=np.sign(expanded[:,0])*.10
        expanded[:,1]+=np.array([.10,.10,-.10,-.10])
        expanded[:,2]+=.015
        path=[]
        for i,c in enumerate(expanded):
            path.append(c*.94+expanded[(i-1)%4]*.06)
            path.append(c*.94+expanded[(i+1)%4]*.06)
        radius=.045;sides=6 if geom==0 else 4;rolls=[]
        for i,p in enumerate(path):
            tangent=path[(i+1)%len(path)]-path[(i-1)%len(path)];tangent/=np.linalg.norm(tangent)
            side=np.cross(tangent,[0,0,1]);side/=np.linalg.norm(side)
            rolls.append([p+side*radius*math.cos(2*math.pi*j/sides)+np.array([0,0,radius*math.sin(2*math.pi*j/sides)])for j in range(sides)])
        for i in range(len(path)):
            k=(i+1)%len(path)
            for j in range(sides):
                n=(j+1)%sides;polygon([rolls[i][j],rolls[k][j],rolls[k][n],rolls[i][n]],True)
    if geom==0:
        # Four flush forged retaining heads, clear of the glass opening.
        for sign in(-1,1):
            for y,z in((bty+.62,float(pts[:,2].max())+.002),(by-.66,float(bottom[:,2].max())-.022)):
                centre=np.array([sign*width*.72,y,z]);base=[];cap=[]
                for j in range(8):
                    v=np.array([math.cos(2*math.pi*j/8),math.sin(2*math.pi*j/8),0])
                    base.append(centre+v*.074);cap.append(centre+v*.056+np.array([0,0,.020]))
                polygon(cap)
                for j in range(8):polygon([base[j],base[(j+1)%8],cap[(j+1)%8],cap[j]])
    mesh=bpy.data.meshes.new(label+' sculpted');mesh.from_pydata(vertices,[],faces);mesh.update()
    for m in obj.data.materials:mesh.materials.append(m)
    for p,soft in zip(mesh.polygons,smooth):p.use_smooth=soft
    obj.data=mesh
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000015)
    bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    native.assign_uv();mesh.calc_loop_triangles()
    template={'p':[native.world(v.co)for v in mesh.vertices],
              'faces':[list(p.vertices)for p in mesh.polygons],
              'uv':[[list(mesh.uv_layers.active.data[l].uv)for l in p.loop_indices]for p in mesh.polygons],
              'smooth':[p.use_smooth for p in mesh.polygons], 'aperture':corners.tolist(),
              'triangles':len(mesh.loop_triangles),'bounds_before':[pts.min(axis=0).tolist(),pts.max(axis=0).tolist()]}
    if preview:
        render_asset(obj,HERE/(label+'-after.png'),view=(4,-7,2),resolution=900)
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(label+'.blend')))
    bpy.data.objects.remove(obj,do_unlink=True)
    return template

def create_instance(fs,row,template,label):
    a,o=matrix(row);native=NativeMesh(label,fs)
    points=[native.local(a@np.array(p)+o)for p in template['p']]
    mesh=bpy.data.meshes.new(label);mesh.from_pydata(points,[],template['faces']);mesh.update()
    for m in native.obj.data.materials:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='UVMap')
    for polygon,st,soft in zip(mesh.polygons,template['uv'],template['smooth']):
        polygon.use_smooth=soft
        for loop,coord in zip(polygon.loop_indices,st):uv.data[loop].uv=coord
    native.obj.data=mesh
    remove,add,maximum=native.records(fs)
    for f in remove:f['instance']=row['instance']
    for f in add:
        f['instance']=row['instance']
        for v in f['vertices']:
            weights=np.clip(v['color_weights'],0,1);v['color_weights']=(weights/weights.sum()).tolist()
    bpy.data.objects.remove(native.obj,do_unlink=True)
    return remove,add,maximum

def main():
    reset();reports={}
    for level in ('wascitya','wascityb'):
        source=json.loads((HERE/f'{level}-native.json').read_text());groups=defaultdict(list)
        for f in source['faces']:
            if f['material']==MAT:groups[f['tree'],f['proto'],f['instance'],f['geom']].append(f)
        matrices={(r['tree'],r['instance'],r['geom']):r for r in source['instance_inventory']if r['tree_type']=='tie'}
        templates={};remove=[];add=[];rows=[]
        for (tree,proto,inst,geom),fs in sorted(groups.items()):
            row=matrices[tree,inst,geom];key=(tree,proto,geom)
            if key not in templates:
                reference=templates.get((tree,proto,0),{}).get('aperture')
                templates[key]=make_template(fs,row,geom,f'{level}-frame-{tree}-{proto}-lod{geom}',preview=geom==0,reference_aperture=reference)
            rr,aa,maximum=create_instance(fs,row,templates[key],f'{level}-{tree}-{inst}-lod{geom}')
            remove.extend(rr);add.extend(aa);rows.append({'tree':tree,'proto':proto,'instance':inst,'geom':geom,'removed':len(rr),'added':len(aa),'maximum_surface_distance_m':maximum})
        patch={'level':level,'source_fr3':source['source_fr3'],'preserve_bvh':True,'remove':remove,'add':add}
        path=HERE/f'{level}-patch.json';path.write_text(json.dumps(patch,separators=(',',':')))
        reports[level]={'source_fr3':source['source_fr3'],'patch':str(path),'patch_sha256':sha(path),'removed':len(remove),'added':len(add),'instances':len({(r['tree'],r['instance'])for r in rows}),
                        'triangles_by_lod':dict(Counter({g:sum(r['added']for r in rows if r['geom']==g)for g in range(4)})),
                        'original_glass_envmap_dark_recess_faces_preserved':True,'templates':[{**{'key':list(k)},**v}for k,v in templates.items()],'groups':rows}
        (HERE/'author-report.json').write_text(json.dumps(reports,indent=2)+'\n')
        print(level,len(remove),'removed',len(add),'added',flush=True)
    print('Window patches authored; no native import or deployment',flush=True)
if __name__=='__main__':main()
