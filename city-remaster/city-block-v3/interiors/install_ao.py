"""Preserve the authored rooms, then adopt the reviewed neutral contact shading."""
from pathlib import Path
import hashlib, json, shutil
H = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    source = H/'ao-candidate'
    proof = json.loads((source/'validation.json').read_text())
    bake = json.loads((source/'bake-report.json').read_text())
    assert proof['status'] == 'passed' and all(r['passed'] and all(r['checks'].values()) for r in proof['rooms'])
    assert not (H/'ao-installed.json').exists(), 'Already installed'
    record = {'status': 'installed', 'rooms': [], 'proofs': {}}
    for name in ('validation.json', 'bake-report.json', 'bake.py', 'verify.py', 'gpu-comparison.json'):
        record['proofs'][str(source/name)] = sha(source/name)
    for room in bake['rooms']:
        name = room['layout']
        assert sha(H/(name+'.bin')) == room['source_sha256']
        assert sha(source/(name+'.bin')) == room['candidate_sha256']
        files = {}
        for ext in ('.bin', '.json'):
            live = H/(name+ext)
            before = H/'no-ao'/(name+ext)
            assert not before.exists()
            before.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, before)
            shutil.copy2(source/(name+ext), live)
            files[name+ext] = {'before_path': str(before), 'before_sha256': sha(before),
                              'after_path': str(live), 'after_sha256': sha(live)}
        record['rooms'].append({'layout': name, 'files': files})
    (H/'ao-installed.json').write_text(json.dumps(record, indent=2)+'\n')
    print('Installed neutral room contact shading; authored source rooms preserved')

if __name__ == '__main__':
    main()
