"""Particules des petites chutes du palais (rubans 2705 et gouttes 2706 de group-waspala-waterfall-top) :
coupees, les nappes d'eau en geometrie (palace_cascade) les remplacent. Patch idempotent de
data/goal_src/.../waspala-part.gc, puis compilation de WASPALA.DGO et synchronisation de la variante.
"""
from pathlib import Path
import subprocess, sys
R = Path(__file__).resolve().parents[2]
PATH = R / 'data/goal_src/jak3/levels/wascity/palace/waspala-part.gc'


def block(s, n):
    start = s.index(f'(defpart {n}\n'); end = s.index('\n(defpart', start + 1)
    return start, end


def main():
    s = PATH.read_text()
    changed = False
    for n, old in ((2705, '(:num 1.0)'), (2706, '(:num 0.8)')):
        a, b = block(s, n); part = s[a:b]
        if old in part:
            s = s[:a] + part.replace(old, '(:num 0.0)', 1) + s[b:]; changed = True
    if changed:
        PATH.write_text(s); print('waspala-part.gc : particules des petites chutes coupees')
    else:
        print('waspala-part.gc : deja patche')
    subprocess.run([sys.executable, str(R / 'liquids-v3/compile_iso.py'), 'out/jak3/iso/WASPALA.DGO'], check=True)
    subprocess.run([sys.executable, str(R / 'sync_variant.py'), 'out/jak3/iso/WASPALA.DGO'], check=True)


if __name__ == '__main__': main()
