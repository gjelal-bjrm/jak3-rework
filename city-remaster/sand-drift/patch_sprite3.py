"""Accroche de la poussiere dans Sprite3.cpp : remplace le bloc de remaillage par une substitution de texture.
Idempotent : retire l'ancien bloc s'il existe, ajoute la substitution juste avant le glBindTexture du sprite."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
CPP = ROOT / 'engine-src/game/graphics/opengl_renderer/sprite/Sprite3.cpp'
SUB = '''    if (SandDrift::in_city(render_state) &&
        SandDrift::matches(render_state->texture_pool->get_debug_texture_name_from_tbp(tbp))) {
      // Poussiere de Spargus : sprite natif inchange, texture haute resolution.
      if (const GLuint hd = m_sand_drift.texture()) tex = u64(hd);
    }
'''


def main():
    text = CPP.read_text()
    # ancien bloc de remaillage (de "if (SandDrift::ENABLED" ou "if (SandDrift::in_city" avec m_sand_drift.render ... jusqu'a la fin du bloc)
    pattern = re.compile(r'    if \(SandDrift::(?:ENABLED && )?in_city\(render_state\) &&\n        SandDrift::matches\([^\n]*\n(?:(?!    std::optional<u64> tex;)[^\n]*\n)*?      if\(m_coastal_native_runs\.empty\(\)\)continue;\n    \}\n\n', re.M)
    text, removed = pattern.subn('', text)
    text = text.replace(SUB, '')
    anchor = '    glActiveTexture(GL_TEXTURE0);\n    glBindTexture(GL_TEXTURE_2D, *tex);\n'
    assert text.count(anchor) == 1, 'ancre glBindTexture introuvable'
    text = text.replace(anchor, SUB + anchor)
    CPP.write_text(text)
    print(f'Sprite3.cpp : {removed} bloc(s) de remaillage retire(s), substitution de texture en place')


if __name__ == '__main__': main()
