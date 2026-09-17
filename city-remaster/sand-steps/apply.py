"""Strict source-only sand-footstep patch. Default is validation; --apply writes."""
from pathlib import Path
import argparse,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
REL='goal_src/jak3/engine/game/effect-control.gc'
METHOD='(defmethod do-effect-for-surface ((this effect-control) (arg0 symbol) (arg1 float) (arg2 int) (arg3 basic) (arg4 pat-surface))\n'
NPC_MARKER='''    (when (logtest? (-> this flags) (effect-control-flag ecf0))
      (if (send-event (-> this process) 'effect-control s3-0 arg1 arg2)
          (return 0)
          )
      )
'''
BASELINE={'data':'28be20a3c2a8f4f2f57a58504b9ea9229fa38b91b3209fc48572b6660db34ee3',
          'engine-src':'8c3a19922b84a0bbaf91b3fd8f70a68d23f3def8896314030249857f2e7cb982'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');args=p.parse_args()
    table=(HERE/'surface-table.gc').read_text();helper=(HERE/'helper.gc').read_text();hook=(HERE/'hook.gc').read_text();npc=(HERE/'npc-hook.gc').read_text();entries=[];backups=HERE/'before'
    for tree in ('data','engine-src'):
        path=ROOT/tree/REL;original=path.read_text();saved=backups/(tree+'-effect-control.gc')
        if ';; REMASTER-SAND-STEPS-BEGIN' in original:
            assert saved.exists();base=saved.read_text()
        else:
            assert sha(path)==BASELINE[tree],f'Unknown source baseline: {tree}'
            base=original
        assert base.count(METHOD)==1 and base.count('(define *debug-effect-control* #f)')==1 and base.count(NPC_MARKER)==1
        added=table.rstrip()+'\n\n'+helper.rstrip()
        proposed=base.replace('(define *debug-effect-control* #f)', '(define *debug-effect-control* #f)\n\n'+added)
        proposed=proposed.replace(METHOD,METHOD+hook)
        proposed=proposed.replace(NPC_MARKER,NPC_MARKER+npc)
        # Strict removal proves all other source, including sound/water/landing
        # behavior, is identical after newline normalization.
        inverse=proposed.replace('\n\n'+added,'').replace(hook,'').replace(npc,'')
        assert inverse==base
        if args.apply:
            backups.mkdir(exist_ok=True)
            if not saved.exists():shutil.copy2(path,saved)
            assert sha(saved)==BASELINE[tree]
            path.write_text(proposed,encoding='utf-8',newline='\n')
        else:assert proposed==original,'Source patch not applied'
        entries.append({'path':str(path),'before':str(saved),'before_sha256':BASELINE[tree],
            'source_sha256':sha(path),'inverse_matches_baseline':True})
    assert (ROOT/'data'/REL).read_bytes()==(ROOT/'engine-src'/REL).read_bytes()
    dgo=ROOT/'data/out/jak3/iso/GAME.CGO';saved=backups/'GAME.CGO'
    if args.apply and not saved.exists():shutil.copy2(dgo,saved)
    assert saved.exists()
    manifest={'status':'source_ready_compile_pending','sources':entries,
        'helper_sha256':sha(HERE/'helper.gc'),'hook_sha256':sha(HERE/'hook.gc'),'npc_hook_sha256':sha(HERE/'npc-hook.gc'),'surface_table_sha256':sha(HERE/'surface-table.gc'),
        'dgo':'out/jak3/iso/GAME.CGO','baseline_dgo':str(saved),'baseline_dgo_sha256':sha(saved),
        'only_expected_object_change':'effect-control','levels':['wascitya','wascityb'],
        'allowed_collision_materials':{'sand':5,'dirt':15},'required_visual_texture':'wascity-ground-01',
        'particles_per_step':2,'lifetime_seconds':[.24,.30],
        'native_visual_validation':False,'runtime_compiled':False,'live_dgo_written':False}
    (HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'sources_identical':True,'inverse_checks':2,'compile_pending':True,'baseline_dgo_sha256':sha(saved)},indent=2))
if __name__=='__main__':main()
