"""Publie au ciel moderne l'etat de Jak (Dark Jak actif) et l'avancement de l'histoire (percent-complete).

Le code du ciel (sky-tng.gc) est compile avant target et game-info : on publie donc depuis le controle
d'eau de Jak (water.gc, methode 10, chaque image), deja patche par liquids-v3. Idempotent.
Apres : python liquids-v3/rebuild_routes.py
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'data/goal_src/jak3/engine/common-obs/water.gc'


def main():
    s = PATH.read_text()
    if 'pc-remaster-sky-actor' in s:
        print('water.gc : etat acteur deja publie'); return
    anchor = '(define-extern pc-remaster-water-stroke (function vector int none))\n'
    assert s.count(anchor) == 1, 'declarations du prototype introuvables'
    s = s.replace(anchor, anchor + '(define-extern pc-remaster-sky-actor (function float float none))\n', 1)
    head = '(defmethod water-control-method-10 ((this water-control))\n'
    assert s.count(head) == 1, 'methode 10 introuvable'
    body = '''  ;; Ciel moderne : Dark Jak actif et avancement de l'histoire (l'etoile du jour y reagit).
  (when (= (-> this process) *target*)
    (pc-remaster-sky-actor
      (if (logtest? (-> this process focus-status) (focus-status dark)) 1.0 0.0)
      (-> *game-info* percent-complete)))
'''
    s = s.replace(head, head + body, 1)
    PATH.write_text(s); print('water.gc : etat acteur publie au ciel')


if __name__ == '__main__': main()
