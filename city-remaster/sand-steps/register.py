"""Prepare a bounded effect-control CGO replacement; --apply installs audited routes.

No compiler, game, renderer, original route or comparison variant is modified.
Default execution writes only immutable candidates/proofs in sand-steps/staging.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OBJECT = 'effect-control'
REL = 'out/jak3/iso/GAME.CGO'
SOURCE_REL = 'goal_src/jak3/engine/game/effect-control.gc'
INITIAL_ROUTES = {
    'arena': 'dfe44d6452e6079fd961c19044495a2fec98f9d2489abaec4fea1447e2fc288f',
    'palace': '5aa47d7ad847d6f407a261e0fbc93d353f625d8748f2cae3119584a63a94bce5',
}
INSTALLED = HERE / 'installed.json'


def digest(data): return hashlib.sha256(data).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def encoded(value): return (json.dumps(value, indent=2) + '\n').encode()


def archive(data):
    assert len(data) >= 64, 'Truncated CGO header'
    count = struct.unpack_from('<I', data)[0]
    assert count < 10000, 'Implausible CGO count'
    offset = 64
    objects = []
    for index in range(count):
        assert offset + 64 <= len(data), 'Truncated object header'
        size = struct.unpack_from('<I', data, offset)[0]
        header = data[offset:offset + 64]
        name = header[4:].split(b'\0', 1)[0].decode('ascii')
        end = offset + 64 + ((size + 15) & ~15)
        assert name and end <= len(data), 'Truncated/unnamed object'
        objects.append({'index': index, 'name': name, 'header': header,
                        'payload': data[offset + 64:offset + 64 + size],
                        'block': data[offset:end]})
        offset = end
    assert offset == len(data), 'Unexpected trailing CGO bytes'
    assert sum(o['name'] == OBJECT for o in objects) == 1, 'Target object not unique'
    return data[:64], objects


def replace_object(before, payload):
    header, objects = archive(before)
    blocks = []
    for obj in objects:
        if obj['name'] != OBJECT or obj['payload'] == payload:
            blocks.append(obj['block'])
        else:
            blocks.append(struct.pack('<I', len(payload)) + obj['header'][4:] +
                          payload + bytes((-len(payload)) % 16))
    return header + b''.join(blocks)


def preservation(before, after, payload, require_change=True):
    bh, bo = archive(before)
    ah, ao = archive(after)
    changed = [a['name'] for a, b in zip(bo, ao) if a['block'] != b['block']]
    checks = {
        'archive_header_identical': bh == ah,
        'object_count_and_order_identical': [o['name'] for o in bo] == [o['name'] for o in ao],
        'only_effect_control_block_changed': changed == ([OBJECT] if require_change else []),
        'all_other_headers_payloads_padding_identical': len(bo) == len(ao) and all(
            a['block'] == b['block'] for a, b in zip(bo, ao) if a['name'] != OBJECT),
        'target_header_name_bytes_identical': next(o for o in bo if o['name'] == OBJECT)['header'][4:] ==
                                            next(o for o in ao if o['name'] == OBJECT)['header'][4:],
        'compiled_object_payload_exact': next(o for o in ao if o['name'] == OBJECT)['payload'] == payload,
        'strict_inverse_restores_entire_archive': replace_object(
            after, next(o for o in bo if o['name'] == OBJECT)['payload']) == before,
    }
    assert all(checks.values()), [k for k, v in checks.items() if not v]
    return {'status': 'passed', 'checks': checks, 'before_sha256': digest(before),
            'after_sha256': digest(after), 'object_sha256': digest(payload),
            'changed_objects': changed, 'preserved_objects': len(bo) - 1,
            'objects': [{'index': a['index'], 'name': a['name'],
                         'before_block_sha256': digest(a['block']),
                         'after_block_sha256': digest(b['block'])} for a, b in zip(bo, ao)]}


def source_proof():
    manifest = load(HERE / 'source-manifest.json')
    helper = (HERE / 'helper.gc').read_text()
    hook = (HERE / 'hook.gc').read_text()
    npc = (HERE / 'npc-hook.gc').read_text()
    table = (HERE / 'surface-table.gc').read_text()
    assert sha(HERE / 'helper.gc') == manifest['helper_sha256']
    assert sha(HERE / 'hook.gc') == manifest['hook_sha256']
    assert sha(HERE / 'npc-hook.gc') == manifest['npc_hook_sha256']
    assert sha(HERE / 'surface-table.gc') == manifest['surface_table_sha256']
    added = table.rstrip() + '\n\n' + helper.rstrip()
    assert manifest['only_expected_object_change'] == OBJECT
    expected_paths = {str((ROOT / tree / SOURCE_REL).resolve()) for tree in ('data', 'engine-src')}
    assert {str(Path(e['path']).resolve()) for e in manifest['sources']} == expected_paths
    method = '(defmethod do-effect-for-surface ((this effect-control) (arg0 symbol) (arg1 float) (arg2 int) (arg3 basic) (arg4 pat-surface))\n'
    npc_marker = '''    (when (logtest? (-> this flags) (effect-control-flag ecf0))
      (if (send-event (-> this process) 'effect-control s3-0 arg1 arg2)
          (return 0)
          )
      )
'''
    for entry in manifest['sources']:
        current = Path(entry['path']); baseline = Path(entry['before'])
        assert sha(current) == entry['source_sha256'] and sha(baseline) == entry['before_sha256']
        base = baseline.read_text(); text = current.read_text()
        assert base.count(method) == 1 and base.count('(define *debug-effect-control* #f)') == 1 and base.count(npc_marker) == 1
        expected = base.replace('(define *debug-effect-control* #f)',
                                '(define *debug-effect-control* #f)\n\n' + added)
        expected = expected.replace(method, method + hook)
        expected = expected.replace(npc_marker, npc_marker + npc)
        assert text == expected, 'Source outside the three exact insertions changed'
        assert text.count('\n\n' + added) == 1 and text.count(hook) == 1 and text.count(npc) == 1
        assert text.replace('\n\n' + added, '', 1).replace(hook, '', 1).replace(npc, '', 1) == base
    assert (ROOT / 'data' / SOURCE_REL).read_bytes() == (ROOT / 'engine-src' / SOURCE_REL).read_bytes()
    assert sha(manifest['baseline_dgo']) == manifest['baseline_dgo_sha256'] == INITIAL_ROUTES['palace']
    surface = load(HERE / 'surface-validation.json')
    assert surface['status'] == 'passed' and surface['table_sha256'] == manifest['surface_table_sha256']
    assert surface['allowed_texture'] == manifest['required_visual_texture'] == 'wascity-ground-01'
    assert surface['probes'] and all(p['result'] == p['expected'] for p in surface['probes'])
    for entry in surface['sources']: assert sha(entry['export']) == entry['export_sha256']
    return manifest


def frozen(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): assert path.read_bytes() == raw, 'Immutable snapshot differs: ' + str(path)
    else: path.write_bytes(raw)


def protected_files():
    records = []
    hashes = load(ROOT / 'variant-hashes.json')
    for variant in ('original', 'remaster-v1'):
        for rel, expected in hashes[variant].items():
            path = ROOT / 'variants' / variant / rel
            assert sha(path) == expected, 'Comparison variant already changed: ' + str(path)
            records.append({'path': str(path), 'sha256': expected})
    for scene in INITIAL_ROUTES:
        path = ROOT / 'routes' / scene / 'GAME.CGO'
        records.append({'path': str(path), 'sha256': sha(path)})
    return records


def atomic_write(path, raw):
    temp = path.with_name(path.name + '.sand-steps-new')
    temp.write_bytes(raw); os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--object', type=Path, default=ROOT / 'data/out/jak3/obj/effect-control.o')
    args = parser.parse_args()
    sources = source_proof()
    obj_path = args.object.resolve(); payload = obj_path.read_bytes()
    assert b'remaster-sand-step-contact?' in payload and b'remaster-sand-step-launcher' in payload, 'Unmodified/wrong compiled object'
    assert obj_path.stat().st_mtime_ns >= max(Path(e['path']).stat().st_mtime_ns for e in sources['sources']), 'Object predates source changes'
    runtime_path = ROOT / 'liquids-v3/runtime-manifest.json'
    runtime = load(runtime_path)
    previous = load(INSTALLED) if INSTALLED.exists() else None
    stage = HERE / 'staging' / ('effect-control-' + digest(payload)[:16])
    protected = protected_files()
    if previous:
        for entry in previous['protected_files']: assert sha(entry['path']) == entry['sha256']
    frozen(stage / 'source-manifest.json', (HERE / 'source-manifest.json').read_bytes())
    frozen(stage / 'surface-validation.json', (HERE / 'surface-validation.json').read_bytes())
    frozen(stage / 'effect-control.o', payload)
    # Baseline route snapshots are created separately: their start-up objects differ.
    rows = []; writes = {}
    for scene, original_sha in INITIAL_ROUTES.items():
        path = ROOT / 'routes/remaster' / scene / 'GAME.CGO'
        baseline = HERE / 'before/routes' / scene / 'GAME.CGO'
        if not baseline.exists():
            assert sha(path) == original_sha, 'Unknown route before baseline snapshot'
            frozen(baseline, path.read_bytes())
        assert sha(baseline) == original_sha
        expected_current = previous['routes'][scene]['output_sha256'] if previous else original_sha
        assert sha(path) == expected_current == runtime['routes'][scene], 'Route/runtime head changed'
        candidate = replace_object(baseline.read_bytes(), payload)
        proof = preservation(baseline.read_bytes(), candidate, payload)
        dest = stage / scene / 'GAME.CGO'; proof_path = stage / scene / 'preservation.json'
        frozen(dest, candidate); frozen(proof_path, encoded(proof))
        rows.append({'scene': scene, 'path': str(path), 'baseline': str(baseline),
                     'baseline_sha256': original_sha, 'candidate': str(dest),
                     'output_sha256': digest(candidate), 'preservation_report': str(proof_path),
                     'preservation_sha256': sha(proof_path), 'preserved_objects': proof['preserved_objects']})
        writes[path] = candidate
    scene = (ROOT / 'current-scene.txt').read_text().strip()
    assert scene in INITIAL_ROUTES and (ROOT / 'current-variant.txt').read_text().strip() == 'remaster'
    active = ROOT / 'data' / REL
    baseline = next(Path(r['baseline']) for r in rows if r['scene'] == scene)
    # Permit an already rebuilt target, but never silently overwrite other live objects.
    ah, ao = archive(active.read_bytes()); bh, bo = archive(baseline.read_bytes())
    assert ah == bh and [o['name'] for o in ao] == [o['name'] for o in bo]
    assert all(a['block'] == b['block'] for a, b in zip(ao, bo) if a['name'] != OBJECT), 'Live CGO has unrelated changes'
    writes[active] = next(Path(r['candidate']).read_bytes() for r in rows if r['scene'] == scene)
    new_runtime = dict(runtime); new_runtime['routes'] = {r['scene']: r['output_sha256'] for r in rows}
    installed = {'status': 'installed', 'object': OBJECT, 'object_path': str(stage / 'effect-control.o'),
                 'object_sha256': digest(payload), 'compiled_from': str(obj_path),
                 'source_manifest': str(stage / 'source-manifest.json'),
                 'source_manifest_sha256': sha(stage / 'source-manifest.json'),
                 'surface_validation': str(stage / 'surface-validation.json'),
                 'surface_validation_sha256': sha(stage / 'surface-validation.json'),
                 'routes': {r['scene']: r for r in rows}, 'protected_files': protected,
                 'runtime_before': str(stage / 'runtime-before.json'),
                 'runtime_before_sha256': sha(runtime_path),
                 'runtime_after': str(stage / 'runtime-after.json'),
                 'runtime_after_sha256': digest(encoded(new_runtime)), 'applied_scene': scene,
                 'native_visual_validation': False}
    # Repeated --apply of the same candidate is a read-only no-op.
    if previous and previous['object_sha256'] == digest(payload):
        assert all(path.read_bytes() == raw for path, raw in writes.items())
        print('Already installed; routes and live archive still match'); return
    frozen(stage / 'runtime-before.json', runtime_path.read_bytes())
    frozen(stage / 'runtime-after.json', encoded(new_runtime))
    frozen(stage / 'install-plan.json', encoded(installed))
    print(json.dumps({'mode': 'apply' if args.apply else 'dry-run', 'stage': str(stage),
                      'changed_objects': [OBJECT], 'routes': [{k: r[k] for k in ('scene', 'preserved_objects', 'output_sha256')} for r in rows]}, indent=2))
    if not args.apply: return
    # Prepare all candidate bytes before the first mutation; restore exactly on error.
    writes[runtime_path] = encoded(new_runtime); writes[INSTALLED] = encoded(installed)
    previous_bytes = {p: p.read_bytes() if p.exists() else None for p in writes}
    try:
        for path, raw in writes.items(): atomic_write(path, raw)
        for entry in protected: assert sha(entry['path']) == entry['sha256']
        for path, raw in writes.items(): assert path.read_bytes() == raw
    except BaseException:
        for path, raw in previous_bytes.items():
            if raw is None:
                if path.exists(): path.unlink()
            else: atomic_write(path, raw)
        raise
    print('Installed: only effect-control replaced in each remaster route and active GAME.CGO')


def verify_installed(check, matches, successor=None):
    if not INSTALLED.exists(): return
    record = load(INSTALLED)
    check(record['status'] == 'installed' and record['object'] == OBJECT, 'Unexpected sand-step installation')
    matches(Path(record['object_path']), record['object_sha256'])
    matches(Path(record['source_manifest']), record['source_manifest_sha256'])
    check(load(record['source_manifest']) == source_proof(), 'Installed sand-step source provenance changed')
    matches(Path(record['surface_validation']), record['surface_validation_sha256'])
    check(load(record['surface_validation']) == load(HERE / 'surface-validation.json'), 'Installed sand surface proof changed')
    payload = Path(record['object_path']).read_bytes()
    check(set(record['routes']) == set(INITIAL_ROUTES), 'Missing sand-step route')
    # A separately verified logic-target descendant may now be the live head.
    # The sand record remains immutable and is proved against its exact output.
    if successor is not None:
        check(successor['status'] == 'installed' and successor['object'] == 'logic-target',
              'Unrecognized successor for sand-step route verification')
        check(successor['parent_record_sha256'] == sha(INSTALLED),
              'Grass successor is not anchored to this exact sand-step record')
    runtime = load(successor['runtime_before']) if successor else load(ROOT / 'liquids-v3/runtime-manifest.json')
    matches(Path(record['runtime_before']), record['runtime_before_sha256'])
    matches(Path(record['runtime_after']), record['runtime_after_sha256'])
    old_runtime = load(record['runtime_before'])
    applied_runtime = load(record['runtime_after'])
    check({k: v for k, v in old_runtime.items() if k != 'routes'} ==
          {k: v for k, v in applied_runtime.items() if k != 'routes'}, 'Sand-step installation changed runtime metadata beyond routes')
    for scene, row in record['routes'].items():
        check(row['baseline_sha256'] == INITIAL_ROUTES[scene], 'Unknown sand-step route baseline')
        matches(Path(row['baseline']), row['baseline_sha256'])
        route = Path(successor['routes'][scene]['baseline']) if successor else Path(row['path'])
        if successor:
            check(successor['routes'][scene]['baseline_sha256'] == row['output_sha256'],
                  'Sand route does not match the successor predecessor')
        matches(route, row['output_sha256'])
        matches(Path(row['candidate']), row['output_sha256'])
        matches(Path(row['preservation_report']), row['preservation_sha256'])
        actual = preservation(Path(row['baseline']).read_bytes(), route.read_bytes(), payload)
        check(actual == load(row['preservation_report']), 'Sand-step byte preservation proof differs')
        check(runtime['routes'][scene] == row['output_sha256'], 'Runtime route does not match sand-step installation')
        check(applied_runtime['routes'][scene] == row['output_sha256'], 'Sand-step runtime snapshot route differs')
    for entry in record['protected_files']: matches(Path(entry['path']), entry['sha256'])
    scene = (ROOT / 'current-scene.txt').read_text().strip()
    if successor:
        matches(Path(successor['routes'][scene]['baseline']), record['routes'][scene]['output_sha256'])
    else:
        matches(ROOT / 'data' / REL, record['routes'][scene]['output_sha256'])


if __name__ == '__main__': main()
