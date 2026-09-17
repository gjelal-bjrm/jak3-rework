"""Install a validated market Merc batch; retain comparison assets."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
CONTROLS={'cty-fruit-stand-lod0','wascity-awning-b-lod0','wascity-awning-b-lod1','market-crate-lod0','market-basket-a-lod0','market-basket-b-lod0','market-sack-a-lod0','market-sack-b-lod0'}
LEVELS={'wascitya.fr3','wascityb.fr3'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,j):p.write_text(json.dumps(j,indent=2))
def copy(source,dest):
    # Replace the entry so an existing hardlink cannot mutate original data.
    dest.parent.mkdir(parents=True,exist_ok=True);temp=dest.with_name(dest.name+'.market-new')
    shutil.copy2(source,temp);assert sha(temp)==sha(source);os.replace(temp,dest)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',type=Path);ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    stage=a.stage.resolve();assert stage.is_relative_to(HERE/'staging'),'Stage outside city workspace'
    report=read(stage/'import-report.json')
    assert report['status']=='passed' and report['protected_hashes_unchanged']
    assert not report['changed_protected_files'] and report['merc_replacement_confirmed_by_extractor']
    models=report['models'];assert models and {m['control'] for m in models}<=CONTROLS
    for m in models:assert sha(Path(m['authored']['path']))==m['authored']['sha256'],'Author changed since extraction'
    assert report['candidates'] and set(report['candidates'])<=LEVELS
    entries=[]
    for name,c in report['candidates'].items():
        source=Path(c['path']);assert source.resolve().is_relative_to(stage) and sha(source)==c['sha256']
        preservation=read(Path(c['preservation_report']))
        assert preservation['status']=='passed' and all(preservation['checks'].values())
        assert preservation['current_static_sha256']==preservation['candidate_static_sha256']
        rel='out/jak3/fr3/'+name;live=ROOT/'data'/rel
        assert sha(live)==c['base_sha256'],'Untracked live city change'
        original=ROOT.parents[1]/'active/jak3/data'/rel
        entries.append({'path':rel,'base_sha256':c['base_sha256'],'output_sha256':c['sha256'],'original_path':str(original),'original_sha256':sha(original),'candidate_path':str(source),'preservation_report':str(Path(c['preservation_report']))})
    record={'levels':entries,'controls':[m['control'] for m in models],'models':[{'control':m['control'],'path':m['authored']['path'],'sha256':m['authored']['sha256']} for m in models],'stage_report':str(stage/'import-report.json'),'native_visual_validation':False,'scope':'Rebuilt market controls and embedded materials; native animation, collision and fruit responses retained','remaining':'City vegetation, terrain, buildings, static market supports and shared fire modernization pending'}
    print(json.dumps({'apply':a.apply,'levels':[e['path'] for e in entries],'controls':record['controls']},indent=2))
    if not a.apply:return
    backup=stage/'pre-deployment';backup.mkdir(exist_ok=True)
    for name in ['variant-files.json','variant-hashes.json']:
        if not (backup/name).exists():shutil.copy2(ROOT/name,backup/name)
    files=read(ROOT/'variant-files.json');hashes=read(ROOT/'variant-hashes.json')
    for e in entries:
        rel=e['path'];current=ROOT/'data'/rel;dest=backup/rel
        if not dest.exists():copy(current,dest)
        if rel not in files:files.append(rel)
        for variant in ['original','remaster-v1','remaster']:
            dest=ROOT/'variants'/variant/rel;source=Path(e['candidate_path'] if variant=='remaster' else e['original_path'])
            if variant!='remaster' and dest.exists():assert sha(dest)==e['original_sha256']
            copy(source,dest);hashes[variant][rel]=sha(dest)
        copy(Path(e['candidate_path']),current)
        assert sha(Path(e['original_path']))==e['original_sha256'],'Original asset changed'
    for m in record['models']:
        authored=Path(m['path']);dest=ROOT/'data/custom_assets/jak3/merc_replacements'/authored.name
        copy(authored,dest);m['replacement_path']=str(dest)
    write(ROOT/'variant-files.json',files);write(ROOT/'variant-hashes.json',hashes);write(HERE/'installed.json',record)
if __name__=='__main__':main()
