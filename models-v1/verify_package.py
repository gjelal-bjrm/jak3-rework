"""Check the deployed native model lot and guard the accepted effects."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = json.loads((ROOT / 'variant-files.json').read_text())
expected = json.loads((ROOT / 'variant-hashes.json').read_text())['remaster']
model = json.loads((HERE / 'native-model-validation.json').read_text())
allowed = {'out/jak3/fr3/waspala.fr3'} | {
    'game/graphics/opengl_renderer/shaders/' + name for name in (
        'tfrag3.vert', 'tfrag3.frag', 'tie_wind.vert', 'tie_wind.frag',
        'etie_base.vert', 'etie_base.frag', 'shrub.frag')}
changed = []
for relative in files:
    deployed = ROOT / 'data' / relative
    packaged = ROOT / 'variants/remaster' / relative
    assert sha(deployed) == sha(packaged) == expected[relative], relative
    old = ROOT / 'variants/remaster-before-objects' / relative
    assert old.is_file(), old
    if sha(old) != sha(packaged):
        changed.append(relative)
assert set(changed) <= allowed, changed
assert sha(ROOT / 'data/out/jak3/fr3/waspala.fr3') == model['output_sha256']
manifest = json.loads((ROOT / 'liquids-v3/runtime-manifest.json').read_text())
assert sha(ROOT / manifest['runtime']) == manifest['sha256']
assert all('rock' not in part['file'] for part in model['parts'])
screenshots = ROOT / 'profiles/remaster-palace/OpenGOAL/jak3/screenshots'
captures = {}
for name in ('brazier', 'throne', 'palms', 'rock-restored'):
    path = screenshots / ('objects-validated-' + name + '.png')
    assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), path
    captures[name] = {'path': str(path), 'sha256': sha(path)}
log = (ROOT / 'remaster-runtime.log').read_text(errors='replace')
fatal = [line for line in log.splitlines() if re.search(
    r'assertion failed|shader.*(?:compile|link).*failed|failed.*(?:compile|link).*shader|fatal error',
    line, re.I)]
assert not fatal, fatal
report = {
    'checked_utc': datetime.now(timezone.utc).isoformat(),
    'live_pid': int((ROOT / 'remaster.pid').read_text()),
    'packaged_and_deployed_files_matching': len(files),
    'changed_files_since_before_objects': changed,
    'protected_files_identical': len(files) - len(changed),
    'level_sha256': model['output_sha256'],
    'runtime_sha256': manifest['sha256'],
    'experimental_rock_excluded': True,
    'captures': captures,
    'fatal_shader_or_assertion_errors': fatal,
    'known_log_limitations': [
        'The native screenshot path reports GL_INVALID_OPERATION 0x502 while producing valid PNGs.',
        'No complete frame-time benchmark or full-room collision audit was performed.'
    ],
    'visual_review': {
        'brazier': 'Continuous bowl and lip; raised ornaments follow the curved body; flame base meets the fuel surface.',
        'throne': 'Frame, cushion and rivets load with their original motifs and proportions.',
        'palms': 'Rounded planter and curved fronds load; hanging plants are outside this lot.',
        'room_complete': False
    }
}
(HERE / 'package-validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: report[k] for k in (
    'packaged_and_deployed_files_matching', 'protected_files_identical',
    'changed_files_since_before_objects', 'experimental_rock_excluded')}, indent=2))
