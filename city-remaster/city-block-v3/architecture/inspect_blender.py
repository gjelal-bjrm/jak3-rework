from pathlib import Path
import bpy,sys,json
R=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'models-v1'))
from blender_common import NativeMesh,reset,render_asset
p=json.loads((R/'city-remaster/environment/architecture/wascitya-native.json').read_text())
for k in (1,2):
 reset();fs=[f for f in p['faces'] if f['geom']==0 and f['tree']==1 and f['instance']==k];n=NativeMesh('native-building-'+str(k),fs)
 render_asset(n.obj,H/('building-'+str(k)+'-source.png'),view=(-6,-7,3),resolution=1000)
 bpy.ops.wm.save_as_mainfile(filepath=str(H/('building-'+str(k)+'-source.blend')))
