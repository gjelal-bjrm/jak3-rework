"""Reinstalle des fonctions de liquids-v3/fluids.glsl dans les shaders deja installes, sans rejouer
la chaine apply_materials.py (perimee : les shaders installes contiennent des ajouts posterieurs).

Usage : python liquids-v3/patch_fluid_functions.py lavaField shadeModernLava
Chaque fonction est remplacee, par nom, dans data/ et engine-src/ (tfrag3, generic, merc2, fountain),
puis les fichiers sont recopies dans variants/remaster par sync_variant.py.
"""
from pathlib import Path
import re, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
SHADERS = ['tfrag3.frag', 'generic.frag', 'merc2.frag', 'fountain.frag']
REL = 'game/graphics/opengl_renderer/shaders/'


def find(text, name):
    m = re.search(r'^\w+\s+' + re.escape(name) + r'\s*\(', text, re.M)
    if not m: return None
    i = text.index('{', m.end()); depth = 0
    for k in range(i, len(text)):
        depth += text[k] == '{'; depth -= text[k] == '}'
        if depth == 0: return m.start(), k + 1
    raise ValueError(name)


def main(names):
    source = (ROOT / 'liquids-v3/fluids.glsl').read_text()
    bodies = {}
    for name in names:
        span = find(source, name); assert span, f'{name} absent de fluids.glsl'
        bodies[name] = source[span[0]:span[1]]
    changed = []
    for shader in SHADERS:
        for root in (ROOT / 'data', ROOT / 'engine-src'):
            path = root / REL / shader; text = path.read_text(); before = text
            missing = []
            for name in names:
                span = find(text, name)
                if span: text = text[:span[0]] + bodies[name] + text[span[1]:]
                else: missing.append(name)
            for name in missing:   # nouvelle fonction : inseree avant la premiere fonction demandee deja presente
                anchors = [find(text, n) for n in names if n not in missing]
                anchors = [a for a in anchors if a]
                if not anchors: continue
                at = min(a[0] for a in anchors)
                text = text[:at] + bodies[name] + chr(10)*2 + text[at:]
            if text != before:
                path.write_text(text); changed.append(shader)
                print('patche :', path.relative_to(ROOT))
    if changed:
        subprocess.run([sys.executable, str(ROOT / 'sync_variant.py')] + [REL + s for s in sorted(set(changed))], check=True)


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1:])
