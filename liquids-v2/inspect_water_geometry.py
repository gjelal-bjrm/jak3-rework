from pathlib import Path
import json,struct
ROOT=Path(__file__).resolve().parents[1]
raw=(ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/levels/waspala/waspala-background.glb').read_bytes()
n=struct.unpack_from('<I',raw,12)[0]
j=json.loads(raw[20:20+n]); base=20+n+8
def accessor(index):
    a=j['accessors'][index];v=j['bufferViews'][a['bufferView']]
    fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    fmt='<'+fmt*width;stride=v.get('byteStride',struct.calcsize(fmt))
    offset=base+v.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from(fmt,raw,offset+i*stride) for i in range(a['count'])]
for node in j['nodes']:
    if 'anim-slot' not in node.get('name',''):continue
    for p in j['meshes'][node['mesh']]['primitives']:
        pos=accessor(p['attributes']['POSITION']);idx=accessor(p['indices'])
        pts=[pos[i[0]] for i in idx]
        print(node['name'],'bounds',[(min(v[c] for v in pts),max(v[c] for v in pts)) for c in range(3)],'ys',sorted(set(round(v[1],3) for v in pts))[:40])
