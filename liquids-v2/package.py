"""Snapshot the built V2; never reset the original or V1 comparison files."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--route',choices=('arena','palace'))
args=parser.parse_args()
files=json.loads((ROOT/'variant-files.json').read_text())
hashes=json.loads((ROOT/'variant-hashes.json').read_text())
for relative in files:
    target=ROOT/'variants/remaster'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'data'/relative,target)
    hashes['remaster'][relative]=hashlib.sha256(target.read_bytes()).hexdigest()
(ROOT/'variant-hashes.json').write_text(json.dumps(hashes,indent=2))
# A shader-only iteration must never overwrite a route with the last played scene.
if args.route:
    shutil.copy2(ROOT/'data/out/jak3/iso/GAME.CGO',ROOT/'routes'/args.route/'GAME.CGO')
print(f'V2 packaged: {len(files)} files; original and V1 snapshots preserved')
