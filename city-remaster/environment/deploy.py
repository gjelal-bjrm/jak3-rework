"""Dry-run by default. Explicit --apply installs or rolls back an audited stage."""
import argparse
from common import *

def check_current(row,expected):
    for base in (ROOT/'data',ROOT/'variants/remaster'):
        assert sha(base/row['path'])==expected, f'Untracked current level: {base/row["path"]}'

def check_protected(plan):
    for item in plan['protected_variants']:
        assert sha(item['path'])==item['sha256'], 'Original/V1 variant changed'

def verify(stage):
    plan=read(stage/'stage.json');proof=read(stage/'audit.json')
    assert proof['status']=='passed' and proof['stage_sha256']==sha(stage/'stage.json')
    assert proof['auditor_sha256']==sha(HERE/'audit.py') and proof['parser_sha256']==sha(CITY/'compare_market.py')
    assert all(r['status']=='passed' and r['checks'] and all(r['checks'].values()) for r in proof['levels'])
    assert sha(plan['prepared'])==plan['prepared_sha256']
    prepared=read(plan['prepared'])
    assert sha(prepared['manifest'])==prepared['manifest_sha256'], 'Generation catalogue changed; restage all current masters'
    for material in prepared['materials']:
        assert sha(material['master'])==material['master_sha256'], 'Master changed after staging'
        assert sha(material['rgba_file'])==material['rgba_sha256'], 'Encoded pixels changed after audit'
    for parent in plan['parent_records']:
        assert sha(parent['path'])==parent['sha256'], 'Parent installation chain changed; restage'
    check_protected(plan)
    results={r['level']:r for r in proof['levels']}
    assert set(results)==set(LEVELS) and len(plan['levels'])==len(LEVELS)
    for row in plan['levels']:
        assert row['path']==relative(row['level'])
        result=results[row['level']]
        assert sha(row['before'])==row['base_sha256']==result['before_sha256']
        assert sha(row['candidate'])==result['after_sha256']
        assert sha(row['patch'])==row['patch_sha256']==result['patch_sha256']
        check_current(row,row['base_sha256'])
    return plan,proof,prepared

def install(stage,apply):
    plan,proof,prepared=verify(stage)
    results={r['level']:r for r in proof['levels']}
    record={'status':'active','stage':str(stage),'scope':plan['scope'],
        'audit':str(stage/'audit.json'),'audit_sha256':sha(stage/'audit.json'),
        'stage_sha256':sha(stage/'stage.json'),'prepared_sha256':plan['prepared_sha256'],
        'parent_records':plan['parent_records'],'native_visual_validation':False,
        'levels':[{**row,'output_sha256':results[row['level']]['after_sha256'],
                   'preserved_static_sha256':results[row['level']]['static_sha256'],
                   'preserved_merc_tail_sha256':results[row['level']]['merc_tail_sha256']}
                  for row in plan['levels']]}
    print(json.dumps({'action':'install','apply':apply,'stage':str(stage),'materials':len(prepared['materials']),
        'outputs':{r['level']:r['output_sha256'] for r in record['levels']}},indent=2))
    if not apply:return
    hashes_path=ROOT/'variant-hashes.json';old_hashes=hashes_path.read_bytes()
    installed=HERE/'installed.json';old_installed=installed.read_bytes() if installed.exists() else None
    # Retain the exact previous descendant for rollback; these are not upstream records.
    (stage/'before-variant-hashes.json').write_bytes(old_hashes)
    if old_installed is not None:(stage/'previous-environment-installed.json').write_bytes(old_installed)
    try:
        for row in record['levels']:
            for base in (ROOT/'data',ROOT/'variants/remaster'):copy(row['candidate'],base/row['path'])
        hashes=json.loads(old_hashes.decode('utf-8-sig'))
        for row in record['levels']:hashes['remaster'][row['path']]=row['output_sha256']
        # WASWIDE is a newly tracked level. Its original/V1 copies were frozen
        # from a proven byte-identical original before this descendant existed.
        for item in plan['protected_variants']:
            protected=Path(item['path']);rel=protected.relative_to(ROOT/'variants').parts
            variant=rel[0];key='/'.join(rel[1:]);existing=hashes[variant].get(key)
            assert existing in (None,item['sha256']), 'Registered original/V1 hash disagrees with frozen copy'
            hashes[variant][key]=item['sha256']
        write(hashes_path,hashes);write(installed,record);write(stage/'installed-record.json',record)
        for row in record['levels']:check_current(row,row['output_sha256'])
        check_protected(plan)
    except BaseException:
        for row in record['levels']:
            for base in (ROOT/'data',ROOT/'variants/remaster'):copy(row['before'],base/row['path'])
        hashes_path.write_bytes(old_hashes)
        if old_installed is not None:installed.write_bytes(old_installed)
        elif installed.exists():installed.unlink()
        raise

def rollback(apply):
    installed=HERE/'installed.json';record=read(installed)
    assert record['status']=='active', 'No active environment descendant to roll back'
    stage=stage_path(Path(record['stage']).name);assert stage==Path(record['stage'])
    plan=read(stage/'stage.json');check_protected(plan)
    for row in record['levels']:
        assert row['path']==relative(row['level'])
        check_current(row,row['output_sha256'])
        assert sha(row['before'])==row['base_sha256'], 'Rollback snapshot changed'
        assert sha(row['candidate'])==row['output_sha256']
    print(json.dumps({'action':'rollback','apply':apply,'stage':str(stage),
        'restore':{r['level']:r['base_sha256'] for r in record['levels']}},indent=2))
    if not apply:return
    hashes_path=ROOT/'variant-hashes.json';old_hashes=hashes_path.read_bytes();old_installed=installed.read_bytes()
    try:
        for row in record['levels']:
            for base in (ROOT/'data',ROOT/'variants/remaster'):copy(row['before'],base/row['path'])
        # Preserve unrelated later entries: update only this batch's levels.
        hashes=json.loads(old_hashes.decode('utf-8-sig'))
        for row in record['levels']:hashes['remaster'][row['path']]=row['base_sha256']
        write(hashes_path,hashes)
        rollback_report={'status':'rolled_back','previous_environment_record_sha256':digest(old_installed),
            'restored':{r['path']:r['base_sha256'] for r in record['levels']}}
        write(stage/'rollback.json',rollback_report)
        previous=stage/'previous-environment-installed.json'
        previous_matches=False
        if previous.exists():
            previous_rows={r['path']:r['output_sha256'] for r in read(previous).get('levels',[])}
            previous_matches=previous_rows==rollback_report['restored']
        if previous_matches:copy(previous,installed)
        else:
            # Geometry may have advanced between texture batches. Do not restore
            # an old environment manifest that identifies a different WCB.
            write(installed,{'status':'rolled_back','stage':str(stage),'rollback_report':str(stage/'rollback.json'),
                'parent_records':record['parent_records'],
                'levels':[{'level':r['level'],'path':r['path'],'output_sha256':r['base_sha256'],
                           'source_path':r['before'],'parent':r['parent']} for r in record['levels']]})
        for row in record['levels']:check_current(row,row['base_sha256'])
    except BaseException:
        for row in record['levels']:
            for base in (ROOT/'data',ROOT/'variants/remaster'):copy(row['candidate'],base/row['path'])
        hashes_path.write_bytes(old_hashes);installed.write_bytes(old_installed);raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage');parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true')
    args=parser.parse_args()
    if args.rollback:
        assert args.stage is None, 'Rollback uses the current installed record';rollback(args.apply)
    else:
        assert args.stage, '--stage required';install(stage_path(args.stage),args.apply)
