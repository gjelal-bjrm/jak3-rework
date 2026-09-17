"""Freeze old/new city fire archives locally. Never installs or controls the game."""
from pathlib import Path
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FIRE = ROOT / 'city-remaster/city-fire-v2'
STAGE = HERE / 'staging'
EXPECTED_OBJECT = '0f8e38bda699d2043140c8318de2f9d010eed352fd2df39e8cffb0f1271e6a41'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def freeze(path, raw):
    path = Path(path).resolve()
    assert path.is_relative_to(HERE), 'Writes outside fire-comparison are forbidden'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, 'Existing evidence must not be overwritten: ' + str(path)
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    return {'path': str(path), 'sha256': sha(path)}


def codec():
    spec = importlib.util.spec_from_file_location('fire_comparison_register', FIRE / 'register.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare():
    reg = codec()
    installed = load(FIRE / 'installed.json')
    assert installed['status'] == 'installed' and installed['object'] == 'generic-obs'
    assert installed['object_sha256'] == EXPECTED_OBJECT == sha(installed['object_path'])
    assert sha(installed['parent_record']) == installed['parent_record_sha256'] == sha(installed['parent_snapshot'])
    assert sha(installed['source_manifest']) == installed['source_manifest_sha256']
    parent = load(installed['parent_snapshot'])
    sources = load(installed['source_manifest'])
    payload = Path(installed['object_path']).read_bytes()
    assert b'pc-remaster-city-fire' in payload and b'pc-remaster-spawner-fire' in payload
    result = {
        'status': 'staged', 'native_capture_status': 'pending',
        'description': 'Legacy city fire emitter versus palace-derived city fire, under the same current renderer and assets. Not the original PS2 renderer.',
        'scope': 'generic-obs only; fresh process required per version; all other objects and assets identical',
        'installed_record': freeze(STAGE / 'installed.json', (FIRE / 'installed.json').read_bytes()),
        'parent_record': freeze(STAGE / 'parent-installed.json', Path(installed['parent_snapshot']).read_bytes()),
        'source_manifest': freeze(STAGE / 'source-manifest.json', Path(installed['source_manifest']).read_bytes()),
        'after_object': freeze(STAGE / 'after-generic-obs.o', payload),
        'source_before': [], 'routes': {},
    }
    # These exact inverse sources document removal of city registration only.
    for relative, entry in sources['files'].items():
        if not relative.endswith('generic-obs.gc'):
            continue
        before = reg.source.source_before(relative)
        assert sha(before) == entry['before_sha256']
        assert sha(ROOT / relative) == entry['after_sha256']
        text = before.read_text(encoding='utf-8-sig')
        assert 'pc-remaster-spawner-fire' not in text
        assert '(spawn (-> self part) (-> self root trans))' in text
        result['source_before'].append(freeze(STAGE / 'source-before' / relative, before.read_bytes()))
    assert len(result['source_before']) == 2
    original_payloads = []
    for scene in ('arena', 'palace'):
        row = installed['routes'][scene]
        assert row['baseline_sha256'] == parent['routes'][scene]['output_sha256']
        assert sha(row['baseline']) == row['baseline_sha256']
        assert sha(row['candidate']) == row['output_sha256']
        assert sha(row['preservation_report']) == row['preservation_sha256']
        before = Path(row['baseline']).read_bytes()
        after = Path(row['candidate']).read_bytes()
        proof = reg.preservation(before, after, payload)
        assert proof == load(row['preservation_report'])
        assert proof['preserved_objects'] == 489 and proof['changed_objects'] == ['generic-obs']
        _, objects = reg.codec.archive(before)
        old = next(o['payload'] for o in objects if o['name'] == 'generic-obs')
        assert b'pc-remaster-city-fire' not in old and b'pc-remaster-spawner-fire' not in old
        original_payloads.append(old)
        # Negative check: changing any other block must be rejected.
        victim = next(o for o in objects if o['name'] != 'generic-obs' and o['payload'])
        at = after.find(victim['block']) + 64
        assert at >= 64
        corrupted = bytearray(after)
        corrupted[at] ^= 1
        rejected = False
        try:
            reg.preservation(before, bytes(corrupted), payload)
        except AssertionError:
            rejected = True
        assert rejected, 'Preservation audit accepted an unrelated object mutation'
        result['routes'][scene] = {
            'before': freeze(STAGE / scene / 'before-GAME.CGO', before),
            'after': freeze(STAGE / scene / 'after-GAME.CGO', after),
            'preservation': freeze(STAGE / scene / 'preservation.json', encoded(proof)),
            'preserved_objects': 489, 'unrelated_object_mutation_rejected': rejected,
        }
    assert original_payloads[0] == original_payloads[1]
    result['before_object'] = freeze(STAGE / 'before-generic-obs.o', original_payloads[0])
    result['camera_views'] = {'path': str(HERE / 'camera-views.json'), 'sha256': sha(HERE / 'camera-views.json')}
    freeze(HERE / 'comparison.json', encoded(result))
    print(json.dumps({'status': result['status'], 'routes': result['routes'], 'native_capture_status': 'pending'}, indent=2))


if __name__ == '__main__':
    prepare()
