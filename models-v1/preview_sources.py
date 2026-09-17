import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from blender_common import *
data=json.loads((HERE/'native-objects.json').read_text())['faces']
tests={
 'brazier-source':lambda f:f['tree_type']=='tie' and f['proto']==11 and all(abs(v['p'][0]-2017.75)<2 and abs(v['p'][2]+427.60)<2 for v in f['vertices']),
 'planter-source':lambda f:f['tree_type']=='tie' and f['proto']==27 and all(abs(v['p'][0]-2014.99)<2 and abs(v['p'][2]+420.19)<2 for v in f['vertices']),
 'throne-source':lambda f:f['material'].startswith('waspala-throne') and f['material']!='waspala-throne-floor',
}
for name,select in tests.items():
    reset();faces=[f for f in data if f['geom']==0 and select(f)];asset=NativeMesh(name,faces)
    render_asset(asset.obj,HERE/(name+'.png'),view=(3,7,3) if name.startswith('throne') else (4,-7,3))
    print(name,len(faces),list(asset.origin))
