"""Catacombes : lumieres bleues apaisees (patch idempotent de data/goal_src/jak3/levels/comb/comb-mood.gc).

D'origine, update-mood-comb fait pulser les palettes de lumiere 1 et 3 a 7 avec un sinus sur 25 tops de l'horloge
des particules (300 tops/s) : 12 eclairs par seconde, et un chenillard de 5 segments qui tourne en 0,42 s.
Retour du joueur : clignotement incessant, desagreable (risque pour les personnes epileptiques). Version apaisee :
respiration lente (1 s par pulsation, jamais sous 55 %), chenillard de 5 s dont les segments eteints gardent 30 %.
Apres : python liquids-v3/compile_iso.py out/jak3/iso/COMBA.DGO, puis sync_variant (COMBA.DGO, RAILA.DGO).
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'data/goal_src/jak3/levels/comb/comb-mood.gc'

OLD = """      (let* ((s5-2 (-> *display* part-clock frame-counter))
             (f0-6 (* 1310.72 (the float (mod s5-2 25))))
             (f30-2 (sin f0-6))
             (f0-8 (* 109.22667 (the float (mod s5-2 600))))
             (s5-3 (/ (mod s5-2 125) 25))
             )
        (set! (-> arg0 times 0 w) 1.0)
        (set! (-> arg0 times 1 w) f30-2)"""
NEW = """      (let* ((s5-2 (-> *display* part-clock frame-counter))
             (f0-6 (* 109.22667 (the float (mod s5-2 300))))
             (f30-2 (+ 0.3 (* 0.7 (sin f0-6))))
             (f0-8 (* 109.22667 (the float (mod s5-2 600))))
             (s5-3 (/ (mod s5-2 1500) 300))
             )
        ;; remaster : lumieres apaisees (respiration de 1 s au lieu de 12 eclairs par seconde)
        (set! (-> arg0 times 0 w) 1.0)
        (set! (-> arg0 times 1 w) (+ 0.55 (* 0.45 (sin f0-6))))"""


def main():
    s = PATH.read_text(encoding='utf-8')
    if NEW in s: print('comb-mood.gc : deja patche'); return
    assert s.count(OLD) == 1, 'ancre introuvable'
    s = s.replace(OLD, NEW)
    # segments eteints du chenillard : 30 % au lieu de noir
    old_off = """                                      f30-2
                                      0.0
                                      )"""
    n = s.count(old_off); assert n == 5, n
    s = s.replace(old_off, """                                      f30-2
                                      0.3
                                      )""")
    PATH.write_text(s, encoding='utf-8'); print('comb-mood.gc : lumieres apaisees')


if __name__ == '__main__': main()
