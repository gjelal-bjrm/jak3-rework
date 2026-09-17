"""Install only a pinned and strictly audited WCA architecture candidate."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;R=H.parents[2]
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 candidate=json.loads((H/'candidate.json').read_text())
 for field in ('base_path','output_path','patch','preservation_report','parent_record','author_report','bvh_coverage','opening_validation','geometry_validation','window_anchors'):
  key={'base_path':'base_sha256','output_path':'output_sha256'}.get(field,field+'_sha256')
  assert sha(candidate[field])==candidate[key],field
 proof=json.loads(Path(candidate['preservation_report']).read_text())
 assert proof['status']=='passed' and all(proof['checks'].values())
 assert proof['before_sha256']==candidate['base_sha256'] and proof['after_sha256']==candidate['output_sha256']
 live=R/'data'/candidate['path'];assert sha(live)in(candidate['base_sha256'],candidate['output_sha256'])
 original={variant:sha(R/'variants'/variant/candidate['path'])for variant in ('original','remaster-v1')}
 shutil.copy2(candidate['output_path'],live)
 candidate.update(status='installed',protected_variant_hashes={str(R/'variants'/v/candidate['path']):s for v,s in original.items()})
 (H/'installed.json').write_text(json.dumps(candidate,indent=2)+'\n')
 print('Installed two WCA houses; native acceptance pending:',sha(live))
if __name__=='__main__':main()
