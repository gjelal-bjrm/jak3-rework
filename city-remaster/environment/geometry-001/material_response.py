"""Opt the new cactus skin into the existing regional foliage light response."""
from pathlib import Path
import argparse,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
RELATIVE='engine-src/game/graphics/opengl_renderer/background/PalaceMaterials.h'
OLD='    if (name=="market-palm-leaf-v1" || name=="market-shrub-orange-v1") return 5;'
NEW='    if (name=="market-palm-leaf-v1" || name=="market-shrub-orange-v1" ||\n        name=="city-cactus-green-v2") return 5;'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_before():
    j=json.loads((HERE/'material-response.json').read_text());target=ROOT/RELATIVE;before=Path(j['before_path'])
    assert sha(target)==j['after_sha256'] and sha(before)==j['before_sha256']
    source=target.read_text();assert source.count(NEW)==1
    assert source.replace(NEW,OLD,1)==before.read_text()
    return before
def apply():
    record=HERE/'material-response.json'
    if record.exists():source_before();return
    target=ROOT/RELATIVE;before=HERE/'PalaceMaterials-before-cactus.h';raw=target.read_bytes();source=target.read_text()
    assert source.count(OLD)==1 and NEW not in source
    before.write_bytes(raw);newline='\r\n' if b'\r\n' in raw else '\n'
    target.write_bytes(source.replace(OLD,NEW,1).replace('\n',newline).encode())
    record.write_text(json.dumps({'relative':RELATIVE,'before_path':str(before),'before_sha256':sha(before),'after_sha256':sha(target),
       'scope':'Only city-cactus-green-v2 uses foliage light/filter response; no foliage motion or grass contact added to cactus'},indent=2)+'\n')
    source_before()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
    if args.apply:apply()
    else:print(source_before())
