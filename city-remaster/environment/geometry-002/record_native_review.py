"""Record the human-readable native observations and pin their actual assets."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHOTS = ROOT / 'profiles/remaster-palace/OpenGOAL/jak3/screenshots'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def proof(path):
    return {'path': str(path), 'sha256': sha(path)}


levels = {}
for level in ('wascitya', 'wascityb'):
    installed = read(HERE / (level + '-installed.json'))
    actual = ROOT / 'data' / installed['path']
    assert sha(actual) == installed['output_sha256']
    audit = read(HERE / (level + '-preservation.json'))
    assert audit['status'] == 'passed' and all(audit['checks'].values())
    levels[level] = {**proof(actual), 'preservation_checks': len(audit['checks']),
                     'installation': proof(HERE / (level + '-installed.json'))}

package_path = ROOT / 'models-v2/package-validation.json'
package = read(package_path)
assert package['passed'] and package['audio_mute_branch_logged']
report = {
    'date': '2026-09-17',
    'status': 'native_views_reviewed_with_scope_limits',
    'levels': levels,
    'engine': proof(ROOT / 'runtime/liquids-v3/gk.exe'),
    'package': proof(package_path),
    'package_checks': package['checks'],
    'audio': 'Native callback logs that every stereo sample is cleared before playback.',
    'captures': [
        {**proof(SHOTS / 'city-models-before-v1.png'), 'role': 'Before new geometry; ENV textures already installed.'},
        {**proof(SHOTS / 'city-models-after-v2.png'), 'role': 'Final WCA, matching fixed camera; visibly curved narrow grasses and intact dry streets.'},
        {**proof(SHOTS / 'city-facade-seam-diagnostic.png'), 'role': 'Rejected 001 facade inset seams; not an accepted result.'},
        {**proof(SHOTS / 'city-facade-seam-corrected-v2.png'), 'role': 'Final WCB, same diagnostic camera; dark inset bands absent, window openings and adjoining market/coast retained.'},
        {**proof(SHOTS / 'city-small-cactus-native-v1.png'), 'role': 'Native small cacti and grasses from 001; exact same vegetation patch SHA retained in 002. Large branching cactus remains original.'},
    ],
    'observations': [
        'Both WCA and WCB loaded and produced native screenshots on the final packaged runtime.',
        'Facade dark bands rejected in 001 are absent at the inspected WCB angle after restoring continuous wall panels.',
        'New roof coping is a restrained improvement; this is not a complete building reconstruction.',
        'New grasses change silhouettes at gameplay distance; small cactus cushions and flower petals are visible in volume.',
        'Existing glass and openings were not filled; no new populated interiors are claimed.',
        'Jak contact callback appears in the final runtime log; separate GPU report validates anchored roots and bounded recovery.',
        'Final camera restored to cam-string and normal wascitya-seem start, with game left running muted.',
    ],
    'short_update_rate_sample': {
        'method': 'Two read-only GOAL real-frame-clock integral counters and __read-ee-timer, 300 MHz.',
        'frames': [304285, 305849], 'ticks': [22773072000, 30597770400],
        'seconds': (30597770400 - 22773072000) / 300000000,
        'updates_per_second': (305849 - 304285) * 300000000 / (30597770400 - 22773072000),
        'limit': 'One stationary WCB view on RTX 3080 Ti; not GPU frame-time, 1% lows, or a whole-city benchmark.',
    },
    'limitations': [
        'Screenshots are observed views, not every building angle, collision or gameplay route.',
        'Grass native placements use the developer REPL; full manual traversal and NPC contact are not validated.',
        'Large branching cacti, complete houses, moving doors, interiors and remaining city flames are unfinished.',
        'Known screenshot OpenGL warning can occur while valid PNGs are written.',
        'The whole city, arena, desert and vehicles remain ongoing work.',
    ],
}
(HERE / 'native-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'checks': report['package_checks'], 'levels': list(levels)}))
