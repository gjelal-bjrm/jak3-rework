from pathlib import Path
import json,sys,bpy
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'models-v1'));from blender_common import NativeMesh,reset,render_asset
s=json.loads((H/'native.json').read_text());p=json.loads((H/'wascitya-patch.json').read_text())
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','stream_index'))
removed={key(f) for f in p['remove']};lookup={(f['geom'],f['tree'],f['draw'],f['group']):f for f in s['faces']}
fs=[f for f in s['faces'] if f['geom']==0 and f['tree_type']=='tie' and key(f) not in removed and (f['tree']==1 and f['group']==2 and ('stucco' in f['material'] or 'stonewall' in f['material']) or f['tree']==0 and f['draw'] in(40,41) and f['group'] in(4,5,6,7,9,10))]
for f in p['add']:
 if f['geom']!=0:continue
 t=lookup[f['geom'],f['tree'],f['draw'],f['group']];fs.append({**f,'material':t['material'],'page':t['page']})
reset();n=NativeMesh('House2 closed pointed metal plaques',fs);render_asset(n.obj,H/'revised-ornaments.png',view=(-6,-7,3),resolution=1400)
