"""Reproducible, area-limited shader patch against the untouched active install."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT.parents[1] / 'active/jak3/data'
DATA = ROOT / 'data'
shader_dir = Path('game/graphics/opengl_renderer/shaders')
helper = (ROOT / 'arena-lighting.glsl').read_text(encoding='utf-8')
changes = []
for shader in ('tfrag3', 'tie_wind', 'etie_base'):
    vert_path = shader_dir / (shader + '.vert')
    frag_path = shader_dir / (shader + '.frag')
    vert = (ORIGINAL / vert_path).read_text(encoding='utf-8')
    frag = (ORIGINAL / frag_path).read_text(encoding='utf-8')
    assert 'out float fogginess;' in vert and 'in float fogginess;' in frag
    assert 'color = fragment_color * T0;' in frag
    vert = vert.replace('out float fogginess;', 'out float fogginess;\nout vec3 arena_world;')
    vert = vert.replace('void main() {', 'void main() {\n  arena_world = position_in / 4096.0;')
    frag = frag.replace('in float fogginess;', 'in float fogginess;\nin vec3 arena_world;')
    frag = frag.replace('void main() {', helper + '\nvoid main() {\n  vec3 arena_light = arenaRelight(fragment_color.rgb, arena_world);')
    frag = frag.replace('color = fragment_color * T0;', 'color = vec4(arena_light, fragment_color.a) * T0;')
    for relative, text in ((vert_path, vert), (frag_path, frag)):
        (DATA / relative).write_text(text, encoding='utf-8')
        changes.append(str(relative))

mood_path = Path('goal_src/jak3/levels/wascity/wasstadium/wasstada-mood.gc')
mood = (ORIGINAL / mood_path).read_text(encoding='utf-8')
# Eight original time-of-day snapshots, retained in the original order.
# Rebalance morning key/ambient; nights remain readable and keep their identity.
keys = [(1.42,1.15,0.68),(1.48,1.29,0.98),(1.61,1.48,1.26),(1.48,1.29,0.98),
        (1.49,1.10,0.59),(0.39,0.39,0.63),(0.29,0.40,0.58),(0.33,0.40,0.42)]
fills = [(0.36,0.40,0.51),(0.34,0.43,0.56),(0.37,0.46,0.57),(0.34,0.43,0.56),
         (0.34,0.39,0.51),(0.29,0.35,0.42),(0.29,0.32,0.39),(0.30,0.33,0.39)]
def replace_vectors(text, field, values, w):
    iterator = iter(values)
    pattern = rf':{field} \(new \'static \'vector[^)]*\)'
    def value(match):
        x,y,z = next(iterator)
        return f":{field} (new 'static 'vector :x {x:.4f} :y {y:.4f} :z {z:.4f}" + (f' :w {w:.1f})' if w is not None else ')')
    text, count = re.subn(pattern, value, text)
    assert count == 8, (field, count)
    return text
mood = replace_vectors(mood, 'lgt-color', keys, None)
mood = replace_vectors(mood, 'amb-color', fills, 1.0)
(DATA / mood_path).write_text(mood, encoding='utf-8')
changes.append(str(mood_path))
(ROOT / 'lighting-files.json').write_text(json.dumps(changes, indent=2), encoding='utf-8')
print('Patched:', ', '.join(changes))
