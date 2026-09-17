"""Build and audit an isolated WCB palm candidate. Never deploy or rebuild."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parent
sys.path.insert(0,str(CITY))
from audit_native_patch import audit
def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text())
def main():
    validation=read(HERE/'validation.json');report=read(HERE/'report.json')
    patch=HERE/'patch.json';base=Path(report['source_fr3']['path']);out=HERE/'wascityb.fr3'
    bridge=ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'
    assert validation['status']=='passed' and all(validation['checks'].values())
    assert sha(patch)==validation['patch_sha256']==report['patch_sha256']
    assert sha(base)==report['source_fr3']['sha256']
    assert not out.exists(),'Candidate exists: never overwrite an earlier reviewed candidate'
    protected=[ROOT/'data/out/jak3/fr3/wascityb.fr3',ROOT/'variants/remaster/out/jak3/fr3/wascityb.fr3',
        ROOT/'variants/original/out/jak3/fr3/wascityb.fr3',ROOT/'variants/remaster-v1/out/jak3/fr3/wascityb.fr3']
    before={str(p):sha(p)for p in protected};bridge_hash=sha(bridge)
    with (HERE/'bridge.log').open('w')as log:
        subprocess.run([str(bridge),str(base),str(patch),str(out)],check=True,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    result=audit(base,out,patch,HERE/'preservation.json')
    assert all(sha(Path(p))==h for p,h in before.items()),'Live or variant changed during isolated staging'
    assert sha(bridge)==bridge_hash
    manifest={'status':'candidate_audited_not_installed','path':'out/jak3/fr3/wascityb.fr3',
        'base_path':str(base),'base_sha256':sha(base),'output_path':str(out),'output_sha256':sha(out),
        'patch':str(patch),'patch_sha256':sha(patch),'preservation_report':str(HERE/'preservation.json'),
        'preservation_report_sha256':sha(HERE/'preservation.json'),'author_report':str(HERE/'validation.json'),
        'author_report_sha256':sha(HERE/'validation.json'),'bridge_sha256':bridge_hash,
        'parent_record':str(CITY/'static-installed.json'),'parent_record_sha256':sha(CITY/'static-installed.json'),
        'scope':'All 13 remaining native WCB palm instances (11 distinct positions), including complete crowns and four LODs; preserve two accepted market palms',
        'palms_rebuilt':13,'accepted_palms_preserved':2,'triangles_by_lod':report['triangles_by_lod'],
        'native_visual_validation':False,'protected_live_variant_hashes':before,'live_files_written':False,
        'remaining':'Native culling, wind and performance inspection; WCA palms are outside this candidate.'}
    (HERE/'candidate.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'candidate':str(out),'sha256':manifest['output_sha256'],'audit':result['status'],'installed':False},indent=2))
if __name__=='__main__':main()
