"""Blender remodel of native Spargus plaster shells and thick weathered coping.

Geometry is imported from the current native export, shaped in Blender, and
returned with native UVs, visibility groups and all eight lighting palettes.
This author never writes game data. Doors, foundations and separate actors are
not selected. Coping is constructed from actual upward wall boundaries.
"""
from pathlib import Path
from collections import defaultdict, Counter
import sys,json,math,hashlib,argparse
import bpy,bmesh
from mathutils import Vector
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parent
sys.path.insert(0,str(ROOT/'models-v1'))
from blender_common import NativeMesh,reset,render_asset

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')
def pointkey(p):return tuple(round(float(x),3) for x in p)
def wallmat(name):return ('stucco-wall-bleached' in name or name in ('wascity-stonewall-bricks','wascity-stonewall-bricks-HI'))

def use_hd_materials(native):
    for mat in native.obj.data.materials:
        source=HERE.parent/'masters'/(mat.name+'.png')
        if not source.exists():continue
        image=bpy.data.images.load(str(source),check_existing=True)
        image.pack()
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE':node.image=image

def top_edges(faces):
    """Top contour where a vertical exterior meets a roof, not every mesh edge."""
    edges=defaultdict(list)
    for f in faces:
        p=[Vector(v['p']) for v in f['vertices']]
        n=(p[1]-p[0]).cross(p[2]-p[0])
        if n.length<1e-8:continue
        n.normalize()
        for i in range(3):
            a,b=p[i],p[(i+1)%3];third=p[(i+2)%3]
            edges[tuple(sorted((pointkey(a),pointkey(b))))].append((a,b,third,n,f))
    selected=[]
    for entries in edges.values():
        for a,b,c,n,f in entries:
            d=b-a
            if abs(n.y)>.35 or d.length<1.1 or abs(d.y)>.10*d.length:continue
            if min(a.y,b.y)-c.y<.48:continue
            others=[e for e in entries if e[4] is not f]
            # A seam within a continuous wall is not a rooftop boundary.
            if others and not any(e[3].y>.50 for e in others):continue
            if 'bricks' in f['material'] or 'cut' in f['material']:continue
            flat=Vector((n.x,0,n.z)).normalized()
            selected.append((a,b,flat,f))
            break
    return selected

