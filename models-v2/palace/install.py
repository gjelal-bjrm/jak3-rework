"""Eau du palais v2 : chutes du plafond (fountain.frag, main remplace) et voile de brume (fountain_mist.*).

- fountain.frag installe (data/ et engine-src/) : la fonction main est remplacee par fountain_main.glsl ;
  les fonctions d'eau partagees restent celles de liquids-v3/fluids.glsl (patch_fluid_functions.py) ;
- fountain_mist.vert/.frag : ecrits dans data/, engine-src/ et les trois variantes (empreintes), avec les
  positions des chutes (liquids-v3/fountain_positions.glsl) ;
- puis sync_variant.py pour fountain.frag.
Verifier avant : data/ doit contenir la variante remaster (python launch.py remaster --prepare-only).
"""
from pathlib import Path
import hashlib, json, subprocess, sys
H = Path(__file__).resolve().parent; R = H.parents[1]
REL = 'game/graphics/opengl_renderer/shaders/'


def main():
    tfrag = (R / 'data' / REL / 'tfrag3.frag').read_text()
    assert 'shadeModernWater' in tfrag, 'data/ ne contient pas la variante remaster : lancer launch.py remaster --prepare-only'
    new_main = (H / 'fountain_main.glsl').read_text(encoding='utf-8')
    for root in (R / 'data', R / 'engine-src'):
        path = root / REL / 'fountain.frag'
        s = path.read_text()
        at = s.index('void main() {')
        comment = s.rfind('\n// Chutes du plafond du palais', 0, at)
        if comment >= 0: at = comment + 1
        path.write_text(s[:at] + new_main)
        print('fountain.frag :', path.relative_to(R))
    positions = (R / 'liquids-v3/fountain_positions.glsl').read_text()
    files = json.loads((R / 'variant-files.json').read_text(encoding='utf-8'))
    hashes = json.loads((R / 'variant-hashes.json').read_text(encoding='utf-8'))
    falls = (H / 'palace_falls.glsl').read_text(encoding='utf-8')
    for name in ('fountain_mist.vert', 'fountain_mist.frag'):
        text = (H / name).read_text(encoding='utf-8').replace('// FOUNTAIN_POSITIONS', positions)
        text = text.replace('// PALACE_FALLS', falls)
        rel = REL + name
        for root in (R / 'data', R / 'engine-src'):
            (root / rel).write_text(text)
        for variant in ('original', 'remaster-v1', 'remaster'):
            target = R / 'variants' / variant / rel
            target.write_text(text)
            hashes.setdefault(variant, {})[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
        if rel not in files: files.append(rel)
        print('installe :', rel)
    (R / 'variant-files.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
    (R / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    # Gerbes (water_spray.vert) : grands impacts, pieds des petites chutes et pieds d'origine.
    spray = (H / 'spray_impacts.glsl').read_text(encoding='utf-8')
    for root in (R / 'data', R / 'engine-src'):
        path = root / REL / 'water_spray.vert'
        text = path.read_text()
        start = text.index('const int water_impact_count=')
        end = text.index(');\n', text.index('const vec3 water_impacts[', start)) + 3
        path.write_text(text[:start] + spray + text[end:])
    subprocess.run([sys.executable, str(R / 'sync_variant.py'), REL + 'fountain.frag', REL + 'water_spray.vert'],
                   check=True)


if __name__ == '__main__': main()
