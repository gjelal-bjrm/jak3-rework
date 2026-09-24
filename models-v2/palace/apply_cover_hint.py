"""Couverture floue des cascades natives du palais : dans tfrag3.frag (installe), avant l'appel a
shadeModernWater, on lit l'alpha de la texture d'origine a un niveau de mip eleve (fluidCoverHint) :
les fines lignes de la texture deviennent une nappe continue. Idempotent ; data/ et engine-src/, puis
sync_variant.py. La variable globale fluidCoverHint est declaree dans liquids-v3/fluids.glsl.
"""
from pathlib import Path
import subprocess, sys
R = Path(__file__).resolve().parents[2]
REL = 'game/graphics/opengl_renderer/shaders/tfrag3.frag'
OLD = '''    } else if (fluid_kind == 2) {
      color = vec4(shadeModernWater(arena_world,surface_normal,'''
NEW = '''    } else if (fluid_kind == 2) {
      fluidCoverHint = textureLod(tex_T0, tex_coord.xy, 3.5).a*fragment_color.a*2.0;   // couverture floue
      color = vec4(shadeModernWater(arena_world,surface_normal,'''


def main():
    for root in (R / 'data', R / 'engine-src'):
        path = root / REL; s = path.read_text()
        if NEW in s: print('deja patche :', path.relative_to(R)); continue
        assert s.count(OLD) == 1, 'appel de shadeModernWater introuvable'
        path.write_text(s.replace(OLD, NEW)); print('patche :', path.relative_to(R))
    subprocess.run([sys.executable, str(R / 'sync_variant.py'), REL], check=True)


if __name__ == '__main__': main()
