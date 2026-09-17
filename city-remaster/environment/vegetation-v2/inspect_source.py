from pathlib import Path
import json,sys
import bpy
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'models-v1'))
from blender_common import NativeMesh,reset,render_asset
d=json.loads((HERE/'wascitya-native.json').read_text());reset()
inv={i['instance']:i for i in d['instance_inventory']}
for instance,label in ((3266,'cactus'),(2302,'grass')):
    fs=[f for f in d['faces']if f['instance']==instance]
    i=inv[instance];asset=NativeMesh(label,fs,i['origin_m'])
    for loop in asset.obj.data.uv_layers.active.data:loop.uv=(loop.uv.x/4096,1-(1-loop.uv.y)/4096)
    render_asset(asset.obj,HERE/(label+'-source.png'),resolution=1000)
    cols=i['matrix_columns'];m=Matrix([[cols[c][r]for c in range(3)]+[i['origin_m'][r]]for r in range(3)]+[[0,0,0,1]])
    pts=[list(m.inverted()@Vector(v['p'])) for f in fs for v in f['vertices']]
    (HERE/(label+'-source-local.json')).write_text(json.dumps({'instance':i,'faces':[{**{k:f[k]for k in ('material','draw','proto')},'vertices':[{**v,'local':list(m.inverted()@Vector(v['p']))}for v in f['vertices']]}for f in fs]},indent=2))
    print(label,'bounds',[[min(p[a]for p in pts)for a in range(3)],[max(p[a]for p in pts)for a in range(3)]],flush=True)