def coping(native,edges,lod):
    """Continuous rounded adobe rim with irregular wear and no tiled blocks."""
    if not edges:return 0
    mesh=native.obj.data
    vs=[v.co.copy() for v in mesh.vertices];polys=[list(p.vertices) for p in mesh.polygons]
    shell_face_count=len(polys)
    mats=[p.material_index for p in mesh.polygons]
    uvs=[[tuple(mesh.uv_layers.active.data[li].uv) for li in p.loop_indices] for p in mesh.polygons]
    # Join neighbouring strips with the same offset at the shared endpoint.
    normals=defaultdict(list)
    for a,b,n,face in edges:
        normals[pointkey(a)].append(n);normals[pointkey(b)].append(n)
    def joint(p,n):
        ns=normals[pointkey(p)];v=sum(ns,Vector())
        if v.length<.01:return n
        v.normalize();return v/max(.55,v.dot(n))
    profile=[(-.055,-.40),(.055,-.40),(.16,-.34),(.225,-.22),(.215,-.10),(.12,.015),(-.055,.025)]
    if lod==2:profile=[profile[i] for i in (0,1,3,5,6)]
    if lod==3:profile=[profile[i] for i in (0,1,3,6)]
    for a,b,n,face in edges:
        mat=face['material']
        fp=[Vector(v['p']) for v in face['vertices']];fu=fp[1]-fp[0];fv=fp[2]-fp[0]
        aa=fu.dot(fu);ab=fu.dot(fv);bb=fv.dot(fv);den=aa*bb-ab*ab
        def project_uv(index):
            q=Vector(native.world(vs[index]))-fp[0];wa=q.dot(fu);wb=q.dot(fv)
            b=(bb*wa-ab*wb)/den;c=(aa*wb-ab*wa)/den;weights=(1-b-c,b,c)
            st=[sum(weights[i]*face['vertices'][i]['uv'][axis] for i in range(3)) for axis in range(2)]
            return (st[0],1-st[1])
        count=max(1,math.ceil((b-a).length/[.75,1.15,2.0,4.0][lod]));rings=[]
        na,nb=joint(a,n),joint(b,n)
        for i in range(count+1):
            t=i/count;p=a.lerp(b,t);normal=na.lerp(nb,t)
            wear=.012*math.sin(p.x*2.41+p.z*.79)+.008*math.sin(p.z*5.37-p.x*.68)
            ring=[]
            for depth,height in profile:
                q=p+normal*(depth+wear)+Vector((0,height+wear*.6,0))
                ring.append(len(vs));vs.append(native.local(q))
            rings.append(ring)
        for i in range(count):
            for j in range(len(profile)):
                k=(j+1)%len(profile)
                polys.append([rings[i][j],rings[i+1][j],rings[i+1][k],rings[i][k]])
                mats.append(native.materials.index(mat))
                uvs.append([project_uv(index) for index in polys[-1]])
        for ring in (rings[0],list(reversed(rings[-1]))):
            polys.append(ring);mats.append(native.materials.index(mat));uvs.append([project_uv(index) for index in ring])
    out=bpy.data.meshes.new(mesh.name+' with sculpted coping');out.from_pydata(vs,[],polys)
    for mat in mesh.materials:out.materials.append(mat)
    layer=out.uv_layers.new(name='UVMap')
    for p,m,uv in zip(out.polygons,mats,uvs):
        p.material_index=m
        for li,st in zip(p.loop_indices,uv):layer.data[li].uv=st
    out.update();native.obj.data=out
    bm=bmesh.new();bm.from_mesh(out)
    bm.faces.ensure_lookup_table();new_faces=list(bm.faces)[shell_face_count:]
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00008)
    # The imported building is an OPEN shell. Reorienting the entire mesh by
    # enclosed volume flips large native walls. Only the new closed coping
    # strips need an outward solve; inherited wall winding stays untouched.
    bmesh.ops.recalc_face_normals(bm,faces=[f for f in new_faces if f.is_valid])
    bm.normal_update();bm.to_mesh(out);bm.free();out.update()
    return len(edges)

def remodel(native,lod):
    # Native city walls are open, overlapping panels with separate junctions.
    # Insetting their construction edges exposes dark seams in the game even
    # when the exported triangle winding is valid. Keep the continuous native
    # shell and author the raised, rounded coping as a separate closed volume.
    caps=coping(native,top_edges(native.faces),lod)
    for p in native.obj.data.polygons:p.use_smooth=False
    return 0,caps


def rejected_inset_bevel(native,lod):
    mesh=native.obj.data
    bm=bmesh.new();bm.from_mesh(mesh)
    # Keep original diagonals and their UV tile seams intact. The angle filter
    # selects construction edges only; dissolving tile seams stretches atlases.
    bm.normal_update()
    edges=[e for e in bm.edges if e.is_manifold and e.calc_length()>.4 and .35<e.calc_face_angle()<2.85]
    count=len(edges)
    if edges:
        bmesh.ops.bevel(bm,geom=edges,offset=[.28,.28,.23,.16][lod],segments=[4,3,2,1][lod],
                        affect='EDGES',profile=.62,clamp_overlap=True,loop_slide=True)
    # Small concave corner miters may triangulate backwards along the original
    # wall even though the enclosing bevel polygon has a valid average normal.
    # Orient those triangles against the actual source surface before adding
    # the separate coping volume. Existing two-sided coincident faces keep
    # their own orientation.
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
    for face in bm.faces:
        centre=face.calc_center_median();near= native.bvh.find_nearest(centre)
        if near[2] is None or near[3]>.025 or face.normal.dot(near[1])>-.95:continue
        if not all(native.bvh.find_nearest(v.co)[3]<.025 for v in face.verts):continue
        alternatives=native.bvh.find_nearest_range(centre,near[3]+.001)
        if any(face.normal.dot(n)>.9 for p,n,i,d in alternatives):continue
        face.normal_flip()
    bm.normal_update();bm.to_mesh(mesh);bm.free();mesh.update()
    caps=coping(native,top_edges(native.faces),lod)
    # Split normals on truly hard edges. Native in-game normals remain per
    # vertex; these Blender faces use flat small bevel segments to retain the
    # hand-built sculpted planes without rounding whole planar walls.
    for p in native.obj.data.polygons:p.use_smooth=False
    return count,caps

