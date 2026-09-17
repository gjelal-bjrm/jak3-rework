"""Register scoped fruit/cloud shaders; official comparison engines ignore them.

This registers source/data and comparison baselines. Root's normal package step
copies the active remaster shaders and records its final hashes afterward.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
parser=argparse.ArgumentParser();parser.add_argument('--clouds-only',action='store_true');args=parser.parse_args()
files=json.loads((ROOT/'variant-files.json').read_text());hashes=json.loads((ROOT/'variant-hashes.json').read_text())
names=['spargus_clouds.vert','spargus_clouds.frag']
if not args.clouds_only:names=['market_fruit.vert','market_fruit.frag']+names
for name in names:
    rel='game/graphics/opengl_renderer/shaders/'+name
    for tree in ['data','engine-src']:
        dest=ROOT/tree/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/name,dest)
    if rel not in files:files.append(rel)
    for variant in ['original','remaster-v1']:
        dest=ROOT/'variants'/variant/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(HERE/name,dest)
        hashes[variant][rel]=hashlib.sha256(dest.read_bytes()).hexdigest()
(ROOT/'variant-files.json').write_text(json.dumps(files,indent=2))
(ROOT/'variant-hashes.json').write_text(json.dumps(hashes,indent=2))
print('Registered scoped shaders: '+', '.join(names))
