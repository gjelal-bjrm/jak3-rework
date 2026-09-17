"""Install the audited R4 map over exact R3, retaining historical records."""
from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[2]
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
c=json.loads((H/'candidate.json').read_text())
for field in ('base_path','output_path','patch','preservation_report','parent_record','author_report','restoration_validation','street_visibility_validation','bvh_coverage','opening_validation','geometry_validation','window_anchors'):
 key={'base_path':'base_sha256','output_path':'output_sha256'}.get(field,field+'_sha256')
 assert sha(c[field])==c[key],field
p=json.loads(Path(c['preservation_report']).read_text())
assert p['status']=='passed' and all(p['checks'].values())
assert p['before_sha256']==c['base_sha256'] and p['after_sha256']==c['output_sha256']
live=R/'data'/c['path'];record=H.parent/'architecture/revision-004/installed.json'
assert sha(live)==c['base_sha256'] and not record.exists()
protected={str(R/'variants'/v/c['path']):sha(R/'variants'/v/c['path'])for v in('original','remaster-v1')}
shutil.copy2(c['output_path'],live);assert sha(live)==c['output_sha256']
assert all(sha(p)==s for p,s in protected.items())
c.update(status='installed',protected_variant_hashes=protected)
record.parent.mkdir(parents=True,exist_ok=True);record.write_text(json.dumps(c,indent=2)+'\n')
print('Installed R4',c['output_sha256'])

