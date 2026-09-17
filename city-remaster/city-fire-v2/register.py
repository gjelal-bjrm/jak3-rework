"""Stage/install one compiled generic-obs block after the latest audited GAME route.

Requires an explicit compiler hash and parent record. Does not run compilers,
stop/start a game or replace runtime binaries. Default is a dry run.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OBJECT='generic-obs';REL='out/jak3/iso/GAME.CGO';INSTALLED=HERE/'installed.json'
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
codec=module(ROOT/'city-remaster/sand-steps/register.py','city_fire_archive_codec');codec.OBJECT=OBJECT
source=module(HERE/'apply.py','city_fire_source_proof')
sha=codec.sha;digest=codec.digest;load=codec.load;encoded=codec.encoded;frozen=codec.frozen
def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.city-fire-new');temp.write_bytes(raw);os.replace(temp,path)
def preservation(before,after,payload):
    proof=codec.preservation(before,after,payload)
    proof['checks']['only_generic_obs_block_changed']=proof['checks'].pop('only_effect_control_block_changed')
    return proof
def source_proof():
    manifest=load(HERE/'manifest.json');assert manifest['status']=='applied'
    for relative in manifest['files']:source.source_before(relative)
    for relative,expected in manifest['new_files'].items():assert sha(ROOT/relative)==expected,relative
    gpu=load(HERE/'gpu-validation.json');assert gpu['status']=='passed'and all(gpu['checks'].values())
    for name,expected in gpu['shader_sha256'].items():assert sha(HERE/'shaders'/name)==expected
    recipe=load(HERE/'shader-provenance.json')
    for path,expected in recipe['accepted_recipe_sources'].items():assert sha(path)==expected
    assert recipe['outputs']==gpu['shader_sha256']
    fit=load(HERE/'source-fit.json');assert len(fit['fits'])==61
    for row in fit['sources']:assert sha(row['path'])==row['sha256']
    assert sha(ROOT/'city-remaster/inventory.json')==fit['inventory_sha256']
    assert {(r['level'],r['aid'])for r in fit['fits']}=={
      (r['level'],r['aid'])for r in load(ROOT/'city-remaster/inventory.json')['source_actor_fire_candidates_all_maps']
      if r['level']in('wascitya','wascityb')and r['art_name']in('group-waswide-gaslamp','group-waswide-talltorch')}
    return manifest

def verify_replaced_record(record, parent_path):
    """Verify the frozen failed revision without accepting arbitrary live bytes."""
    assert record['status']=='installed' and record['object']==OBJECT
    assert Path(record['parent_record']).resolve()==parent_path.resolve()
    assert sha(parent_path)==record['parent_record_sha256']==sha(record['parent_snapshot'])
    assert sha(record['object_path'])==record['object_sha256']
    assert sha(record['source_manifest'])==record['source_manifest_sha256']
    parent=load(record['parent_snapshot']);payload=Path(record['object_path']).read_bytes()
    assert set(record['routes'])==set(parent['routes'])=={'arena','palace'}
    for scene,row in record['routes'].items():
      assert row['baseline_sha256']==parent['routes'][scene]['output_sha256']
      for key,hash_key in [('baseline','baseline_sha256'),('candidate','output_sha256'),('preservation_report','preservation_sha256')]:
        assert sha(row[key])==row[hash_key]
      assert preservation(Path(row['baseline']).read_bytes(),Path(row['candidate']).read_bytes(),payload)==load(row['preservation_report'])
    for entry in record['protected_files']:assert sha(entry['path'])==entry['sha256']
    return record
def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--revise',action='store_true',help='Replace a verified city-fire revision over the exact same parent');p.add_argument('--parent-record',type=Path,required=True);p.add_argument('--object-sha256',required=True);args=p.parse_args()
    src=source_proof();obj=ROOT/'data/out/jak3/obj/generic-obs.o';payload=obj.read_bytes()
    assert sha(obj)==args.object_sha256 and len(args.object_sha256)==64,'Compiler output hash mismatch'
    assert b'pc-remaster-city-fire'in payload and b'pc-remaster-spawner-fire'in payload
    assert obj.stat().st_mtime_ns>=max((ROOT/r).stat().st_mtime_ns for r in src['files']if r.endswith('generic-obs.gc'))
    revision=None
    if INSTALLED.exists() and load(INSTALLED)['object_sha256']==args.object_sha256:
      errors=[];verify_installed(lambda ok,msg:errors.append(msg)if not ok else None,lambda p,h:errors.append(str(p))if sha(p)!=h else None)
      assert not errors,errors;print('City fire already installed and verified');return
    if INSTALLED.exists():
      assert args.revise,'A different installed object requires explicit --revise'
      revision=verify_replaced_record(load(INSTALLED),args.parent_record)
      old_source=load(revision['source_manifest'])
      assert old_source.keys()==src.keys() and old_source['new_files']==src['new_files']
      assert old_source['files'].keys()==src['files'].keys()
      for relative,old_entry in old_source['files'].items():
        new_entry=src['files'][relative]
        assert old_entry['before_path']==new_entry['before_path'] and old_entry['before_sha256']==new_entry['before_sha256']
        if not relative.endswith('generic-obs.gc'):assert old_entry==new_entry
    parent=load(args.parent_record);assert parent['status']=='installed'and set(parent['routes'])=={'arena','palace'}
    runtime_path=ROOT/'liquids-v3/runtime-manifest.json';runtime=load(runtime_path)
    stage=HERE/'staging'/('generic-obs-'+args.object_sha256[:16]);rows={};writes={}
    frozen(stage/'generic-obs.o',payload);frozen(stage/'source-manifest.json',(HERE/'manifest.json').read_bytes())
    frozen(stage/'parent-installed.json',args.parent_record.read_bytes())
    if revision:frozen(stage/'previous-installed.json',INSTALLED.read_bytes())
    for scene,parent_row in parent['routes'].items():
      route=ROOT/'routes/remaster'/scene/'GAME.CGO'
      if revision:
        previous=revision['routes'][scene]
        allowed={previous['output_sha256'],previous['baseline_sha256']}
        assert sha(route) in allowed and runtime['routes'][scene] in allowed,'Unexpected live city-fire revision: '+scene
        before=Path(previous['baseline']).read_bytes()
      else:
        before=route.read_bytes()
        assert digest(before)==runtime['routes'][scene],'Wrong runtime parent route: '+scene
      assert digest(before)==parent_row['output_sha256'],'Wrong parent route: '+scene
      candidate=codec.replace_object(before,payload);proof=preservation(before,candidate,payload)
      baseline=stage/scene/'before-GAME.CGO';target=stage/scene/'GAME.CGO';report=stage/scene/'preservation.json'
      frozen(baseline,before);frozen(target,candidate);frozen(report,encoded(proof))
      rows[scene]={'path':str(route),'baseline':str(baseline),'baseline_sha256':digest(before),
        'candidate':str(target),'output_sha256':digest(candidate),'preservation_report':str(report),
        'preservation_sha256':sha(report),'preserved_objects':proof['preserved_objects']};writes[route]=candidate
    scene=(ROOT/'current-scene.txt').read_text().strip();active=ROOT/'data'/REL
    allowed_active={rows[scene]['baseline_sha256']}
    if revision:allowed_active.add(revision['routes'][scene]['output_sha256'])
    assert (ROOT/'current-variant.txt').read_text().strip()=='remaster'and sha(active) in allowed_active
    writes[active]=Path(rows[scene]['candidate']).read_bytes()
    after=dict(runtime);after['routes']={scene:row['output_sha256']for scene,row in rows.items()}
    frozen(stage/'runtime-before.json',runtime_path.read_bytes());frozen(stage/'runtime-after.json',encoded(after));writes[runtime_path]=encoded(after)
    files_path=ROOT/'variant-files.json';hashes_path=ROOT/'variant-hashes.json';files=load(files_path);hashes=load(hashes_path)
    protected=codec.protected_files()
    shader_paths=[]
    for asset in sorted((HERE/'shaders').glob('*')):
      relative='game/graphics/opengl_renderer/shaders/'+asset.name;shader_paths.append(relative)
      raw=(ROOT/'data'/relative).read_bytes();assert raw==asset.read_bytes()
      if relative not in files:files.append(relative)
      for variant in ('original','remaster-v1','remaster'):
        dest=ROOT/'variants'/variant/relative
        # Additional unused shader files make variant switching complete; no
        # previously existing original or V1 file may be overwritten.
        if dest.exists():assert dest.read_bytes()==raw
        else:writes[dest]=raw
        hashes[variant][relative]=digest(raw)
    frozen(stage/'variant-files-before.json',files_path.read_bytes());frozen(stage/'variant-hashes-before.json',hashes_path.read_bytes())
    writes[files_path]=encoded(files);writes[hashes_path]=encoded(hashes)
    record={'status':'installed','object':OBJECT,'object_path':str(stage/'generic-obs.o'),'object_sha256':args.object_sha256,
      'source_manifest':str(stage/'source-manifest.json'),'source_manifest_sha256':sha(stage/'source-manifest.json'),
      'parent_record':str(args.parent_record.resolve()),'parent_record_sha256':sha(args.parent_record),
      'parent_snapshot':str(stage/'parent-installed.json'),'routes':rows,'protected_files':protected,
      'runtime_before':str(stage/'runtime-before.json'),'runtime_before_sha256':sha(stage/'runtime-before.json'),
      'runtime_after':str(stage/'runtime-after.json'),'runtime_after_sha256':sha(stage/'runtime-after.json'),
      'added_shaders':shader_paths,'applied_scene':scene,'native_visual_validation':False}
    if revision:
      record['replaces_record']=str(stage/'previous-installed.json')
      record['replaces_record_sha256']=sha(stage/'previous-installed.json')
      record['replaces_object_sha256']=revision['object_sha256']
    frozen(stage/'install-plan.json',encoded(record));writes[INSTALLED]=encoded(record)
    print(json.dumps({'mode':'apply'if args.apply else'dry-run','routes':rows,'new_shaders':shader_paths},indent=2))
    if not args.apply:return
    previous={p:p.read_bytes()if p.exists()else None for p in writes}
    try:
      for path,raw in writes.items():atomic(path,raw)
      for e in protected:assert sha(e['path'])==e['sha256']
      for path,raw in writes.items():assert path.read_bytes()==raw
    except BaseException:
      for path,raw in previous.items():
        if raw is None:
          if path.exists():path.unlink()
        else:atomic(path,raw)
      raise
    print('Installed generic-obs only; all other GAME blocks preserved; six city shader files registered')
def previous_route(scene):
    record=load(INSTALLED);row=record['routes'][scene];payload=Path(record['object_path']).read_bytes()
    before=Path(row['baseline']);assert sha(before)==row['baseline_sha256']
    assert preservation(before.read_bytes(),Path(row['path']).read_bytes(),payload)==load(row['preservation_report'])
    return before
def verify_installed(check,matches):
    if not INSTALLED.exists():return None
    record=load(INSTALLED);check(record['status']=='installed'and record['object']==OBJECT,'Invalid city fire installation')
    matches(Path(record['object_path']),record['object_sha256']);matches(Path(record['source_manifest']),record['source_manifest_sha256'])
    check(load(record['source_manifest'])==source_proof(),'City fire source provenance differs')
    matches(Path(record['parent_record']),record['parent_record_sha256']);matches(Path(record['parent_snapshot']),record['parent_record_sha256'])
    if 'replaces_record' in record:
      matches(Path(record['replaces_record']),record['replaces_record_sha256'])
      previous=verify_replaced_record(load(record['replaces_record']),Path(record['parent_record']))
      check(previous['object_sha256']==record['replaces_object_sha256'],'Replaced city-fire object identity differs')
      check(all(previous['routes'][scene]['baseline_sha256']==row['baseline_sha256']for scene,row in record['routes'].items()),'City-fire revision changed its original parent')
    parent=load(record['parent_snapshot']);payload=Path(record['object_path']).read_bytes();runtime=load(ROOT/'liquids-v3/runtime-manifest.json')
    for scene,row in record['routes'].items():
      check(row['baseline_sha256']==parent['routes'][scene]['output_sha256'],'City fire archive parent differs')
      for k,h in [('path','output_sha256'),('candidate','output_sha256'),('baseline','baseline_sha256'),('preservation_report','preservation_sha256')]:matches(Path(row[k]),row[h])
      check(preservation(Path(row['baseline']).read_bytes(),Path(row['path']).read_bytes(),payload)==load(row['preservation_report']),'City fire preserved archive blocks differ')
      check(runtime['routes'][scene]==row['output_sha256'],'City fire runtime head differs')
    for e in record['protected_files']:matches(Path(e['path']),e['sha256'])
    for relative in record['added_shaders']:
      expected=sha(ROOT/'data'/relative)
      for variant in ('original','remaster-v1','remaster'):matches(ROOT/'variants'/variant/relative,expected)
    scene=(ROOT/'current-scene.txt').read_text().strip();matches(ROOT/'data'/REL,record['routes'][scene]['output_sha256'])
    return record
if __name__=='__main__':main()
