"""Fit fire to the indexed coal bowl, including its recessed centre and tilted rim."""
from pathlib import Path
import struct,json,math
ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/levels/waspala/waspala-background.glb'
raw=source.read_bytes();size=struct.unpack_from('<I',raw,12)[0]
doc=json.loads(raw[20:20+size]);base=28+size
coal=set();triangles=[]
for mesh in doc['meshes']:
    for p in mesh['primitives']:
        if doc['materials'][p['material']].get('name')!='waspala-fire-coal':continue
        a=doc['accessors'][p['attributes']['POSITION']];b=doc['bufferViews'][a['bufferView']]
        offset=base+b.get('byteOffset',0)+a.get('byteOffset',0)
        indices=doc['accessors'][p['indices']];view=doc['bufferViews'][indices['bufferView']]
        io=base+view.get('byteOffset',0)+indices.get('byteOffset',0)
        kind={5125:'I',5123:'H',5121:'B'}[indices['componentType']]
        stride=view.get('byteStride',struct.calcsize('<'+kind))
        vertices=[]
        for k in range(indices['count']):
            index=struct.unpack_from('<'+kind,raw,io+k*stride)[0]
            vertex=struct.unpack_from('<3f',raw,offset+index*b.get('byteStride',12))
            coal.add(vertex);vertices.append(vertex)
        triangles.extend(tuple(vertices[k:k+3]) for k in range(0,len(vertices),3))
actors=json.loads((ROOT/'desert-remaster/palace-fire.json').read_text())['actors']
fits=[]
for actor in actors:
    x,y,z,_=actor['trans_m']
    points=[p for p in coal if abs(p[1]-y)<2.5 and (p[0]-x)**2+(p[2]-z)**2<3.2**2]
    # Coal faces belong to standing crucibles. Wall/hanging holders have no coal mesh.
    has_coal=actor['group']=='group-waspala-crucible-fire'
    if has_coal:
        assert len(points)>=3,actor['aid']
        top=max(p[1] for p in points)
        radius=max(math.hypot(p[0]-x,p[2]-z) for p in points)*.78
    else:
        top=y+.035
        radius=1.0 if actor['group']=='group-waspala-wallfire' else 1.5
    anchor=top+.015
    planes=[]
    if has_coal:
        local=[(p[0]-x,p[1]-anchor,p[2]-z) for p in points]
        for triangle in triangles:
            if not all(p in points for p in triangle):continue
            a,b,c=[(p[0]-x,p[1]-anchor,p[2]-z) for p in triangle]
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            assert abs(normal[1])>1e-6,actor['aid']
            sx,sz=-normal[0]/normal[1],-normal[2]/normal[1]
            plane=(sx,sz,a[1]-sx*a[0]-sz*a[2])
            if not any(max(abs(plane[i]-q[i]) for i in range(3))<1e-5 for q in planes):
                planes.append(plane)
        assert len(planes)==8,(actor['aid'],len(planes))
        # The eight faces form a convex height field. Its maximum plane must
        # reproduce both the centre and every rim vertex, not a floating disc.
        error=max(abs(max(a*p[0]+b*p[2]+c for a,b,c in planes)-p[1]) for p in local)
        assert error<.0001,(actor['aid'],error)
        floor=min(p[1] for p in local)-.025
    else:
        planes=[(0.0,0.0,0.0)]*8;floor=0.0;error=0.0
    fits.append({'aid':actor['aid'],'actor_y':y,'fuel_y':anchor,'fuel_radius':radius,
                 'coal_vertices':len(points),'y_offset':top+.015-y,
                 'fuel_floor':floor,'fuel_planes':planes,'surface_max_error_m':error,
                 'method':'indexed coal bowl surface' if has_coal else 'conservative actor opening'})
out=ROOT/'fire-v1/source-fit.json'
out.write_text(json.dumps({'source':str(source),'fits':fits},indent=2))
print(f'Fitted {len(fits)} sources; {sum(f["coal_vertices"]==9 for f in fits)} indexed coal bowls; maximum surface error {max(f["surface_max_error_m"] for f in fits):.8f} m')
