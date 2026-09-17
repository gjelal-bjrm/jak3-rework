from pathlib import Path
import re,json,struct
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'engine-src/common/texture/texture_slots.cpp').read_text().split('jak3_slots = {')[1].split('};')[0]
s=re.sub(r'//[^\n]*','',s)
print('Slots:',[(i,t) for i,t in enumerate(re.findall(r'"([^"]+)"',s)) if 'waspala' in t or 'lava-base' in t])
b=(ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/levels/waspala/waspala-background.glb').read_bytes()
n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n])
for i,node in enumerate(j['nodes']):
    if 'anim-slot' in node.get('name',''):
        print('Water node',i,node)
        print('Mesh',j['meshes'][node['mesh']])
        for parent in j['nodes']:
            if i in parent.get('children',[]): print('Parent',parent)
print('Root nodes',[(i,j['nodes'][i].get('name')) for i in j['scenes'][0]['nodes']])
