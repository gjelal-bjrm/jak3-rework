"""Read-only R3 preflight, with mutations of scope and retained window anchors."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('city_descendants',ROOT/'city-remaster/verify_descendants.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
candidate_path=HERE/'architecture-single-window-r3/candidate.json'
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
    v.architecture_single_window_descendant(candidate_path,heads,check,matches,[])
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
wrong_group=dict(patch,add=[dict(patch['add'][0],group=2)]+patch['add'][1:])
anchors_path=Path(candidate['window_anchors']);anchors=original_load(anchors_path)
shifted=json.loads(json.dumps(anchors));shifted[0]['center'][0]+=.1
historical=original_load(HERE/'architecture/window-anchors.json')
report={'status':'passed','positive_checks':positive,'source_sha256':candidate['base_sha256'],
        'output_sha256':candidate['output_sha256'],'patch_sha256':candidate['patch_sha256'],
        'unknown_group_rejected':reject(patch_path,wrong_group),
        'changed_retained_anchor_rejected':reject(anchors_path,shifted),
        'restored_duplicate_room_rejected':reject(anchors_path,historical),
        'wrong_parent_rejected':reject(candidate_path,dict(candidate,base_sha256='0'*64)),
        'native_visual_validation':False,'deployed':False}
(HERE/'single-window-proof-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
