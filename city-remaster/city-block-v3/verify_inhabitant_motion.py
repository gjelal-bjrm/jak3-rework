"""Strict, read-only verification of the two installed dialogue animation revisions.

The predecessor maps preserve the earlier package's source and runtime proof
chain. They do not exempt the current files: every installed byte is checked here.
"""
from pathlib import Path
import copy
import hashlib
import json
import math
import struct


ACTORS = {'conversing-male': 5310, 'conversing-female': 6288}
FILES = {name + ext for name in ACTORS for ext in ('.json', '.bin')}
UNCHANGED = {'sitting-male.bin', 'sitting-male.json', 'validation.json', 'source-manifest.json'}
PREVIEWS = {'pair-frame-00.png', 'pair-frame-06.png', 'pair-frame-06-side.png',
            'pair-frame-12.png', 'pair-frame-22.png'}
PROOFS = PREVIEWS | {'README.md', 'author.py', 'preview.py'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime_json(meta):
    """Reproduce interiors/prepare.py's existing source-to-runtime conversion."""
    result = copy.deepcopy(meta)
    for draw in result['draws']:
        draw['texture'] = draw['texture'].replace('.png', '.rgba')
    return json.dumps(result, indent=2).encode('utf-8')


def area(a, b, c):
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    return math.sqrt(sum(x*x for x in (u[1]*v[2]-u[2]*v[1],
                                     u[2]*v[0]-u[0]*v[2],
                                     u[0]*v[1]-u[1]*v[0]))) * .5


def verify(actors_directory, check, matches):
    directory = Path(actors_directory)
    here = directory / 'motion-v2'
    installed_path = here / 'installed.json'
    if not installed_path.exists():
        # A staged revision may exist while the original package remains live.
        for name in ACTORS:
            check(load(directory / (name+'.json'))['frame_count'] == 4,
                  'Revised dialogue actor is installed without motion-v2 provenance')
        return {}
    installed = load(installed_path)
    check(set(installed) == {'status', 'provenance_sha256'} and installed['status'] == 'installed',
          'Dialogue motion installation broadens its immutable record')
    matches(here / 'provenance.json', installed['provenance_sha256'])
    record = load(here / 'provenance.json')
    check(set(record) == {'version', 'scope', 'author', 'author_sha256',
                         'native_topology_preserved', 'predecessor_files', 'candidate_files',
                         'sources', 'native_game_validation', 'room_transform_recommendation',
                         'status', 'proofs', 'previews', 'unchanged_source_files'} and
          record['version'] == 2 and record['status'] == 'staged' and
          record['scope'] == 'Only conversing-male and conversing-female; staged, not installed.' and
          record['native_game_validation'] is False and record['native_topology_preserved'] is True,
          'Dialogue motion revision changes scope or claims a native-game validation')
    check(set(record['predecessor_files']) == FILES and
          set(record['sources']) == {'male-selected.glb', 'female-selected.glb'} and
          set(record['unchanged_source_files']) == UNCHANGED and
          set(record['proofs']) == PROOFS and record['author'] == 'author.py' and
          set(record['previews']['inspected']) == PREVIEWS,
          'Dialogue motion source, predecessor or proof inventory is not bounded to two actors')
    for relative, expected in record['proofs'].items():
        matches(here / relative, expected)
    matches(here / 'author.py', record['author_sha256'])
    for relative, expected in record['unchanged_source_files'].items():
        matches(directory / relative, expected)
    for relative, expected in record['sources'].items():
        matches(directory / relative, expected)
    native = load(directory / 'source-manifest.json')
    old_meta = {name: load(here / 'before' / (name+'.json')) for name in ACTORS}
    textures = {d['texture']: d['texture_sha256']
                for meta in old_meta.values() for d in meta['draws']}
    check(len(textures) == 24 and set(record['candidate_files']) == FILES | set(textures),
          'Dialogue animation revision adds or removes an actor or texture')
    for relative, expected in record['candidate_files'].items():
        matches(here / relative, expected)
        matches(directory / relative, expected)
    for relative, expected in textures.items():
        check(record['candidate_files'][relative] == expected,
              'Dialogue animation revision changes a native texture')
    for relative, expected in record['predecessor_files'].items():
        matches(here / 'before' / relative, expected)
    transform = record['room_transform_recommendation']
    check(transform == {'male': {'position': [.25, .058, -2.15], 'yaw_radians': math.atan2(1.2, -.9)},
                        'female': {'position': [1.45, .058, -3.05], 'yaw_radians': math.atan2(-1.2, .9)},
                        'phase_seconds': 'same for both', 'duration_seconds': 8.0},
          'Dialogue animation changes the agreed shared-room placement or phase')

    timelines = {}
    for name, n in ACTORS.items():
        before = old_meta[name]
        meta = load(directory / (name+'.json'))
        sex = name.removeprefix('conversing-')
        matches(Path(native[sex]['source']), native[sex]['source_sha256'])
        check(record['sources'][sex+'-selected.glb'] == native[sex]['selected_sha256'],
              name+': selected skin differs from the original native source')
        mutable = {'version', 'binary_sha256', 'source_manifest', 'frame_count', 'duration_seconds',
                   'sample_times', 'bounds_by_frame', 'joint_positions_by_frame'}
        additions = {'dialogue_timeline', 'phase_contract', 'loop_seam_max_error_m', 'feet'}
        check(set(meta) == set(before) | additions and
              all(meta[k] == v for k, v in before.items() if k not in mutable),
              name+': animation changes topology, draws, material response or an unrelated actor field')
        check(meta['name'] == name and meta['source_sex'] == sex and meta['version'] == 2 and
              meta['source_manifest'] == 'provenance.json' and meta['frame_count'] == 32 and
              meta['duration_seconds'] == 8.0 and meta['sample_times'] == [i/32 for i in range(32)] and
              meta['vertex_count'] == n and meta['stride_bytes'] == 48 and
              meta['frame_stride_bytes'] == n*48 and meta['loop'] is True and
              meta['binary'] == name+'.bin' and meta['loop_seam_max_error_m'] == 0 and
              len(meta['joint_positions_by_frame']) == len(meta['bounds_by_frame']) == 32,
              name+': frame layout, duration or cyclic animation contract changed')
        raw = (directory / meta['binary']).read_bytes()
        old_raw = (here / 'before' / before['binary']).read_bytes()
        check(hashlib.sha256(raw).hexdigest() == meta['binary_sha256'] and
              hashlib.sha256(old_raw).hexdigest() == before['binary_sha256'] and
              len(raw) == 32*n*48 and len(old_raw) == 4*n*48,
              name+': binary frame size or metadata digest is invalid')
        # UV and COLOR_0 bytes are checked in their original triangle-corner order.
        # This covers the topology of the non-indexed native triangle stream as
        # well as each material assignment, including repeated coincident corners.
        check(all(raw[(frame*n+i)*48+24:(frame*n+i+1)*48] == old_raw[i*48+24:(i+1)*48]
                  for frame in range(32) for i in range(n)),
              name+': UV, colour or native triangle-corner ordering changed')
        draws = meta['draws']
        check(sum(d['count'] for d in draws) == n and draws[0]['first'] == 0 and
              all(d['count'] > 0 and d['count'] % 3 == 0 for d in draws) and
              all(a['first']+a['count'] == b['first'] for a, b in zip(draws, draws[1:])),
              name+': material draws do not exactly cover the native triangle stream')
        vertices = list(struct.iter_unpack('<12f', raw))
        frames = [vertices[i*n:(i+1)*n] for i in range(32)]
        check(all(math.isfinite(x) for v in vertices for x in v) and
              all(abs(math.sqrt(sum(x*x for x in v[3:6]))-1) < 1e-5 for v in vertices),
              name+': animated positions or normals are invalid')
        check(all(0 <= x <= 1.01 for v in vertices for x in v[8:11]) and
              all(v[11] == 2 for v in vertices), name+': native material colour contract changed')
        for i, frame in enumerate(frames):
            bounds = [[min(v[a] for v in frame) for a in range(3)],
                      [max(v[a] for v in frame) for a in range(3)]]
            check(all(abs(bounds[b][a]-meta['bounds_by_frame'][i][b][a]) < 1e-6
                      for b in range(2) for a in range(3)) and abs(bounds[0][1]) < 1e-5 and
                  bounds[1][1] < 2.1,
                  name+': frame '+str(i)+' has incorrect bounds or loses contact with the floor')
        # Check skin vertices as well as author joint metadata: a rig-only claim
        # would not catch a moving, stretched or mis-exported visible sole.
        sole = [i for i, v in enumerate(frames[0]) if v[1] < .01]
        check(len(sole) >= 30 and all(math.dist(frames[0][i][:3], f[i][:3]) < 1e-5
                                     for f in frames for i in sole),
              name+': exported soles slide or detach from their fixed support')
        joints = meta['joint_positions_by_frame']
        feet = ('Lankle', 'Rankle', 'Lball', 'Rball')
        check(all(math.dist(joints[0][joint], frame[joint]) < 1e-5
                  for frame in joints for joint in feet),
              name+': one of the four sole support joints moves')
        check(all(abs(f[hand][0]) < .65 for f in joints for hand in ('Lhand', 'Rhand')),
              name+': the dialogue returns to a wide permanent arm pose')
        max_motion = max(math.dist(a[:3], b[:3]) for f in frames for a, b in zip(frames[0], f))
        steps = [max(math.dist(a[:3], b[:3]) for a, b in zip(frames[i], frames[(i+1)%32]))
                 for i in range(32)]
        check(.15 < max_motion < 1 and max(steps) < .5 and steps[-1] < .01,
              name+': dialogue has no visible motion, implausible displacement or a loop discontinuity')
        old_vertices = list(struct.iter_unpack('<12f', old_raw[:n*48]))
        old_areas = [area(*old_vertices[i:i+3]) for i in range(0, n, 3)]
        check(all(old_areas[i//3] <= 1e-7 or area(*frame[i:i+3]) >= 1e-8
                  for frame in frames for i in range(0, n, 3)),
              name+': revised pose collapses a previously valid native triangle')
        timeline = meta['dialogue_timeline']
        check(len(timeline) == 32 and all(set(row) == {'speaking_envelope', 'weight_shift_m', 'listening_nod'}
              and all(math.isfinite(v) for v in row.values()) and 0 <= row['speaking_envelope'] <= 1
              and abs(row['weight_shift_m']) <= .023 and 0 <= row['listening_nod'] <= 1
              for row in timeline), name+': dialogue cadence metadata is invalid')
        timelines[sex] = timeline
    male, female = timelines['male'], timelines['female']
    check(all(male[i]['speaking_envelope'] == 0 for i in range(16, 32)) and
          all(female[i]['speaking_envelope'] == 0 for i in range(16)) and
          max(row['speaking_envelope'] for row in male[:16]) == 1 and
          max(row['speaking_envelope'] for row in female[16:]) == 1 and
          all(a['speaking_envelope']*b['speaking_envelope'] == 0 for a, b in zip(male, female)),
          'Dialogue actors no longer alternate their gestures over the shared eight-second cycle')

    source_predecessors = {(directory/name).resolve(): (here/'before'/name).resolve() for name in FILES}
    runtime_predecessor = {}
    prefix = 'custom_assets/jak3/city-interiors/'
    for name, meta in old_meta.items():
        runtime_predecessor[prefix+name+'.json'] = hashlib.sha256(runtime_json(meta)).hexdigest()
        runtime_predecessor[prefix+name+'.bin'] = record['predecessor_files'][name+'.bin']
    return {'source_predecessors': source_predecessors,
            'runtime_predecessor_sha256': runtime_predecessor}


def main():
    here = Path(__file__).resolve().parent
    directory = here/'inhabitants'
    checks = []
    def check(condition, message):
        checks.append({'check': message, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(message)
    def matches(path, expected):
        check(Path(path).is_file() and sha(path) == expected, 'Pinned file: '+str(path))
    result = verify(directory, check, matches)
    report = {'status': 'passed', 'native_game_validation': False,
              'verifier_sha256': sha(Path(__file__)),
              'provenance_sha256': sha(directory/'motion-v2/provenance.json'),
              'method': 'Read-only float32 mesh, immutable predecessor and installed-source verification',
              'checks': checks,
              'source_predecessors': {str(k):str(v) for k,v in result['source_predecessors'].items()},
              'runtime_predecessor_sha256': result['runtime_predecessor_sha256']}
    (directory/'motion-v2/numeric-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'checks': len(checks),
                      'runtime_predecessor_sha256': result['runtime_predecessor_sha256']}, indent=2))


if __name__ == '__main__':
    main()
