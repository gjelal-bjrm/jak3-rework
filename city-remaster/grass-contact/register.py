"""Append only logic-target to the installed sand-step routes. No compiler/game."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OBJECT='logic-target'
EXPECTED_OBJECT='bda9445ece1b1aa376c2780227e8beb938c6b5d13adbf6b8b94d4b2a72cd16ab'
REL='out/jak3/iso/GAME.CGO'
INSTALLED=HERE/'installed.json'

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
codec=module(ROOT/'city-remaster/sand-steps/register.py','grass_cgo_codec')
codec.OBJECT=OBJECT
source=module(HERE/'apply.py','grass_source_proof')
sha=codec.sha;load=codec.load;encoded=codec.encoded;frozen=codec.frozen;digest=codec.digest

def preservation(before,after,payload):
    proof=codec.preservation(before,after,payload)
    proof['checks']['only_logic_target_block_changed']=proof['checks'].pop('only_effect_control_block_changed')
    return proof

def source_proof():
    record=load(HERE/'manifest.json')
    assert record['status']=='applied'and set(record['files'])==set(source.edits())
    for relative in record['files']:source.source_before(relative)
    assert sha(ROOT/record['new_header'])==sha(HERE/'GrassContacts.h')==record['new_header_sha256']
    return record

def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.grass-contact-new');temp.write_bytes(raw);os.replace(temp,path)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    src=source_proof()
    obj=ROOT/'data/out/jak3/obj/logic-target.o';payload=obj.read_bytes()
    assert sha(obj)==EXPECTED_OBJECT,'Unreviewed compiled logic-target object'
    assert b'pc-remaster-grass-contact'in payload
    assert obj.stat().st_mtime_ns>=max((ROOT/r).stat().st_mtime_ns for r in src['files']if r.endswith('logic-target.gc'))
    if INSTALLED.exists():
        errors=[]
        verify_installed(lambda ok,msg:errors.append(msg)if not ok else None,
                         lambda p,h:errors.append('Hash mismatch: '+str(p))if sha(p)!=h else None)
        assert not errors,errors
        print('Already installed; all grass route and source checks pass');return
    parent_path=ROOT/'city-remaster/sand-steps/installed.json';parent=load(parent_path)
    assert parent['status']=='installed'and parent['object']=='effect-control'
    runtime_path=ROOT/'liquids-v3/runtime-manifest.json';runtime=load(runtime_path)
    stage=HERE/'staging'/('logic-target-'+EXPECTED_OBJECT[:16])
    protected=codec.protected_files()
    frozen(stage/'logic-target.o',payload)
    frozen(stage/'source-manifest.json',(HERE/'manifest.json').read_bytes())
    frozen(stage/'parent-installed.json',parent_path.read_bytes())
    rows={};writes={}
    for scene,parent_row in parent['routes'].items():
        route=ROOT/'routes/remaster'/scene/'GAME.CGO'
        before=route.read_bytes()
        assert digest(before)==parent_row['output_sha256']==runtime['routes'][scene]
        baseline=stage/scene/'before-GAME.CGO';candidate_path=stage/scene/'GAME.CGO';proof_path=stage/scene/'preservation.json'
        candidate=codec.replace_object(before,payload);proof=preservation(before,candidate,payload)
        frozen(baseline,before);frozen(candidate_path,candidate);frozen(proof_path,encoded(proof))
        rows[scene]={'path':str(route),'baseline':str(baseline),'baseline_sha256':digest(before),
          'candidate':str(candidate_path),'output_sha256':digest(candidate),'preservation_report':str(proof_path),
          'preservation_sha256':sha(proof_path),'preserved_objects':proof['preserved_objects']}
        writes[route]=candidate
    scene=(ROOT/'current-scene.txt').read_text().strip();active=ROOT/'data'/REL
    assert scene in rows and(ROOT/'current-variant.txt').read_text().strip()=='remaster'
    assert sha(active)==rows[scene]['baseline_sha256'],'Live GAME changed outside the tracked dust route'
    writes[active]=Path(rows[scene]['candidate']).read_bytes()
    new_runtime=dict(runtime);new_runtime['routes']={scene:row['output_sha256']for scene,row in rows.items()}
    frozen(stage/'runtime-before.json',runtime_path.read_bytes());frozen(stage/'runtime-after.json',encoded(new_runtime))
    record={'status':'installed','object':OBJECT,'object_path':str(stage/'logic-target.o'),'object_sha256':EXPECTED_OBJECT,
      'source_manifest':str(stage/'source-manifest.json'),'source_manifest_sha256':sha(stage/'source-manifest.json'),
      'parent_record':str(parent_path),'parent_record_sha256':sha(parent_path),
      'parent_snapshot':str(stage/'parent-installed.json'),'routes':rows,'protected_files':protected,
      'runtime_before':str(stage/'runtime-before.json'),'runtime_before_sha256':sha(stage/'runtime-before.json'),
      'runtime_after':str(stage/'runtime-after.json'),'runtime_after_sha256':sha(stage/'runtime-after.json'),
      'applied_scene':scene,'native_visual_validation':False}
    frozen(stage/'install-plan.json',encoded(record))
    print(json.dumps({'mode':'apply'if args.apply else'dry-run','stage':str(stage),'routes':rows},indent=2))
    if not args.apply:return
    writes[runtime_path]=encoded(new_runtime);writes[INSTALLED]=encoded(record)
    previous={p:p.read_bytes()if p.exists()else None for p in writes}
    try:
        for p,raw in writes.items():atomic(p,raw)
        for e in protected:assert sha(e['path'])==e['sha256']
        for p,raw in writes.items():assert p.read_bytes()==raw
    except BaseException:
        for p,raw in previous.items():
            if raw is None:
                if p.exists():p.unlink()
            else:atomic(p,raw)
        raise
    print('Installed only logic-target; effect-control and all other blocks preserved')

def verify_installed(check,matches,successor=None):
    if not INSTALLED.exists():return None
    record=load(INSTALLED)
    check(record['status']=='installed'and record['object']==OBJECT,'Unexpected grass installation')
    matches(Path(record['object_path']),record['object_sha256'])
    check(record['object_sha256']==EXPECTED_OBJECT,'Grass object differs from the reviewed compile')
    matches(Path(record['source_manifest']),record['source_manifest_sha256'])
    check(load(record['source_manifest'])==source_proof(),'Installed grass source provenance changed')
    matches(Path(record['parent_record']),record['parent_record_sha256'])
    matches(Path(record['parent_snapshot']),record['parent_record_sha256'])
    parent=load(record['parent_snapshot']);payload=Path(record['object_path']).read_bytes()
    check(parent['object']=='effect-control'and set(parent['routes'])==set(record['routes']),
          'Grass installation is not a complete descendant of sand routes')
    matches(Path(record['runtime_before']),record['runtime_before_sha256'])
    matches(Path(record['runtime_after']),record['runtime_after_sha256'])
    before=load(record['runtime_before']);after=load(record['runtime_after'])
    if successor is not None:
        check(successor['status']=='installed'and successor['object']=='generic-obs',
              'Unrecognized successor for grass GAME verification')
        check(successor['parent_record_sha256']==sha(INSTALLED),
              'City fire successor does not name this exact grass installation')
    if successor:
        # A corrected city-fire object records the previous city-fire runtime
        # at installation time. Peel its exact immutable revision records to
        # reach the first city-fire insertion over this grass parent.
        first=successor;seen=set()
        while 'replaces_record' in first:
            revision_path=Path(first['replaces_record']).resolve()
            check(str(revision_path) not in seen,'Cycle in city-fire revision records')
            if str(revision_path) in seen:raise AssertionError('City-fire revision cycle')
            seen.add(str(revision_path))
            matches(revision_path,first['replaces_record_sha256'])
            previous=load(revision_path)
            check(previous['status']=='installed'and previous['object']=='generic-obs'and
                  previous['object_sha256']==first['replaces_object_sha256']and
                  previous['parent_record_sha256']==sha(INSTALLED),
                  'City-fire revision changed object identity or grass parent')
            check(set(previous['routes'])==set(record['routes'])and
                  all(previous['routes'][scene]['baseline_sha256']==row['output_sha256']
                      for scene,row in record['routes'].items()),
                  'City-fire revision has a different grass route baseline')
            first=previous
        matches(Path(first['runtime_before']),first['runtime_before_sha256'])
        runtime=load(first['runtime_before'])
    else:runtime=load(ROOT/'liquids-v3/runtime-manifest.json')
    check({k:v for k,v in before.items()if k!='routes'}=={k:v for k,v in after.items()if k!='routes'},
          'Grass installation altered unrelated runtime metadata')
    for scene,row in record['routes'].items():
        check(row['baseline_sha256']==parent['routes'][scene]['output_sha256']==before['routes'][scene],
              'Grass route does not start from the installed dust output')
        route=Path(successor['routes'][scene]['baseline'])if successor else Path(row['path'])
        if successor:
            check(successor['routes'][scene]['baseline_sha256']==row['output_sha256'],
                  'Grass route does not match the city fire predecessor')
        matches(route,row['output_sha256'])
        for key,hashkey in [('baseline','baseline_sha256'),('candidate','output_sha256'),('preservation_report','preservation_sha256')]:
            matches(Path(row[key]),row[hashkey])
        proof=preservation(Path(row['baseline']).read_bytes(),route.read_bytes(),payload)
        check(proof==load(row['preservation_report']),'Grass native archive preservation proof differs')
        check(row['output_sha256']==after['routes'][scene]==runtime['routes'][scene],'Grass current route/runtime head mismatch')
    for e in record['protected_files']:matches(Path(e['path']),e['sha256'])
    scene=(ROOT/'current-scene.txt').read_text().strip()
    if successor:matches(Path(successor['routes'][scene]['baseline']),record['routes'][scene]['output_sha256'])
    else:matches(ROOT/'data'/REL,record['routes'][scene]['output_sha256'])
    return record

if __name__=='__main__':main()
