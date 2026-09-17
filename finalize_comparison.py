"""Package real engine captures and verify the installed A/B assets."""
from pathlib import Path
from PIL import Image
from io import BytesIO
import base64
import hashlib
import json

ROOT = Path(__file__).resolve().parent
ACTIVE = ROOT.parents[1] / 'active/jak3/data'
OUTPUT = Path('C:/Users/Gjelal/.codex/visualizations/2026/09/15/01a0a501-7cc7-7072-9c65-4e16af3cef4d/spargus-avant-apres.html')
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

expected = json.loads((ROOT / 'variant-hashes.json').read_text())
for variant, files in expected.items():
    for relative, checksum in files.items():
        assert digest(ROOT / 'variants' / variant / relative) == checksum, relative
        if variant == 'original':
            assert digest(ACTIVE / relative) == checksum, f'Original changed: {relative}'
        if variant == 'remaster':
            assert digest(ROOT / 'data' / relative) == checksum, f'Remaster not installed: {relative}'

fragment = (ROOT / 'comparison/compare-template.html').read_text(encoding='utf-8')
captures = {}
for variant in ('original', 'remaster'):
    source = ROOT / 'comparison' / f'arena-{variant}.png'
    with Image.open(source) as capture:
        assert capture.size == (1920, 1080)
        stream = BytesIO()
        capture.convert('RGB').resize((1280, 720), Image.Resampling.LANCZOS).save(stream, format='JPEG', quality=85, optimize=True)
        data = 'data:image/jpeg;base64,' + base64.b64encode(stream.getvalue()).decode('ascii')
        fragment = fragment.replace(f'{variant.upper()}_IMAGE', data)
        captures[variant] = {'file': str(source), 'size': list(capture.size), 'sha256': digest(source)}
assert len(fragment.encode('utf-8')) < 1_000_000
assert 'ORIGINAL_IMAGE' not in fragment and 'REMASTER_IMAGE' not in fragment
OUTPUT.write_text(fragment, encoding='utf-8')
report = {
    'date': '2026-09-16',
    'runtime': 'OpenGOAL v0.3.6',
    'checkpoint': 'game-start',
    'time_of_day': '09:00:00 frozen in both variants',
    'captures': captures,
    'capture_method': 'Built-in pc-screen-shot; no artistic editing or color correction',
    'limitations': ['Particles and lava animation are not deterministic between launches.',
                    'The native screenshot function logs GL_INVALID_OPERATION in both original and remaster, but produces valid PNGs.',
                    'Validated startup and rendered frame; full tutorial playthrough and performance benchmark not performed.'],
    'checks': {'variant_hashes': 'passed', 'original_install_matches_snapshot': 'passed',
               'remaster_variant_installed': 'passed', 'capture_dimensions': 'passed'},
    'inline_comparison': str(OUTPUT),
}
(ROOT / 'validation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'comparison_bytes': OUTPUT.stat().st_size, 'validation': report['checks']}, indent=2))
