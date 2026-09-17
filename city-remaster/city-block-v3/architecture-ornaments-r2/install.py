"""Install the street-facing correction over the exact, immutable R1 map."""
from pathlib import Path
import hashlib, json, shutil
H = Path(__file__).resolve().parent
R = H.parents[2]

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    candidate = json.loads((H/'candidate.json').read_text())
    for field in ('base_path', 'output_path', 'patch', 'preservation_report',
                  'parent_record', 'author_report', 'bvh_coverage', 'opening_validation',
                  'geometry_validation', 'window_anchors', 'ornament_validation',
                  'visibility_validation'):
        key = {'base_path': 'base_sha256', 'output_path': 'output_sha256'}.get(field, field+'_sha256')
        assert sha(candidate[field]) == candidate[key], field
    proof = json.loads(Path(candidate['preservation_report']).read_text())
    assert proof['status'] == 'passed' and all(proof['checks'].values())
    assert proof['before_sha256'] == candidate['base_sha256']
    assert proof['after_sha256'] == candidate['output_sha256']
    live = R/'data'/candidate['path']
    assert sha(live) == candidate['base_sha256'], 'Unexpected live architecture'
    record = H.parent/'architecture/revision-002/installed.json'
    assert not record.exists(), 'Revision already installed'
    protected = {str(R/'variants'/v/candidate['path']): sha(R/'variants'/v/candidate['path'])
                 for v in ('original', 'remaster-v1')}
    shutil.copy2(candidate['output_path'], live)
    assert sha(live) == candidate['output_sha256']
    candidate.update(status='installed', protected_variant_hashes=protected)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(candidate, indent=2)+'\n')
    print('Installed street-facing ornament correction:', sha(live))

if __name__ == '__main__':
    main()
