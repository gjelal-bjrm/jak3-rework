import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from blender_common import *
faces=[f for f in json.loads((HERE/'native-brazier-roundtrip.json').read_text())['faces'] if f['tree_type']=='tie' and f['proto']==11]
reset();asset=NativeMesh('Native roundtrip brazier',faces)
print('NATIVE',len(faces),flush=True)
render_asset(asset.obj,HERE/'brazier-native-roundtrip.png')
