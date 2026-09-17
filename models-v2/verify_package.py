"""Read-only checks of the packaged V2 models and regional ocean prototype.

Run after packaging and launching the final remaster build. The only output
written is models-v2/package-validation.json; this never starts or alters a game.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHADERS = 'game/graphics/opengl_renderer/shaders/'
MODEL_CHANGES = {'out/jak3/fr3/waspala.fr3'} | {
    SHADERS + name for name in (
        'tfrag3.vert', 'tfrag3.frag', 'tie_wind.vert', 'tie_wind.frag',
        'etie_base.vert', 'etie_base.frag', 'shrub.vert', 'shrub.frag')}
OCEAN_ADDITIONS = {SHADERS + name for name in (
    'ocean_common.frag', 'direct_basic_textured.frag',
    'modern_ocean_surface.vert', 'modern_ocean_surface.frag',
    'ocean_underwater.vert', 'ocean_underwater.frag',
    'coast_spray.vert', 'coast_spray.frag',
    'coast_breaker.vert', 'coast_breaker.frag')}
CITY_ADDITIONS = {'out/jak3/fr3/wascitya.fr3', 'out/jak3/fr3/wascityb.fr3', 'out/jak3/fr3/waswide.fr3'}
CITY_SHADER_ADDITIONS = {SHADERS + name for name in (
    'market_fruit.vert', 'market_fruit.frag', 'spargus_clouds.vert', 'spargus_clouds.frag',
    'city_fire.vert', 'city_fire.frag', 'city_fire_lighting.vert', 'city_fire_lighting.frag',
    'city_fire_embers.vert', 'city_fire_embers.frag')}
CITY_GOAL_ADDITIONS = {'out/jak3/iso/WWD.DGO'}
REQUIRED_PROTECTED = {'out/jak3/iso/WASPALA.DGO', 'out/jak3/iso/WASSTADA.DGO'} | {
    SHADERS + name for name in (
        'generic.frag', 'merc2.frag', 'merc2.vert',
        'liquid_bloom.vert', 'liquid_bloom.frag',
        'water_spray.vert', 'water_spray.frag', 'fountain.vert', 'fountain.frag',
        'palace-shore.bin', 'palace_fire.vert', 'palace_fire.frag',
        'fire_lighting.vert', 'fire_lighting.frag', 'fire_embers.vert', 'fire_embers.frag')}
UNDERWATER_PROTECTED = {SHADERS + name for name in ('generic.frag', 'merc2.frag')}


def underwater_inverse():
    # This module has no import-time writes. Its strict inverse recognizes only
    # the two documented insertions, not arbitrary changes to protected shaders.
    path = ROOT / 'liquids-v3/apply_underwater.py'
    spec = importlib.util.spec_from_file_location('palace_underwater_fix', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.without_underwater_fix


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    # Foliage patches exceed 1 GB. Stream hashes rather than loading them in RAM.
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    errors = []
    checks = 0
    city_descendants = []

    def check(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    def matches(path, expected):
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if not path.is_file():
            check(False, f'Missing file: {label}')
            return False
        actual = sha(path)
        check(actual == expected, f'Hash mismatch: {label}')
        return actual == expected

    files = load(ROOT / 'variant-files.json')
    hashes = load(ROOT / 'variant-hashes.json')
    model = load(ROOT / 'models-v1/native-model-validation.json')
    manifest = load(ROOT / 'liquids-v3/runtime-manifest.json')
    city_proof_path = ROOT / 'city-remaster/verify_descendants.py'
    spec = importlib.util.spec_from_file_location('city_descendant_proof', city_proof_path)
    city_proof = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(city_proof)
    grass_predecessors = city_proof.verify_grass_sources(check, matches)
    interior_additions, interior_predecessors = city_proof.verify_city_interiors(check, matches)
    check(len(files) == len(set(files)), 'Duplicate variant file entries')
    check(all(not Path(rel).is_absolute() and '..' not in Path(rel).parts for rel in files),
          'Variant paths must be relative and remain inside the prototype')
    if errors:
        raise ValueError('; '.join(errors))
    check(set(hashes) == {'original', 'remaster-v1', 'remaster'},
          'Unexpected or missing variant hash manifest')
    for variant, expected in hashes.items():
        check(set(expected) == set(files), f'Incomplete file list for {variant}')
        for relative in files:
            if relative in expected:
                matches(ROOT / 'variants' / variant / relative, expected[relative])

    active = (ROOT / 'current-variant.txt').read_text().strip()
    check(active == 'remaster', f'Expected the final remaster to be deployed, got {active}')
    for relative in files:
        if relative in hashes['remaster']:
            matches(ROOT / 'data' / relative, hashes['remaster'][relative])

    baseline = ROOT / 'variants/remaster-before-objects'
    previous = {p.relative_to(baseline).as_posix(): p for p in baseline.rglob('*') if p.is_file()}
    check(bool(previous), 'Missing pre-model baseline')
    check(REQUIRED_PROTECTED <= set(previous), 'Missing protected palace effect baseline')
    check(set(previous) <= set(files), 'A pre-model variant file was removed from the manifest')
    additions = sorted(set(files) - set(previous))
    check(set(additions) <= OCEAN_ADDITIONS | CITY_ADDITIONS | CITY_SHADER_ADDITIONS | CITY_GOAL_ADDITIONS | interior_additions, f'Unexpected new files: {additions}')
    if CITY_GOAL_ADDITIONS & set(files):
        contact = load(ROOT / 'city-remaster/fruit-contact-installed.json')
        path = ROOT / 'city-remaster/register_fruit_contact.py'
        spec = importlib.util.spec_from_file_location('market_contact_validation', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = module.objects(Path(contact['original_path']))
        after = module.objects(ROOT / 'data' / contact['path'])
        check(list(before) == list(after) and
              [name for name in before if before[name] != after.get(name)] == ['ctymark-obs'],
              'WWD rebuild modified objects beyond the market fruit controller')
        check(contact['before_objects'] == before and contact['after_objects'] == after,
              'WWD fruit preservation record no longer matches the binaries')
        matches(Path(contact['original_path']), contact['baseline_sha256'])
        for variant in ('original', 'remaster-v1'):
            matches(ROOT / 'variants' / variant / contact['path'], contact['baseline_sha256'])
        matches(ROOT / 'data' / contact['path'], contact['output_sha256'])
    if CITY_ADDITIONS & set(files):
        city = load(ROOT / 'city-remaster/installed.json')
        check(bool(city['levels']) and {e['path'] for e in city['levels']} <= CITY_ADDITIONS,
              'Untracked city replacement levels')
        heads = {entry['path']: entry['output_sha256'] for entry in city['levels']}
        city_descendants = city_proof.verify_city_chain(heads, check, matches)
        for entry in city['levels']:
            for variant in ('original', 'remaster-v1'):
                matches(ROOT / 'variants' / variant / entry['path'], entry['original_sha256'])
            matches(Path(entry['original_path']), entry['original_sha256'])
            matches(Path(entry['candidate_path']), entry['output_sha256'])
            preservation = load(Path(entry['preservation_report']))
            check(preservation['status'] == 'passed' and all(preservation['checks'].values()) and
                  preservation['current_static_sha256'] == preservation['candidate_static_sha256'],
                  'Unrelated city content was changed by Merc extraction')
        for relative, output_sha in heads.items():
            matches(ROOT / 'data' / relative, output_sha)
            matches(ROOT / 'variants/remaster' / relative, output_sha)
        for model_entry in city['models']:
            matches(Path(model_entry['path']), model_entry['sha256'])
            matches(Path(model_entry['replacement_path']), model_entry['sha256'])
        stage = load(Path(city['stage_report']))
        check(stage['status'] == 'passed' and stage['protected_hashes_unchanged'] and
              stage['merc_replacement_confirmed_by_extractor'], 'City import checks failed')
    if (ROOT / 'city-remaster/static-installed.json').exists():
        city_proof.verify_wind_frame(check, matches, grass_predecessors)
        wind = load(ROOT / 'city-remaster/shrub-wind-manifest.json')
        spec = importlib.util.spec_from_file_location('market_shrub_wind_check', ROOT / 'city-remaster/apply_shrub_wind.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for entry in wind['files']:
            path = grass_predecessors.get(entry['path'], ROOT / entry['path'])
            matches(path, entry['after_sha256'])
            raw_shader = path.read_bytes()
            newline = '\r\n' if b'\r\n' in raw_shader else '\n'
            restored = module.without_market_shrub_wind(raw_shader.decode('utf-8').replace('\r\n', '\n'))
            restored_bytes = restored.replace('\n', newline).encode('utf-8')
            check(hashlib.sha256(restored_bytes).hexdigest() == entry['before_sha256'],
                  'City shrub wind changed the previously accepted palace shader path')
    if (ROOT / 'city-remaster/spargus-clouds-manifest.json').exists():
        city_proof.verify_cloud_sources(check, matches)
    undo_underwater = underwater_inverse()
    changed, protected, underwater_preserved = [], [], []
    for relative, old in sorted(previous.items()):
        packaged = ROOT / 'variants/remaster' / relative
        if not packaged.is_file():
            continue
        if sha(old) != sha(packaged):
            changed.append(relative)
            if relative in UNDERWATER_PROTECTED:
                # read_text normalizes CRLF/LF on both sides. Every character
                # outside the two exact insertions must still match the baseline.
                try:
                    restored = undo_underwater(packaged.read_text(encoding='utf-8-sig'))
                    original = old.read_text(encoding='utf-8-sig')
                    bounded = restored == original
                except AssertionError:
                    bounded = False
                check(bounded, f'Unexpected palace underwater shader change: {relative}')
                if bounded:
                    underwater_preserved.append({
                        'path': relative,
                        'baseline_sha256': sha(old),
                        'packaged_sha256': sha(packaged),
                        'strict_inverse_matches_baseline': True,
                        'comparison': 'Full shader text after exact inverse; only CRLF/LF normalized',
                    })
            else:
                check(relative in MODEL_CHANGES, f'Protected baseline changed: {relative}')
        elif relative not in MODEL_CHANGES:
            protected.append(relative)
    accounted = set(protected) | {entry['path'] for entry in underwater_preserved}
    check(REQUIRED_PROTECTED <= accounted, 'Accepted palace effects or DGO files changed')

    underwater_manifest_path = ROOT / 'liquids-v3/underwater-fix.json'
    underwater_manifest = load(underwater_manifest_path)
    underwater_files = {'liquids-v3/fluids.glsl'} | {
        tree + '/' + SHADERS + name
        for tree in ('data', 'engine-src')
        for name in ('generic.frag', 'merc2.frag', 'tfrag3.frag')}
    entries = underwater_manifest['files']
    check(len(entries) == len(underwater_files) and
          {entry['path'] for entry in entries} == underwater_files,
          'Unexpected or missing underwater fix manifest entries')
    for entry in entries:
        if entry['path'] in underwater_files:
            matches(ROOT / entry['path'], entry['after_sha256'])

    matches(ROOT / 'data/out/jak3/fr3/waspala.fr3', model['output_sha256'])
    matches(Path(model['output']), model['output_sha256'])
    matches(Path(model['source']), model['source_sha256'])
    parts = load(ROOT / 'models-v1/model-set.json')['parts']
    check(parts == [part['file'] for part in model['parts']], 'Model set differs from the native report')
    for part in model['parts']:
        matches(ROOT / 'models-v1' / part['file'], part['sha256'])
    check(model['fuel_faces_exactly_preserved'] == 288, 'Fuel face preservation count differs')
    check(model['overlapping_replacements'] == 0, 'Overlapping native model replacements')
    check(model['removed_triangles'] == sum(p['removed'] for p in model['parts']), 'Removed triangle total differs')
    check(model['added_triangles'] == sum(p['added'] for p in model['parts']), 'Added triangle total differs')

    matches(ROOT / manifest['runtime'], manifest['sha256'])
    matches(ROOT / 'engine-build/bin/Release/gk.exe', manifest['sha256'])
    for scene, expected in manifest['routes'].items():
        matches(ROOT / 'routes/remaster' / scene / 'GAME.CGO', expected)
    scene = (ROOT / 'current-scene.txt').read_text().strip()
    check(scene in manifest['routes'], f'Untracked deployed route: {scene}')
    if scene in manifest['routes']:
        matches(ROOT / 'data/out/jak3/iso/GAME.CGO', manifest['routes'][scene])

    city_fire_successor = None
    if (ROOT / 'city-remaster/city-fire-v2/installed.json').exists():
        path = ROOT / 'city-remaster/city-fire-v2/register.py'
        spec = importlib.util.spec_from_file_location('city_fire_archive_proof', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        city_fire_successor = module.verify_installed(check, matches)
    grass_successor = None
    if (ROOT / 'city-remaster/grass-contact/installed.json').exists():
        path = ROOT / 'city-remaster/grass-contact/register.py'
        spec = importlib.util.spec_from_file_location('grass_contact_archive_proof', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        grass_successor = module.verify_installed(check, matches, city_fire_successor)
    if (ROOT / 'city-remaster/sand-steps/installed.json').exists():
        path = ROOT / 'city-remaster/sand-steps/register.py'
        spec = importlib.util.spec_from_file_location('sand_step_archive_proof', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.verify_installed(check, matches, grass_successor)

    log = (ROOT / 'remaster-runtime.log').read_text(errors='replace')
    fatal = [line for line in log.splitlines() if re.search(
        r'assertion failed|shader.*(?:compile|link).*failed|failed.*(?:compile|link).*shader|fatal error',
        line, re.I)]
    check(not fatal, 'Fatal shader, link or assertion message in the runtime log')
    muted_message = 'Prototype test audio: muted output; every stereo sample is cleared before playback'
    check(muted_message in log, 'Current runtime log does not confirm the engine audio mute path')
    launch = (ROOT / 'launch.py').read_text()
    check("environment['OPENGOAL_TEST_MUTE'] = '1'" in launch and 'env=environment' in launch,
          'Launch no longer passes the prototype mute environment')

    # Captures are evidence that assets loaded, not an automated visual score.
    screenshots = ROOT / 'profiles/remaster-palace/OpenGOAL/jak3/screenshots'
    captures = {}
    for name in ('objects-v2-throne', 'objects-v2-palms', 'objects-v2-hanging'):
        path = screenshots / (name + '.png')
        if path.is_file():
            with path.open('rb') as handle:
                check(handle.read(8) == b'\x89PNG\r\n\x1a\n', f'Invalid PNG: {name}')
            captures[name] = {'path': str(path), 'sha256': sha(path)}
        else:
            check(False, f'Missing native model capture: {name}')

    report = {
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'passed': not errors, 'checks': checks, 'errors': errors,
        'files_per_variant': len(files), 'variants_checked': sorted(hashes),
        'deployed_variant': active, 'deployed_route': scene,
        'changed_since_before_objects': changed, 'added_ocean_files': additions,
        'city_descendant_chain': city_descendants,
        'protected_files_identical': protected,
        'protected_files_preserved_except_bounded_underwater_fix': underwater_preserved,
        'underwater_fix_manifest': {
            'path': underwater_manifest_path.relative_to(ROOT).as_posix(),
            'sha256': sha(underwater_manifest_path),
            'scope': 'Underside normal orientation and camera-to-surface absorption path',
            'visual_validation_inferred': False,
        },
        'level_sha256': model['output_sha256'], 'runtime_sha256': manifest['sha256'],
        'model_triangles_all_lods': {'removed': model['removed_triangles'], 'added': model['added_triangles']},
        'fuel_faces_exactly_preserved': model['fuel_faces_exactly_preserved'],
        'audio_mute_branch_logged': muted_message in log,
        'fatal_shader_or_assertion_errors': fatal, 'native_model_captures': captures,
        'limitations': [
            'Hash checks establish package consistency, not visual quality or complete gameplay compatibility.',
            'Palace effects use byte comparisons except the two exact underwater insertions in Generic/Merc; their strict inverse must match the complete protected baseline text. Shared engine behavior is not proven by these checks.',
            'No automated acoustic capture or complete frame-time/collision/cutscene audit.',
            'Native screenshots may log GL_INVALID_OPERATION 0x502 while producing valid PNGs.',
            'Idle swimming ripple visual approval is not inferred by this validator.',
            'The complete city, arena, desert and vehicle remaster remains unfinished.'
        ]
    }
    (HERE / 'package-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in (
        'passed', 'checks', 'files_per_variant', 'variants_checked', 'audio_mute_branch_logged', 'errors')}, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
