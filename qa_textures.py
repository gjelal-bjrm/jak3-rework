"""Controle des textures reellement affichees (journal du moteur, REMASTER_TEXTURE_AUDIT=1).

  python qa_textures.py            resume par niveau : textures vues, HD affichees, HD attendues mais basses
Le jeu doit avoir ete lance avec la variable REMASTER_TEXTURE_AUDIT=1 (launch.py la transmet).
"""
from pathlib import Path
import json, re
ROOT = Path(__file__).resolve().parent


def main():
    log = (ROOT / 'remaster-runtime.log').read_text(encoding='utf-8', errors='replace')
    seen = {}
    for m in re.finditer(r'Texture audit: (\S+) (\S+) (\d+)x(\d+)', log):
        seen[(m.group(1), m.group(2))] = (int(m.group(3)), int(m.group(4)))
    hd = set()
    for f in ('arena-remaster/textures/textures-genshin.json', 'textures-remaster/textures.json'):
        p = ROOT / f
        if p.exists(): hd |= {t['name'] for t in json.loads(p.read_text())['textures']}
    levels = {}
    for (level, name), (w, h) in seen.items():
        d = levels.setdefault(level, {'vues': 0, 'hd': 0, 'manquantes': []}); d['vues'] += 1
        if name in hd:
            if max(w, h) >= 512: d['hd'] += 1
            else: d['manquantes'].append(f'{name} {w}x{h}')
    bad = 0
    for level, d in sorted(levels.items()):
        print(f"{level:12s} vues {d['vues']:3d} | HD affichees {d['hd']:3d} | HD NON affichees : {d['manquantes'] or 'aucune'}")
        bad += len(d['manquantes'])
    print('RESULTAT :', 'OK' if not bad else f'{bad} texture(s) HD non affichee(s)')
    return bad


if __name__ == '__main__':
    main()
