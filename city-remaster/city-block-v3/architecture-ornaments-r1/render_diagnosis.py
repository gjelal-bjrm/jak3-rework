from pathlib import Path
import json,sys,bpy
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'models-v1'));from blender_common import NativeMesh,reset,render_asset
for name,path in [('geometry002',H.parent/'architecture/block-native.json'),('installed',H/'native.json')]:
 s=json.loads(path.read_text());fs=[f for f in s['faces'] if f['geom']==0 and f['tree_type']=='tie' and (f['tree']==1 and f['group']==2 and ('stucco' in f['material'] or 'stonewall' in f['material']) or f['tree']==0 and f['draw'] in (40,41) and f['group'] in (4,5,6,7,9,10))]
 reset();n=NativeMesh(name,fs);render_asset(n.obj,H/(name+'-ornaments.png'),view=(-6,-7,3),resolution=1400)
