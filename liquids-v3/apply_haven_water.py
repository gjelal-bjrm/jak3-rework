"""Effets de Jak dans l'eau (contacts, coups de bras, suppression des anneaux natifs) : etend la porte
GOAL de Spargus au port de Haven, et publie les contacts a la hauteur reelle de la surface.

Patch idempotent de data/goal_src/jak3/engine/common-obs/water.gc (deja patche par liquids-v3 pour
Spargus et le palais). Apres : rebuild des routes (apply_boot.py --scene arena|palace, compile_iso.py
GAME.CGO, copie dans routes/remaster/<scene>/GAME.CGO, empreintes du manifeste) : voir rebuild_routes.py.
"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/goal_src/jak3/engine/common-obs/water.gc'
HELPER = ''';; Port de Haven (carte d'ocean *ocean-map-city*, niveau 0 m) : meme rendu moderne de la mer.
(defun remaster-haven-water? ((this water-control))
  (and (= (-> this process) *target*)
       (logtest? (water-flag use-ocean) (-> this flags))
       (> (-> this process root trans x) (meters -864.0))
       (< (-> this process root trans x) (meters 3744.0))
       (> (-> this process root trans z) (meters -1728.0))
       (< (-> this process root trans z) (meters 2880.0))
       (< (fabs (-> this surface-height)) (meters 2.0))))

;; Toute mer rendue par le prototype (Spargus ou Haven).
(defun remaster-modern-water? ((this water-control))
  (or (remaster-spargus-water? this) (remaster-haven-water? this)))

'''


def main():
    s = PATH.read_text()
    if 'remaster-haven-water?' in s:
        print('water.gc : deja patche pour Haven'); return
    anchor = '\n;; Keep all original water physics/sounds; replace Jak\'s visual emitters here only.\n'
    assert s.count(anchor) == 1, 'ancre du palais introuvable'
    s = s.replace(anchor, '\n' + HELPER + anchor.lstrip('\n'), 1)
    # les six portes (anneaux, eclaboussures, gouttes, ondulation native, emission) utilisent la porte combinee
    n = s.count('(remaster-spargus-water? this)')
    s = s.replace('(remaster-spargus-water? this)', '(remaster-modern-water? this)')
    # la definition combinee ne doit pas se referencer elle-meme
    s = s.replace('(or (remaster-modern-water? this) (remaster-haven-water? this))', '(or (remaster-spargus-water? this) (remaster-haven-water? this))', 1)
    # contact publie a la hauteur reelle de la surface (9 m a Spargus, 0 m a Haven)
    old = '        (set! (-> packet y) (meters 9.0))\n'
    assert s.count(old) == 1
    s = s.replace(old, '        (set! (-> packet y) (-> this surface-height))\n')
    PATH.write_text(s)
    print(f'water.gc : porte Haven ajoutee, {n} portes combinees, contact a la hauteur de surface')


if __name__ == '__main__': main()