def remove_collapsed(records):
    # Blender bevel intersections can produce zero-area slivers, especially
    # after rounding large native world coordinates to float32. They have no
    # visible surface and must not be passed to the native normal generator.
    valid=[]
    for face in records:
        a,b,c=[Vector(v['p']) for v in face['vertices']]
        normal=(b-a).cross(c-a)
        if normal.length<2e-10:continue
        normal.normalize()
        for v in face['vertices']:v['normal']=list(normal)
        valid.append(face)
    return valid,len(records)-len(valid)

def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('--level',choices=['wascitya','wascityb'],required=True)
    parser.add_argument('--sample',action='store_true');a=parser.parse_args(args)
    export=HERE.parent/'architecture'/(a.level+'-native.json');source=read(export);reset()
    groups=defaultdict(lambda:defaultdict(list))
    for f in source['faces']:
        if wallmat(f['material']):groups[(f['tree'],f['proto'],f['instance'])][f['geom']].append(f)
    patch={'level':a.level,'source_fr3':source['source_fr3'],'preserve_bvh':True,'remove':[],'add':[]}
    report={'level':a.level,'source_export':str(export),'source_export_sha256':sha(export),'source_fr3':source['source_fr3'],
            'author_sha256':sha(__file__),'instances':[],'scope':'Continuous native plaster shells with new thick rounded roof coping; native shapes, UV palette and doors retained',
            'native_game_validation':False}
    previews={(0,39,2894),(1,0,1)} if a.level=='wascitya' else {(0,15,1615),(0,43,2471)}
    made=[]
    for key,lods in groups.items():
        if a.sample and key not in previews:continue
        entry={'tree':key[0],'proto':key[1],'instance':key[2],'lods':[]}
        for lod,faces in sorted(lods.items()):
            if a.sample and lod:continue
            native=NativeMesh(f'{a.level}_plaster_{key[0]}_{key[2]}_LOD{lod}',faces);use_hd_materials(native)
            if key in previews and lod==0:render_asset(native.obj,HERE/f'{a.level}-{key[2]}-before.png',resolution=900)
            bevels,caps=remodel(native,lod)
            remove,add,deviation=native.records(faces)
            add,collapsed=remove_collapsed(add)
            patch['remove'].extend(remove);patch['add'].extend(add)
            entry['lods'].append({'lod':lod,'removed':len(remove),'added':len(add),'beveled_edges':bevels,'coping_edges':caps,'max_distance_m':deviation,'zero_area_slivers_removed':collapsed})
            if key in previews and lod==0:render_asset(native.obj,HERE/f'{a.level}-{key[2]}-authored.png',resolution=900)
            # Keep complete LOD0 in the editable Blender project. Lower LODs
            # are generated from their own native mesh and exported separately.
            native.obj.location=(native.origin.x,-native.origin.z,native.origin.y)
            native.obj.hide_render=lod!=0;native.obj.hide_set(lod!=0)
            if lod: bpy.data.objects.remove(native.obj,do_unlink=True)
            else: made.append(native.obj)
        report['instances'].append(entry)
        print(json.dumps({'instance':key,'processed':len(report['instances']),'total':len(groups),'last':entry['lods'][-1]}),flush=True)
    prefix=a.level+('-sample' if a.sample else '')
    for obj in made:obj.hide_render=False;obj.hide_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(prefix+'-architecture.blend')))
    pp=HERE/(prefix+'-patch.json');pp.write_text(json.dumps(patch,separators=(',',':')))
    report.update(patch=str(pp),patch_sha256=sha(pp),removed=len(patch['remove']),added=len(patch['add']))
    write(HERE/(prefix+'-author-report.json'),report)
    print(json.dumps({'status':'authored_not_installed','instances':len(report['instances']),'removed':report['removed'],'added':report['added']}),flush=True)

if __name__=='__main__':main()
