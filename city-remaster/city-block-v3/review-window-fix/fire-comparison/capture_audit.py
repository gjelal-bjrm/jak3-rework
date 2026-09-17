"""Read-only capture provenance. Writes evidence only inside fire-comparison."""
from pathlib import Path
import argparse
import re

from prepare import HERE, ROOT, codec, encoded, freeze, load, sha

GAME = 'out/jak3/iso/GAME.CGO'


def name(value):
    assert re.fullmatch(r'[a-z0-9-]+', value), 'Use a short lowercase evidence name'
    return value


def environment():
    # A complete package snapshot plus runtime-loaded shaders/interiors. The
    # latter catch an extra, unregistered file that package manifests might miss.
    relative = set(load(ROOT / 'variant-files.json'))
    for directory in ('game/graphics/opengl_renderer/shaders', 'custom_assets/jak3/city-interiors'):
        relative.update(str(p.relative_to(ROOT / 'data')).replace('\\', '/')
                        for p in (ROOT / 'data' / directory).rglob('*') if p.is_file())
    relative.update(('out/jak3/fr3/wascitya.fr3', 'out/jak3/fr3/wascityb.fr3',
                     'out/jak3/iso/WCA.DGO', 'out/jak3/iso/WCB.DGO'))
    relative.discard(GAME)
    files = {p: sha(ROOT / 'data' / p) for p in sorted(relative)}
    runtime = load(ROOT / 'liquids-v3/runtime-manifest.json')['runtime']
    files['@runtime/' + runtime] = sha(ROOT / runtime)
    return files


def snapshot(args):
    manifest = load(HERE / 'comparison.json')
    expected = manifest['routes'][args.scene][args.version]['sha256']
    assert sha(ROOT / 'data' / GAME) == expected, 'Wrong active GAME for requested fire version'
    views = load(HERE / 'camera-views.json')
    assert sha(HERE / 'camera-views.json') == manifest['camera_views']['sha256']
    dest = HERE / 'captures' / name(args.tag)
    result = {
        'status': 'environment-recorded', 'version': args.version, 'scene': args.scene,
        'view': args.view, 'planned_camera': views[args.view],
        'game_sha256': expected, 'comparison_sha256': sha(HERE / 'comparison.json'),
        'environment': environment(),
        'note': 'File provenance is automatic. Native camera/time/audio readback is supplied by the capture operator and preserved separately.',
    }
    for field, source in (('image', args.image), ('log', args.log), ('native_state', args.state)):
        if source:
            result[field] = freeze(dest / (field + Path(source).suffix), Path(source).read_bytes())
    if args.state:
        state = load(args.state)
        for key in ('eye_m', 'target_m', 'fov_degrees', 'time_of_day', 'render_size', 'fresh_process', 'audio_muted'):
            assert key in state, 'Missing native readback: ' + key
        assert state['fresh_process'] is True and state['audio_muted'] is True
        assert 1 < state['fov_degrees'] < 179
        assert len(state['render_size']) == 2 and all(v >= 64 for v in state['render_size'])
        assert state['time_of_day'] and 'REMPLACER' not in str(state['time_of_day'])
        assert len(state['eye_m']) == len(state['target_m']) == 3
        for key in ('eye_m', 'target_m'):
            assert max(abs(a-b) for a, b in zip(state[key], views[args.view][key])) < .01, 'Camera differs from agreed view'
        result['operator_native_readback'] = state
    # Refuse to record through concurrent deployment.
    assert sha(ROOT / 'data' / GAME) == expected
    assert result['environment'] == environment(), 'Assets changed during snapshot; retry with a new tag after deployment'
    freeze(dest / 'record.json', encoded(result))
    print('Recorded ' + str(dest / 'record.json'))


def pair(args):
    a = load(HERE / 'captures' / name(args.before) / 'record.json')
    b = load(HERE / 'captures' / name(args.after) / 'record.json')
    manifest = load(HERE / 'comparison.json')
    assert a['version'] == 'before' and b['version'] == 'after'
    for key in ('scene', 'view', 'planned_camera', 'comparison_sha256', 'environment'):
        assert a[key] == b[key], 'Capture pair differs: ' + key
    assert a['comparison_sha256'] == sha(HERE / 'comparison.json')
    for record in (a, b):
        assert record['game_sha256'] == manifest['routes'][record['scene']][record['version']]['sha256']
        for field in ('image', 'log', 'native_state'):
            assert field in record, 'Missing native evidence: ' + field
            assert sha(record[field]['path']) == record[field]['sha256']
    for key in ('eye_m', 'target_m', 'fov_degrees', 'time_of_day', 'render_size'):
        assert a['operator_native_readback'][key] == b['operator_native_readback'][key], 'Native readbacks differ: ' + key
    for record in (a, b):
        assert record['operator_native_readback']['fresh_process'] is True
        assert record['operator_native_readback']['audio_muted'] is True
    # Verify the staged CGO difference again; never trust a declared version only.
    row = manifest['routes'][a['scene']]
    for item in row.values():
        if isinstance(item, dict) and 'path' in item:
            assert sha(item['path']) == item['sha256']
    reg = codec()
    report = reg.preservation(Path(row['before']['path']).read_bytes(),
                              Path(row['after']['path']).read_bytes(),
                              Path(manifest['after_object']['path']).read_bytes())
    assert report == load(row['preservation']['path'])
    result = {'status': 'provenance-passed', 'visual_review_status': 'pending',
              'view': a['view'], 'before': a, 'after': b,
              'scope': 'Only the generic-obs fire emitter differs; the renderer and all recorded assets are identical. Camera/time/audio are operator readback evidence, not inferred from pixels.'}
    freeze(HERE / 'pairs' / (name(args.before) + '--' + name(args.after) + '.json'), encoded(result))
    print('Pair provenance passed; inspect both native images and animation before claiming a visual pass.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot')
    snap.add_argument('--tag', required=True)
    snap.add_argument('--version', choices=('before', 'after'), required=True)
    snap.add_argument('--scene', choices=('arena', 'palace'), default='palace')
    snap.add_argument('--view', choices=('wca', 'wcb'), required=True)
    snap.add_argument('--image', type=Path)
    snap.add_argument('--log', type=Path)
    snap.add_argument('--state', type=Path, help='Native readbacks supplied by root; format in README')
    compare = commands.add_parser('pair')
    compare.add_argument('--before', required=True)
    compare.add_argument('--after', required=True)
    args = parser.parse_args()
    snapshot(args) if args.command == 'snapshot' else pair(args)


if __name__ == '__main__':
    main()
