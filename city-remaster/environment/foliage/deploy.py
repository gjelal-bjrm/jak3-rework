"""Install this audited foliage descendant; preserve original/V1 and its parent."""
from pathlib import Path
import argparse, hashlib, json, os, shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');a=parser.parse_args()
    record=read(HERE/'candidate.json')
    for p,h in [('base_path','base_sha256'),('output_path','output_sha256'),
                ('patch','patch_sha256'),('preservation_report','preservation_report_sha256'),
                ('author_report','author_report_sha256'),('parent_record','parent_record_sha256')]:
        assert sha(record[p])==record[h],p
    audit=read(record['preservation_report'])
    assert audit['status']=='passed' and all(v is True for v in audit['checks'].values())
    assert audit['before_sha256']==record['base_sha256'] and audit['after_sha256']==record['output_sha256']
    assert audit['patch_sha256']==record['patch_sha256']
    for p,h in record['protected_live_variant_hashes'].items():assert sha(p)==h,p
    assert record['base_sha256']==read(record['parent_record'])['output_sha256']
    print(json.dumps({'apply':a.apply,'output_sha256':record['output_sha256'],'palms':record['palms_rebuilt']}))
    if not a.apply:return
    assert not (HERE/'installed.json').exists(),'Already installed'
    shutil.copy2(ROOT/'variant-hashes.json',HERE/'variant-hashes-before.json')
    for tree in ['data','variants/remaster']:
        dest=ROOT/tree/record['path'];temp=dest.with_name(dest.name+'.foliage-new')
        shutil.copy2(record['output_path'],temp);assert sha(temp)==record['output_sha256'];os.replace(temp,dest)
    hashes=read(ROOT/'variant-hashes.json');hashes['remaster'][record['path']]=record['output_sha256']
    write(ROOT/'variant-hashes.json',hashes)
    record['status']='installed';record['live_files_written']=True
    write(HERE/'installed.json',record)
if __name__=='__main__':main()
