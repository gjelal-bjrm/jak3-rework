"""Distance to real rock/wall cross sections at each palace basin water level."""
from pathlib import Path
from array import array
import json, struct, math, time
ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/levels/waspala/waspala-background.glb'
raw=source.read_bytes(); size=struct.unpack_from('<I',raw,12)[0]
doc=json.loads(raw[20:20+size]); base=28+size
cache={}
def access(i):
    if i in cache:return cache[i]
    a=doc['accessors'][i]; b=doc['bufferViews'][a['bufferView']]
    kind={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    fmt='<'+kind*width; stride=b.get('byteStride',struct.calcsize(fmt))
    offset=base+b.get('byteOffset',0)+a.get('byteOffset',0)
    result=[struct.unpack_from(fmt,raw,offset+k*stride) for k in range(a['count'])]
    cache[i]=result
    return result
levels=[240.629257,241.491302,242.372253,243.497742]
segments=[[] for _ in levels]
materials={}
for node in doc['nodes']:
    if 'mesh' not in node or 'anim-slot' in node.get('name',''):continue
    for primitive in doc['meshes'][node['mesh']]['primitives']:
        material=doc['materials'][primitive.get('material',0)].get('name','')
        # Solid bank materials only; exclude water, foliage, glass and fake mist.
        if not any(key in material for key in ('rock','pool-floor','step','column','stage','fountain-base')):continue
        if 'lowres' in material:continue
        vertices=access(primitive['attributes']['POSITION']);indices=access(primitive['indices'])
        for i in range(0,len(indices)-2,3):
            tri=[vertices[indices[i+k][0]] for k in range(3)]
            for layer,level in enumerate(levels):
                if not min(v[1] for v in tri)<level<max(v[1] for v in tri):continue
                hits=[]
                for k in range(3):
                    a,b=tri[k],tri[(k+1)%3]
                    if (a[1]-level)*(b[1]-level)<0:
                        t=(level-a[1])/(b[1]-a[1])
                        hits.append((a[0]+(b[0]-a[0])*t,a[2]+(b[2]-a[2])*t))
                if len(hits)==2:
                    segments[layer].append(hits)
                    materials[material]=materials.get(material,0)+1
N=1024; origin=(1944.0,-524.0); step=128.0/N; radius=1.5
out=ROOT/'data/game/graphics/opengl_renderer/shaders/palace-shore.bin'
started=time.time()
with out.open('wb') as f:
    f.write(struct.pack('<4I',0x53484F52,N,N,len(levels)))
    for layer,lines in enumerate(segments):
        field=array('f',[radius*radius])*(N*N)
        for a,b in lines:
            vx,vz=b[0]-a[0],b[1]-a[1];length=vx*vx+vz*vz
            if length<1e-10:continue
            bounds=[]
            for c in range(2):
                lo=max(0,math.floor((min(a[c],b[c])-radius-origin[c])/step))
                hi=min(N-1,math.ceil((max(a[c],b[c])+radius-origin[c])/step))
                bounds.append((lo,hi))
            for iz in range(bounds[1][0],bounds[1][1]+1):
                z=origin[1]+(iz+0.5)*step;dz=z-a[1];row=iz*N
                for ix in range(bounds[0][0],bounds[0][1]+1):
                    x=origin[0]+(ix+0.5)*step;dx=x-a[0]
                    t=max(0.0,min(1.0,(dx*vx+dz*vz)/length))
                    d2=(dx-t*vx)**2+(dz-t*vz)**2
                    if d2<field[row+ix]:field[row+ix]=d2
        field=array('f',(math.sqrt(d2) for d2 in field));field.tofile(f)
        print('Shore layer',levels[layer],len(lines),'segments',flush=True)
report={'source':str(source),'resolution':[N,N],'bounds':[origin,[origin[0]+128,origin[1]+128]],
        'water_levels':levels,'segments_per_level':[len(s) for s in segments],
        'materials':materials,'seconds':time.time()-started}
(ROOT/'shore-v4/geometry-report.json').write_text(json.dumps(report,indent=2))
print('Built',out,'in',round(time.time()-started,2),'seconds')
