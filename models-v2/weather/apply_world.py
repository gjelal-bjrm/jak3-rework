"""Meteo sur le decor dans le shader de terrain (tfrag3.frag) installe : sol mouille, flaques, ronds de
pluie, neige au sol (weather_world.glsl).

Patch idempotent entre les marqueurs WEATHER_WORLD_BEGIN / WEATHER_WORLD_END, applique a data/ et
engine-src/, puis recopie dans variants/remaster (empreintes) par sync_variant.py.
"""
from pathlib import Path
import re, subprocess, sys
H = Path(__file__).resolve().parent; R = H.parents[1]
REL = 'game/graphics/opengl_renderer/shaders/tfrag3.frag'
BEGIN, END = '// WEATHER_WORLD_BEGIN', '// WEATHER_WORLD_END'
CALL = '    color.rgb=weatherSurface(color.rgb,arena_light,arena_world,surface_normal);   // meteo\n'


def patch(text):
    text = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n', '', text, flags=re.S)
    text = text.replace(CALL, '')
    anchor = '    color.rgb=beachWetSand(color.rgb,arena_world);   // plage de Spargus\n'
    assert text.count(anchor) == 1, 'appel du sable mouille introuvable (lancer models-v2/shore/apply_beach.py)'
    text = text.replace(anchor, anchor + CALL)
    marker = '\nvoid main() {'
    assert text.count(marker) == 1
    block = BEGIN + '\n' + (H / 'weather_world.glsl').read_text(encoding='utf-8') + END + '\n'
    return text.replace(marker, '\n' + block + marker)


def main():
    for root in (R / 'data', R / 'engine-src'):
        path = root / REL
        path.write_text(patch(path.read_text()))
        print('patche :', path.relative_to(R))
    subprocess.run([sys.executable, str(R / 'sync_variant.py'), REL], check=True)


if __name__ == '__main__': main()
