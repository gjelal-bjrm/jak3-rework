"""Correct the basin's underside without regenerating accepted room materials.

The canonical helper is fluids.glsl. Its complete shader generator also rebuilds
older scenery code, so this patch updates only the two bounded water expressions
in the canonical helper and the three currently installed shader variants.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SHADERS = Path('game/graphics/opengl_renderer/shaders')
NORMAL_OLD = '  vec3 projectedOffset = fluidProject(P+vec3(N.x,0.0,N.z)*0.16);'
NORMAL_NEW = '''  // The basin is visible from both sides. Preserve the accepted upper face;
  // only its underside needs the normal oriented toward the submerged camera.
  bool belowSurface = cam_trans.y/4096.0 < P.y;
  if (belowSurface && dot(N,V)<0.0) N = -N;
''' + NORMAL_OLD
PATH_OLD = '  float thickness = min(length(fluidUnproject(refractUV,z)-P),3.0);'
PATH_NEW = PATH_OLD + '''
  // From below, the submerged segment ends at the surface. The remaining ray
  // goes through air; a distant wall must not add metres of water absorption.
  if (belowSurface) thickness = min(length(cam_trans.xyz/4096.0-P),3.0);'''


def without_underwater_fix(source):
    """Strict inverse for validating protected baseline shader differences."""
    for old, new in ((NORMAL_OLD, NORMAL_NEW), (PATH_OLD, PATH_NEW)):
        assert source.count(new) == 1, 'Missing or modified underwater correction'
        source = source.replace(new, old, 1)
    return source


def with_underwater_fix(source):
    for old, new in ((NORMAL_OLD, NORMAL_NEW), (PATH_OLD, PATH_NEW)):
        if new in source:
            assert source.count(new) == 1
        else:
            assert source.count(old) == 1, 'Water source differs from expected helper'
            source = source.replace(old, new, 1)
    return source


def main():
    paths = [ROOT / 'liquids-v3/fluids.glsl'] + [
        ROOT / tree / SHADERS / name
        for tree in ('data', 'engine-src')
        for name in ('generic.frag', 'merc2.frag', 'tfrag3.frag')
    ]
    changes = []
    # Validate every target before writing any file. Inverting the correction
    # proves that no unrelated material/effect code has changed in this patch.
    for path in paths:
        before = path.read_bytes()
        newline = '\r\n' if b'\r\n' in before else '\n'
        text = before.decode('utf-8').replace('\r\n', '\n')
        updated = with_underwater_fix(text)
        original = without_underwater_fix(updated)
        assert original == text or updated == text
        after = updated.replace('\n', newline).encode('utf-8')
        changes.append((path, before, after))
    for path, _, after in changes:
        path.write_bytes(after)
    report = {
        'purpose': 'Underside normal orientation and camera-to-surface absorption path only',
        'above_water_expressions_preserved': True,
        'fire_shape_unchanged': True,
        'full_snell_refraction': False,
        'protected_shader_exceptions': ['generic.frag', 'merc2.frag', 'tfrag3.frag'],
        'validation': 'Remove exactly NORMAL_NEW/PATH_NEW with without_underwater_fix before comparing the protected baseline; no general shader exception is needed.',
        'files': [{
            'path': path.relative_to(ROOT).as_posix(),
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
        } for path, before, after in changes],
    }
    (ROOT / 'liquids-v3/underwater-fix.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Updated canonical water helper and six installed shader files; two expressions only.')


if __name__ == '__main__':
    main()
