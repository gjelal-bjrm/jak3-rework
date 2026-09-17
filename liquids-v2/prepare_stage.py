from pathlib import Path
import json
import hashlib
import shutil
ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT.parents[1] / 'active/jak3/data'
extras = ['out/jak3/fr3/game.fr3', 'out/jak3/fr3/waspala.fr3', 'out/jak3/iso/WASPALA.DGO']
files = json.loads((ROOT / 'variant-files.json').read_text())
for relative in extras:
    assert relative not in files
    files.append(relative)
    for variant in ('original', 'remaster', 'remaster-v1'):
        dest = ROOT / 'variants' / variant / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ACTIVE / relative, dest)
for scene in ('arena', 'palace'):
    (ROOT / 'routes' / scene).mkdir(parents=True, exist_ok=True)
if not (ROOT / 'routes/arena/GAME.CGO').exists():
    shutil.copy2(ROOT / 'data/out/jak3/iso/GAME.CGO', ROOT / 'routes/arena/GAME.CGO')
hashes = {v: {f: hashlib.sha256((ROOT/'variants'/v/f).read_bytes()).hexdigest() for f in files}
          for v in ('original','remaster','remaster-v1')}
(ROOT/'variant-files.json').write_text(json.dumps(files,indent=2))
(ROOT/'variant-hashes.json').write_text(json.dumps(hashes,indent=2))
print(f'{len(files)} A/B files; V1 snapshot retained')
