"""Create an isolated texture-only WCA/WCB/WASWIDE descendant; never deploy it."""
import argparse, subprocess
from common import *
from prepare import prepare

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True)
    args=parser.parse_args();stage=stage_path(args.stage)
    assert not stage.exists(), 'Use a new stage name; existing candidates are immutable'
    parents=records();bases=[]
    # Prove current levels descend from their tracked installation or baseline.
    for level in LEVELS:
        live=ROOT/'data'/relative(level);h=sha(live);parent=parent_for(level,h,parents)
        assert sha(ROOT/'variants/remaster'/relative(level))==h, 'Live/remaster variant mismatch'
        bases.append((level,live,h,parent))
    stage.mkdir(parents=True)
    prepared=prepare(stage/'prepared');copy(HERE/'generated-materials.json',stage/'generation-manifest.json')
    assert sha(stage/'generation-manifest.json')==prepared['manifest_sha256']
    protected=[]
    for level,live,h,parent in bases:
        copy(live,stage/('before-'+level+'.fr3'));assert sha(live)==h
        for variant in ('original','remaster-v1'):
            p=ROOT/'variants'/variant/relative(level);protected.append({'path':str(p),'sha256':sha(p)})
    command=[str(BLENDER_PYTHON),str(HERE/'audit.py'),'--inventory',str(stage/'native-inventory.json')]
    for level,_,_,_ in bases:command+=['--input',str(stage/('before-'+level+'.fr3'))]
    subprocess.run(command,check=True,cwd=ROOT)
    inventory=read(stage/'native-inventory.json');rows=[];used=set()
    for level,live,h,parent in bases:
        available={t['name'] for t in inventory[level]['textures']}
        selected=[m for m in prepared['materials'] if m['name'] in available]
        assert selected, f'No approved master belongs to {level}'
        used.update(m['name'] for m in selected)
        before=stage/('before-'+level+'.fr3');candidate=stage/(level+'.fr3');patchpath=stage/(level+'-patch.json')
        patch={'level':level,'source_fr3':{'sha256':h,'bytes':before.stat().st_size},'preserve_bvh':True,'remove':[],'add':[],
            'textures':[{k:m[k] for k in ('name','width','height','rgba_file')} for m in selected]}
        write(patchpath,patch)
        rows.append({'level':level,'path':relative(level),'before':str(before),'base_sha256':h,'candidate':str(candidate),
            'patch':str(patchpath),'patch_sha256':sha(patchpath),'parent':parent,'materials':[m['name'] for m in selected]})
    assert used=={m['name'] for m in prepared['materials']}, 'Approved master absent from all three levels'
    plan={'status':'staged_pending_audit','scope':'WCA/WCB/WASWIDE broad surface materials, pixels only','levels':rows,
        'parent_records':parents,'protected_variants':protected,'prepared':str(stage/'prepared/prepared.json'),
        'prepared_sha256':sha(stage/'prepared/prepared.json'),'bridge_sha256':sha(BRIDGE),'native_visual_validation':False}
    write(stage/'stage.json',plan)
    for row in rows:
        with (stage/(row['level']+'-bridge.log')).open('w') as log:
            subprocess.run([str(BRIDGE),row['before'],row['patch'],row['candidate']],stdout=log,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
    subprocess.run([str(BLENDER_PYTHON),str(HERE/'audit.py'),'--stage',str(stage)],check=True,cwd=ROOT)
    print(json.dumps({'stage':str(stage),'materials':len(used),'audit':'passed','deployed':False},indent=2))

if __name__=='__main__':main()
