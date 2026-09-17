"""Gouttes de lave de l'arene : retrouver la lisibilite de l'original (grosses gouttes jaune-orange qui
jaillissent du lac) avec un rendu plus fin. Codex les avait reduites a des points gris (v3).

Modifie data/goal_src/.../wasstada-obs.gc (parts 1928 sploop, 1929 sploop-box) et wasstada-part.gc
(1930 geyser-sploop, 1931 jets du geyser, 1932 vapeur). Idempotent.
- Notre lave ecrit la profondeur (necessaire au bloom) alors que l'originale etait un plan transparent :
  les gouttes, qui naissent sous la surface, etaient invisibles. Elles naissent maintenant 1,2 m plus haut.
- La vapeur 1932 (sprite dirtpuff01 recolore en gris) faisait des taches grises sur la lave : retiree.
Recompiler ensuite : python liquids-v3/compile_iso.py puis python sync_variant.py out/jak3/iso/WASSTADA.DGO
"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
FILES = {'wasstada-obs.gc': (1928, 1929), 'wasstada-part.gc': (1930, 1931)}
SETTINGS = {   # champ -> nouvelle valeur (texte GOAL), par particule
    1928: {'num': '(:num 2.0 8.0)', 'scale-x': '(:scale-x (meters 0.22) (meters 0.7))'},
    1929: {'num': '(:num 0.1 0.5)', 'scale-x': '(:scale-x (meters 0.18) (meters 0.6))'},
    1930: {'num': '(:num 4.0 9.0)', 'scale-x': '(:scale-x (meters 0.22) (meters 0.7))'},
    1931: {'num': '(:num 1.5 2.5)', 'scale-x': '(:scale-x (meters 0.14) (meters 0.24))', 'scale-y': '(:scale-y (meters 0.28) (meters 0.42))'},
}
COLOR = {'r': '(:r 255.0)', 'g': '(:g 120.0 40.0)', 'b': '(:b 20.0)', 'fade-g': '(:fade-g -0.25)', 'fade-b': '(:fade-b -0.10)', 'fade-a': '(:fade-a -0.35)'}
LIFT = {1928: '(:y (meters 1.2))', 1929: '(:y (meters 1.2))', 1930: '(:y (meters 1.2))'}
FIELD = r'\(:%s [^()]*(?:\([^()]*\)[^()]*)*\)'


def patch_block(block, settings):
    for field, value in {**COLOR, **settings}.items():
        block, n = re.subn(FIELD % re.escape(field), value, block, count=1)
        if n == 0 and field.startswith('fade'):
            block = block.replace('    (:accel-y', '    ' + value + '\n    (:accel-y', 1)   # fondus absents dans l'original : ajoutes
    return block


def lift(block, part):
    if part not in LIFT: return block
    block = re.sub(r'\n    \(:y \(meters [^)]*\)\)', '', block)
    # les champs suivent l'ordre des identifiants sparticle : :y se place entre :x et :z
    return re.sub(r'(\n    \(:x [^\n]*\))', lambda m: m.group(1) + '\n    ' + LIFT[part], block, count=1)


def block_span(text, part):
    start = text.index(f'(defpart {part}\n'); end = text.index('\n  )\n', start) + 5
    return start, end


def main():
    for name, parts in FILES.items():
        path = ROOT / 'data/goal_src/jak3/levels/wascity/wasstadium' / name
        text = path.read_text()
        for part in parts:
            start, end = block_span(text, part)
            text = text[:start] + lift(patch_block(text[start:end], SETTINGS[part]), part) + text[end:]
        if name == 'wasstada-part.gc':
            # 1932 vapeur grise ; 1934 sprite de distorsion thermique (revele l'image d'avant la lave dans notre
            # moteur : tache gris-vert). Le shader de lave a deja son propre miroitement (bloom).
            for part in (1932, 1934):
                start, end = block_span(text, part)
                text = text[:start] + re.sub(FIELD % 'num', '(:num 0.0 0.0)', text[start:end], count=1) + text[end:]
        path.write_text(text); print('patche :', path.relative_to(ROOT), parts, '+ vapeur 1932 retiree' if name.endswith('part.gc') else '')


if __name__ == '__main__': main()
