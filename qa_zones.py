"""Controle des zones : pour chaque scene, 4 vues depuis le point de reprise (nord, est, sud, ouest), jeu d'origine /
remaster cote a cote (qa_compare.py), controle des textures affichees et mesure de fluidite.

  python qa_zones.py desa desc dese ...        (scenes de launch.py)
Planches : qa/zone-<scene>-compare.png
"""
import re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent


def viewpoint(scene):
    text = (ROOT / 'launch.py').read_text(encoding='utf-8')
    if re.fullmatch(r'des[a-h]', scene):
        z = scene[-1]
        m = re.search(r"\('" + z + r"', ([-\d.]+), ([-\d.]+), ([-\d.]+)\)", text)
        return tuple(float(v) for v in m.groups())
    m = re.search(r"'" + scene + r"': \{[^}]*'viewpoint': \(([-\d.]+), ([-\d.]+), ([-\d.]+)\)", text)
    return tuple(float(v) for v in m.groups())


for scene in sys.argv[1:]:
    x, y, z = viewpoint(scene)
    eye = f'{x:.1f},{y + 6:.1f},{z:.1f}'
    views = [f'{eye}/{x + dx * 60:.1f},{y + 2:.1f},{z + dz * 60:.1f}' for dx, dz in ((0, 1), (1, 0), (0, -1), (-1, 0))]
    print(scene, views, flush=True)
    subprocess.run([sys.executable, '-u', str(ROOT / 'qa_compare.py'), scene, f'zone-{scene}'] + views, cwd=ROOT)
