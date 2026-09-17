"""Curved palm fronds and rounded trunks, retaining original placement and UVs."""
import sys,json,math
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from blender_common import *
data=json.loads((HERE/'native-objects.json').read_text())['faces'];groups=defaultdict(lambda:defaultdict(list))
for f in data:
    if f['tree_type']=='tie' and f['proto'] in (23,26,28):groups[(f['proto'],f['instance'])][f['geom']].append(f)
patch={'description':'Curved palm leaves and rounded trunks authored in Blender','remove':[],'add':[]};report=[]
reset();preview_saved=False
for (proto,instance),targets in groups.items():
    source=targets[0];asset=NativeMesh(('Palm_frond_' if proto==26 else 'Palm_trunk_')+str(instance),source)
    bm=bmesh.new();bm.from_mesh(asset.obj.data);uv=bm.loops.layers.uv.active
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=3 if proto==26 else 2,use_grid_fill=True)
    bm.normal_update()
    if proto==26:
        for vertex in bm.verts:
            if not vertex.link_loops:continue
            st=sum((loop[uv].uv for loop in vertex.link_loops),Vector((0,0)))/len(vertex.link_loops)
            # Blender V is flipped. The frond's attachment is the upper-right UV.
            reach=min(1.0,(st-Vector((1,1))).length*.8)
            curve=.11*reach**1.5*math.sin(st.x*2.1+st.y*1.7)
            vertex.co+=vertex.normal*curve
    else:
        lo=min(v.co.z for v in bm.verts);hi=max(v.co.z for v in bm.verts)
        movable=[v for v in bm.verts if lo+.04*(hi-lo)<v.co.z<hi-.04*(hi-lo)]
        for _ in range(4):bmesh.ops.smooth_vert(bm,verts=movable,factor=.42,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update();bm.to_mesh(asset.obj.data);bm.free()
    for polygon in asset.obj.data.polygons:polygon.use_smooth=True
    asset.obj.data.update()
    counts={};max_distance=0
    for lod,faces in targets.items():
        remove,add,distance=asset.records(faces);patch['remove'].extend(remove);patch['add'].extend(add)
        counts[lod]={'original':len(faces),'new':len(add)};max_distance=max(max_distance,distance)
    report.append({'proto':proto,'instance':instance,'counts':counts,'max_surface_distance_m':max_distance})
    if proto==26 and not preview_saved:
        save_asset(asset.obj,'palm-frond-remodel');preview_saved=True
    bpy.data.objects.remove(asset.obj,do_unlink=True)
    if len(report)%50==0:print('Authored',len(report),'palm surfaces',flush=True)
(HERE/'foliage-patch.json').write_text(json.dumps(patch,separators=(',',':')))
(HERE/'foliage-report.json').write_text(json.dumps(report,indent=2))
print('Saved',len(report),'palm surfaces',len(patch['remove']),'->',len(patch['add']),flush=True)
