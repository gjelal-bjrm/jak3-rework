"""Cote GOAL de la meteo du remaster : patch idempotent de data/goal_src/jak3/engine/gfx/mood/mood.gc.

A chaque image, init-weather! (appele par update-time-of-day) echange un petit tableau avec le moteur
(pc-remaster-weather, WeatherState.h) :
  - GOAL -> moteur : max-rain du niveau (0 a l'interieur), eclair natif en cours, indice d'eclair ;
  - moteur -> GOAL : meteo active, nuages/brouillard natifs (tables de lumiere couverte de chaque niveau),
    pluie (son rain-hiss, gouttes natives), neige native, eclairs + tonnerre autorises.
Le tirage aleatoire, les fondus et le rendu moderne sont dans le moteur. Commande de test :
  (pc-remaster-weather-force 4)   ; 0 beau temps, 1 voile, 2 couvert, 3 pluie, 4 orage, 5 neige,
                                  ; 6 tempete de sable, 7 brouillard, -1 retour au hasard
Apres : python liquids-v3/rebuild_routes.py arena palace (mood.gc est dans GAME.CGO).
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'data/goal_src/jak3/engine/gfx/mood/mood.gc'


def replace_once(s, old, new, what):
    assert s.count(old) == 1, f'{what} : ancre introuvable ou multiple'
    return s.replace(old, new, 1)


PARTS = ROOT / 'data/goal_src/jak3/engine/gfx/mood/weather-part.gc'


def lens_drops():
    """Gouttes d'eau natives sur l'objectif (part-water-drip, sprite starflash en forme de X) : coupees quand la
    meteo du remaster est active (la pluie moderne se passe d'effet de lentille)."""
    s = PARTS.read_text()
    old = ("          (if (< 0.0 f26-0)\n"
           "              (send-event *camera* 'part-water-drip f26-0 f0-11)\n")
    new = ("          (if (and (< 0.0 f26-0) (>= 0.5 (-> *pc-weather-io* data 8)))\n"
           "              (send-event *camera* 'part-water-drip f26-0 f0-11)\n")
    if new in s: print('weather-part.gc : deja patche'); return
    PARTS.write_text(replace_once(s, old, new, 'gouttes sur l objectif'))
    print('weather-part.gc : gouttes sur l objectif coupees sous la meteo du remaster')


TOD = ROOT / 'data/goal_src/jak3/engine/gfx/mood/time-of-day.gc'


def outdoor():
    """Exterieur = exterior-level natif (vrai dehors, faux dans les interieurs), publie en io[4] juste avant sa
    remise a zero par update-time-of-day (il vaut alors l'etat de l'image precedente). max-rain ne convient
    pas : il vaut 0 a Spargus (le desert n'a pas de pluie native)."""
    s = TOD.read_text()
    old = ("    (set! (-> arg0 exterior-level) #f)\n"
           "    (init-weather! *mood-control*)\n")
    new = ("    (set! (-> *pc-weather-io* data 4) (if (-> arg0 exterior-level) 1.0 0.0))\n"
           "    (set! (-> arg0 exterior-level) #f)\n"
           "    (init-weather! *mood-control*)\n")
    if new in s: print('time-of-day.gc : deja patche')
    else:
        TOD.write_text(replace_once(s, old, new, 'exterior-level')); print('time-of-day.gc : exterieur publie')
    s = PATH.read_text()
    pairs = [('(fmin (-> *pc-weather-io* data 11) f28-2)', '(* (-> *pc-weather-io* data 11) (-> *pc-weather-io* data 4))'),
             ('(fmin (-> io 12) (-> *time-of-day-context* max-rain))', '(* (-> io 12) (-> io 4))')]
    for a, b in pairs:
        if a in s: s = replace_once(s, a, b, a)
    PATH.write_text(s); print('mood.gc : pluie et neige natives suivent l exterieur')


def main():
    lens_drops()
    s = PATH.read_text()
    if 'pc-remaster-weather' in s:
        print('mood.gc : deja patche'); outdoor(); return
    s = replace_once(s, ';; DECOMP BEGINS\n', ''';; DECOMP BEGINS

;; Meteo du remaster : le moteur choisit la meteo (WeatherState.h) et pilote ici le systeme natif.
(define-extern pc-remaster-weather (function pointer none))
(define-extern pc-remaster-weather-force (function int none))
(deftype pc-weather-io (structure)
  ((data  float  16)
   )
  )
(define *pc-weather-io* (new 'static 'pc-weather-io))
''', 'debut du fichier')

    s = replace_once(s, '''(defmethod init-weather! ((this mood-control))
  (local-vars (v1-32 int) (a1-12 object))
  (let ((s5-0 (level-get-target-inside *level*)))
    (when s5-0
''', '''(defmethod init-weather! ((this mood-control))
  (local-vars (v1-32 int) (a1-12 object))
  (let ((s5-0 (level-get-target-inside *level*)))
    (when s5-0
      (let ((io (-> *pc-weather-io* data)))
        (set! (-> io 0) (-> *time-of-day-context* max-rain))
        (set! (-> io 1) (-> this lightning-flash))
        (set! (-> io 2) (the float (-> this lightning-index)))
        (pc-remaster-weather io)
        (when (< 0.5 (-> io 8))
          (set! (-> this overide-weather-flag) #t)
          (set! (-> this overide cloud) (-> io 9))
          (set! (-> this overide fog) (-> io 10))
          (set! (-> *setting-control* user-default snow) (fmin (-> io 12) (-> *time-of-day-context* max-rain)))
          )
        )
''', 'debut de init-weather!')

    s = replace_once(s, '               (f30-3 (fmin 0.75 f0-125))\n',
                     '               (f30-3 (if (< 0.5 (-> *pc-weather-io* data 8))\n'
                     '                          (fmin (-> *pc-weather-io* data 11) f28-2)\n'
                     '                          (fmin 0.75 f0-125)\n'
                     '                          )\n'
                     '                      )\n', 'intensite de pluie')

    s = replace_once(s, '             (gen-lightning-and-thunder! this (the-as int a1-12))\n',
                     '             (if (or (>= 0.5 (-> *pc-weather-io* data 8)) (< 0.5 (-> *pc-weather-io* data 13)))\n'
                     '                 (gen-lightning-and-thunder! this (the-as int a1-12))\n'
                     '                 (set! (-> this lightning-flash) 0.0)\n'
                     '                 )\n', 'eclairs')
    PATH.write_text(s)
    print('mood.gc : meteo du remaster branchee (echange, nuages/brouillard, pluie, neige, eclairs)')
    outdoor()


if __name__ == '__main__':
    main()
