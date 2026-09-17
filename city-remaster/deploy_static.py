"""Install a preservation-audited static batch descended from market Merc004.

Keeps the Merc installation record intact and records this patch as a separate
descendant. Staging, original and V1 levels remain available for comparison.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,os
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2),encoding='utf-8')
def copy(source,dest):
    temp=dest.with_name(dest.name+'.static-new');shutil.copy2(source,temp)
    assert sha(temp)==sha(source);os.replace(temp,dest)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',type=Path);parser.add_argument('--apply',action='store_true');a=parser.parse_args()
    stage=a.stage.resolve();assert stage.parent==HERE/'staging'
    source=stage/'before-wascityb.fr3';candidate=stage/'wascityb.fr3';patch=stage/'combined-patch.json';audit=stage/'preservation.json'
    author=read(stage/'author-validation.json');proof=read(audit)
    assert proof.get('status')=='passed' and proof.get('checks') and all(proof['checks'].values()),'Native preservation audit failed'
    # Audit must identify these exact binaries, not just an earlier sample.
    assert proof['before_sha256']==sha(source) and proof['after_sha256']==sha(candidate)
    assert proof['patch_sha256']==sha(patch)
    assert author['base_sha256']==sha(source) and author['patch_sha256']==sha(patch)
    for part in author['parts']:assert sha(Path(part['path']))==part['sha256'],'Author patch changed after staging'
    rel='out/jak3/fr3/wascityb.fr3';current=ROOT/'data'/rel
    merc=next(x for x in read(HERE/'installed.json')['levels'] if x['path']==rel)
    assert sha(source)==merc['output_sha256'],'Unexpected Merc baseline'
    expected_live=author.get('replaces_live_sha256',sha(source))
    assert sha(current)==expected_live,'Untracked live baseline'
    previous_path=HERE/'static-installed.json'
    if expected_live!=sha(source):
        previous=read(previous_path)
        assert previous['output_sha256']==expected_live and previous['base_sha256']==sha(source)
    record={'path':rel,'base_path':str(source),'base_sha256':sha(source),'output_path':str(candidate),'output_sha256':sha(candidate),'patch':str(patch),'patch_sha256':sha(patch),'preservation_report':str(audit),'author_report':str(stage/'author-validation.json'),'parts':author['parts'],'scope':author['scope'],'native_visual_validation':False,'remaining':'Native visual inspection pending. This batch does not complete the city, buildings, terrain or regional fire.'}
    for variant in ['original','remaster-v1']:
        assert sha(ROOT/'variants'/variant/rel)==merc['original_sha256']
    print(json.dumps({'apply':a.apply,'scope':record['scope'],'output_sha256':record['output_sha256']},indent=2))
    if not a.apply:return
    if previous_path.exists():shutil.copy2(previous_path,stage/'previous-static-installed.json')
    for name in ['variant-hashes.json','variant-files.json']:
        dest=stage/('before-'+name)
        if not dest.exists():shutil.copy2(ROOT/name,dest)
    copy(candidate,current);copy(candidate,ROOT/'variants/remaster'/rel)
    hashes=read(ROOT/'variant-hashes.json');hashes['remaster'][rel]=sha(candidate)
    write(ROOT/'variant-hashes.json',hashes);write(HERE/'static-installed.json',record)

if __name__=='__main__':main()
