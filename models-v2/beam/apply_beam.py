"""Rayon des departs de mission (« rod-of-god » de task-arrow) remplace par un rendu moderne.

- GOAL (data/goal_src/jak3/engine/game/task/task-arrow.gc) : chaque image, publie position, rayon et intensite
  au moteur (pc-remaster-beam) et masque le cylindre natif (draw-control-status no-draw) ; la grande lueur
  de base (particules 410/411, sprite glow-soft de 18 m) est ramenee a 20 % : le moteur dessine sa propre
  lueur au sol. Les petites etincelles qui montent (409) restent.
- Moteur : ModernBeam.h, shaders modern_beam.vert/.frag (installes ici dans data/, engine-src/, variantes).
Apres : python liquids-v3/rebuild_routes.py arena palace ; recompiler le moteur.
"""
from pathlib import Path
import hashlib, json, shutil
H = Path(__file__).resolve().parent; R = H.parents[1]
TA = R / 'data/goal_src/jak3/engine/game/task/task-arrow.gc'
REL = 'game/graphics/opengl_renderer/shaders/'


def replace_once(s, old, new, what):
    assert s.count(old) == 1, f'{what} : ancre introuvable ou multiple ({s.count(old)})'
    return s.replace(old, new, 1)


def patch_goal():
    s = TA.read_text()
    if 'pc-remaster-beam' in s:
        print('task-arrow.gc : deja patche'); return
    s = replace_once(s, ';; DECOMP BEGINS\n', ''';; DECOMP BEGINS

;; Rayon moderne du remaster : le moteur dessine le rayon ; le cylindre natif est masque.
(define-extern pc-remaster-beam (function pointer none))
(define *pc-remaster-beam* #t)
''', 'debut du fichier')
    old = '''       (set-vector! (-> this draw color-emissive) 0.5 0.5 0.3 1.0)
'''
    new = '''       (set-vector! (-> this draw color-emissive) 0.5 0.5 0.3 1.0)
       (when *pc-remaster-beam*
         (let ((io (new 'stack-no-clear 'matrix)))
           (vector-copy! (-> io rvec) (-> this root trans))
           (set! (-> io rvec w) (* 1843.2 f0-39 f30-1))
           (set! (-> io uvec x) (-> this alpha))
           (pc-remaster-beam (the-as pointer io))
           )
         (logior! (-> this draw status) (draw-control-status no-draw))
         )
'''
    s = replace_once(s, old, new, 'rayon')
    for part in ('410', '411'):
        old = (f'       (set! (-> *part-id-table* {part} init-specs 9 initial-valuef)\n'
               f'             (* (-> this alpha) (rand-vu-float-range 80.0 96.0))\n')
        new = (f'       (set! (-> *part-id-table* {part} init-specs 9 initial-valuef)\n'
               f'             (* (if *pc-remaster-beam* 0.2 1.0) (-> this alpha) (rand-vu-float-range 80.0 96.0))\n')
        s = replace_once(s, old, new, f'lueur {part}')
    TA.write_text(s)
    print('task-arrow.gc : rayon publie au moteur, cylindre natif masque, lueur de base attenuee')


def install_shaders():
    files = json.loads((R / 'variant-files.json').read_text(encoding='utf-8'))
    hashes = json.loads((R / 'variant-hashes.json').read_text(encoding='utf-8'))
    for name in ('modern_beam.vert', 'modern_beam.frag'):
        rel = REL + name
        for root in (R / 'data', R / 'engine-src'):
            shutil.copy2(H / name, root / rel)
        for variant in ('original', 'remaster-v1', 'remaster'):
            target = R / 'variants' / variant / rel
            shutil.copy2(H / name, target)
            hashes.setdefault(variant, {})[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
        if rel not in files: files.append(rel)
        print('installe :', rel)
    (R / 'variant-files.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
    (R / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    patch_goal()
    install_shaders()
