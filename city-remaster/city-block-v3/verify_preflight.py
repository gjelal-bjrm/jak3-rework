"""Read-only package preflight; staged architecture is installed only in memory."""
from pathlib import Path
import hashlib, importlib.util, json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('city_descendants',ROOT/'city-remaster/verify_descendants.py')
desc=importlib.util.module_from_spec(spec);spec.loader.exec_module(desc)
original_load=desc.load
candidate_path=HERE/'architecture/candidate.json'
candidate=original_load(candidate_path)
candidate=dict(candidate,status='installed')
overrides={str(candidate_path.resolve()):candidate}
desc.load=lambda path:overrides.get(str(Path(path).resolve()),None) or original_load(path)
checks=[]

def check(ok,message):
    checks.append((bool(ok),message))
    if not ok:raise AssertionError(message)

def matches(path,expected):
    check(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,'Hash mismatch: '+str(path))

def architecture():
    heads={candidate['path']:candidate['base_sha256']}
    desc.architecture_descendant(candidate_path,heads,check,matches,[])
    assert heads[candidate['path']]==candidate['output_sha256']

architecture();architecture_checks=len(checks)
assets,_=desc.verify_city_interiors(check,matches)
interior_checks=len(checks)-architecture_checks

def rejects(path,value,call):
    key=str(Path(path).resolve());prior=overrides.get(key)
    overrides[key]=value
    try:
        try:call()
        except AssertionError:return True
        raise AssertionError('Out-of-scope mutation unexpectedly accepted')
    finally:
        if prior is None:overrides.pop(key)
        else:overrides[key]=prior

patch_path=Path(candidate['patch']);patch=original_load(patch_path)
wrong_scope=dict(patch,add=[dict(patch['add'][0],group=999999)]+patch['add'][1:])
scope_rejected=rejects(patch_path,wrong_scope,architecture)
bvh_rejected=rejects(patch_path,dict(patch,preserve_bvh=False),architecture)
parent_rejected=rejects(candidate_path,dict(candidate,base_sha256='0'*64),architecture)
manifest_path=HERE/'interiors/asset-manifest.json';manifest=original_load(manifest_path)
rogue=dict(manifest,assets=dict(manifest['assets'],**{'custom_assets/jak3/city-interiors/rogue.bin':'0'*64}))
asset_rejected=rejects(manifest_path,rogue,lambda:desc.verify_city_interiors(check,matches))
result={'status':'passed','architecture_checks':architecture_checks,
        'architecture_source_sha256':candidate['base_sha256'],
        'architecture_output_sha256':candidate['output_sha256'],
        'architecture_patch_sha256':candidate['patch_sha256'],
        'interiors_source_and_asset_checks':interior_checks,'exact_runtime_files':len(assets),
        'unexpected_geometry_group_rejected':scope_rejected,'bvh_expansion_rejected':bvh_rejected,
        'wrong_architecture_parent_rejected':parent_rejected,'unknown_asset_rejected':asset_rejected,
        'writes_to_assets':False,'native_visual_validation':False}
(HERE/'package-proof-preflight.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
