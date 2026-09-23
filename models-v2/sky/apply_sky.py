"""Cote GOAL du ciel moderne : patch idempotent de data/goal_src/jak3/engine/gfx/sky/sky-tng.gc.

- publie chaque image l'etat du ciel au moteur (pc-remaster-sky-state : positions soleil / soleil vert /
  lune / etoile du jour, heure, etoile active) ;
- quand *pc-remaster-sky* est vrai, ne dessine plus les nuages plats natifs, le sprite du soleil ni celui
  de l'etoile du jour (redessines par la passe moderne) ; base, brume, brouillard, lune, soleil vert et
  etoiles de nuit restent natifs.
Apres : python liquids-v3/rebuild_routes.py (le code du ciel est dans GAME.CGO).
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'data/goal_src/jak3/engine/gfx/sky/sky-tng.gc'


def main():
    s = PATH.read_text()
    if 'pc-remaster-sky-state' in s:
        print('sky-tng.gc : deja patche'); return
    anchor = ';; DECOMP BEGINS\n'
    assert s.count(anchor) == 1
    s = s.replace(anchor, anchor + '''
;; Ciel moderne du remaster : le moteur redessine nuages, soleil et etoile du jour.
(define-extern pc-remaster-sky-state (function pointer vector none))
(define *pc-remaster-sky* #t)
''', 1)
    old = """(defmethod draw ((this sky-work))
  ;; og:preserve-this
  (update-pc-sky-scaling)
"""
    new = """(defmethod draw ((this sky-work))
  ;; og:preserve-this
  (update-pc-sky-scaling)
  (let ((misc (new 'stack-no-clear 'vector)))
    (set! (-> misc x) (-> this time))
    (set! (-> misc y) (if (or (task-node-closed? (game-task-node precursor-destroy-ship-resolution)) (-> this disable-day-star)) 0.0 1.0))
    (set! (-> misc z) 0.0)
    (set! (-> misc w) 0.0)
    (pc-remaster-sky-state (the-as pointer (-> this upload-data)) misc))
"""
    assert s.count(old) == 1, 'debut de la methode draw introuvable'
    s = s.replace(old, new, 1)
    # branche normale du ciel (pas le champ d'etoiles) : soleil, etoile du jour, nuages
    old_sun = "                 (sun-dma s4-1 s2-0)\n                 (green-sun-dma s4-1 s2-0)\n                 (moon-dma s4-1 s2-0)\n"
    assert s.count(old_sun) == 1, 'bloc soleil introuvable'
    s = s.replace(old_sun, "                 (if (not *pc-remaster-sky*) (sun-dma s4-1 s2-0))\n                 (green-sun-dma s4-1 s2-0)\n                 (moon-dma s4-1 s2-0)\n", 1)
    old_star = "                     (day-star-dma s4-1 s2-0)\n"
    assert s.count(old_star) == 1
    s = s.replace(old_star, "                     (if (not *pc-remaster-sky*) (day-star-dma s4-1 s2-0))\n", 1)
    old_clouds = "                 (draw-clouds s4-1 s2-0)\n"
    assert s.count(old_clouds) == 1
    s = s.replace(old_clouds, "                 (if (not *pc-remaster-sky*) (draw-clouds s4-1 s2-0))\n", 1)
    PATH.write_text(s)
    print('sky-tng.gc : etat publie, nuages/soleil/etoile natifs desactives sous *pc-remaster-sky*')


def disable_day_star_particle():
    """La lueur blanche a aigrettes de l'etoile du jour est une particule de time-of-day-proc (champ day-star),
    spawnee tant que day-star-enable est vrai : sous *pc-remaster-sky* on la coupe (le ciel moderne la redessine)."""
    s = PATH.read_text()
    old = "                     (set! (-> *time-of-day* 0 day-star-enable) #t)\n"
    new = "                     (set! (-> *time-of-day* 0 day-star-enable) (not *pc-remaster-sky*))\n"
    if new in s: print('sky-tng.gc : particule de l etoile deja coupee'); return
    assert s.count(old) == 1, 'activation native de l etoile introuvable'
    PATH.write_text(s.replace(old, new, 1)); print('sky-tng.gc : particule native de l etoile coupee sous *pc-remaster-sky*')


if __name__ == '__main__':
    main()
    disable_day_star_particle()
