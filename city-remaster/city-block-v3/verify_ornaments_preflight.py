"""Verify the staged ornament revision and reject representative scope regressions."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('city_descendants',ROOT/'city-remaster/verify_descendants.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
parser=argparse.ArgumentParser();parser.add_argument('--reanchor',action='store_true');args=parser.parse_args()
candidate_path=HERE/('architecture-ornaments-r2'if args.reanchor else'architecture-ornaments-r1')/'candidate.json'
original_load=v.load;candidate=dict(original_load(candidate_path),status='installed')
overrides={str(candidate_path.resolve()):candidate}
v.load=lambda path:overrides.get(str(Path(path).resolve()))or original_load(path)
checks=[]
def check(ok,message):
    checks.append(bool(ok))
    if not ok:raise AssertionError(message)
def matches(path,expected):check(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,'Hash mismatch: '+str(path))
def verify():
    heads={candidate['path']:candidate['base_sha256']}
    validate=v.architecture_ornaments_reanchor_descendant if args.reanchor else v.architecture_ornaments_descendant
    validate(candidate_path,heads,check,matches,[])
    assert heads[candidate['path']]==candidate['output_sha256']
verify();positive=len(checks)
def reject(path,value):
    key=str(Path(path).resolve());old=overrides.get(key);overrides[key]=value
    try:
        try:verify()
        except AssertionError:return True
        raise RuntimeError('Unexpected mutation accepted')
    finally:
        if old is None:overrides.pop(key)
        else:overrides[key]=old
patch_path=Path(candidate['patch']);patch=original_load(patch_path)
wrong_group=dict(patch,add=[dict(patch['add'][0],group=99999)]+patch['add'][1:])
open_plate=dict(patch,add=patch['add'][1:])
old_parent=dict(candidate,base_sha256='0'*64)
report={'status':'passed','positive_checks':positive,'source_sha256':candidate['base_sha256'],
        'output_sha256':candidate['output_sha256'],'patch_sha256':candidate['patch_sha256'],
        'unknown_group_rejected':reject(patch_path,wrong_group),
        'open_plaque_rejected':reject(patch_path,open_plate),
        'wrong_parent_rejected':reject(candidate_path,old_parent),
        'native_visual_validation':False,'deployed':False}
(HERE/('ornaments-reanchor-proof-preflight.json'if args.reanchor else'ornaments-proof-preflight.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
