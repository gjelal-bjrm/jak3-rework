"""Camera orbitale du remaster (manette) : patch idempotent de
data/goal_src/jak3/engine/camera/cam-states.gc (camera « a ficelle » cam-string).

Le jeu d'origine n'utilise le stick droit vertical que pour rapprocher / eloigner la camera le long d'une
courbe fixe : impossible de regarder le ciel ou le sol. Ici, le stick droit vertical incline vraiment la
camera autour de Jak (de -60 deg, camera basse qui regarde le ciel, a +75 deg, vue plongeante). La
rotation horizontale, le suivi, les collisions et les cameras fixes / cinematiques restent ceux du jeu.
Modes arme, vehicule et BOMBBOT : camera d'origine.
Apres : python liquids-v3/rebuild_routes.py arena palace (le code camera est dans GAME.CGO).
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'data/goal_src/jak3/engine/camera/cam-states.gc'
CAMERA = ROOT / 'data/goal_src/jak3/engine/camera/camera.gc'
MARK = ';; ---- Camera orbitale du remaster'
STATE = """;; ---- Camera orbitale du remaster : etat partage (defini ici, camera.gc est compile avant cam-states.gc)
(define *pc-orbit-enable* #t)
(deftype pc-orbit-state (structure)
  ((pitch   float)
   (idle    float)
   (ready   int32)
   (active  int32)
   (stamp   time-frame)
   )
  )
(define *pc-orbit* (new 'static 'pc-orbit-state))

"""

ORBIT = r''';; ---- Camera orbitale du remaster (manette) -------------------------------------------------------
;; Stick droit vertical = inclinaison autour de Jak : -60 deg (camera basse, on voit le ciel) a +75 deg (vue
;; plongeante). Distance nominale de la zone (hypotenuse de string-max-val) ; vers le haut, la camera glisse
;; au ras du sol en se rapprochant (elle ne s'enfonce plus dans le sol) et vise a travers la tete de Jak. Sans toucher au stick pendant 3 s, l'inclinaison
;; revient doucement a celle de la zone quand Jak se deplace. Le reglage d'inversion verticale d'OpenGOAL
;; est respecte (par defaut : pousser le stick vers le haut fait regarder vers le haut).
(defbehavior pc-orbit-joystick camera-slave ()
  (set! (-> *pc-orbit* active) 0)
  (when (and *pc-orbit-enable*
             (not (logtest? (cam-slave-options-u32 GUN_CAM) (-> self options)))
             (not (logtest? (-> *camera* settings slave-options) (cam-slave-options BIKE_MODE)))
             (not (logtest? (cam-slave-options BOMBBOT) (-> *camera* settings slave-options)))
             )
    (let* ((zmax (fmax 8192.0 (-> self string-max-val z)))
           (ymax (-> self string-max-val y))
           (dist (sqrtf (+ (* zmax zmax) (* ymax ymax))))
           (rest (fmax 6.0 (fmin 32.0 (* 0.0054931640625 (atan ymax zmax)))))
           (v (analog-input-vertical-third
                (the-as int (-> *cpad-list* cpads 0 righty)) 128.0 32.0 110.0 (* 100.0 (seconds-per-frame))))
           )
      (when (zero? (-> *pc-orbit* ready))
        (set! (-> *pc-orbit* pitch) rest)
        (set! (-> *pc-orbit* ready) 1)
        )
      (if (or (logtest? (cam-slave-options-u32 BLOCK_RIGHT_STICK) (-> self options))
              (logtest? (-> *camera* settings master-options) (cam-master-options BLOCK_RIGHT_STICK))
              (logtest? (-> *camera* settings master-options) (cam-master-options IGNORE_ANALOG))
              )
          (set! v 0.0)
          )
      (cond
        ((!= v 0.0)
         (+! (-> *pc-orbit* pitch) v)
         (set! (-> *pc-orbit* idle) 0.0)
         (logior! (-> self options) (cam-slave-options-u32 PLAYER_MOVING_CAMERA))
         )
        (else
          (+! (-> *pc-orbit* idle) (seconds-per-frame))
          (when (and (< 3.0 (-> *pc-orbit* idle))
                     (< 40.96 (vector-vector-distance (-> *camera* tpos-curr-adj) (-> *camera* tpos-old-adj)))
                     )
            (seek! (-> *pc-orbit* pitch) rest (* 12.0 (seconds-per-frame)))
            )
          )
        )
      (set! (-> *pc-orbit* pitch) (fmax -60.0 (fmin 75.0 (-> *pc-orbit* pitch))))
      (let* ((p (-> *pc-orbit* pitch))
             (a (* 182.04445 p))
             (d dist)
             )
        ;; vers le haut : la camera glisse au ras du sol (40 cm) en se rapprochant de Jak, sans s'y enfoncer ;
        ;; elle vise toujours a travers sa tete, donc vers le ciel
        (when (< p 0.0)
          (set! d (fmin d (/ (fmax 2048.0 (- (-> *camera* settings target-height) 1638.4)) (- (sin a)))))
          (set! d (fmax 3276.8 d))
          )
        (set! (-> self view-off z) (* d (cos a)))
        (set! (-> self view-off y) (* d (sin a)))
        (set! (-> self view-off-param) 1.0)
        )
      (set! (-> *pc-orbit* active) 1)
      (set! (-> *pc-orbit* stamp) (-> *display* real-clock frame-counter))
      #t
      )
    )
  )

'''


def replace_once(s, old, new, what):
    assert s.count(old) == 1, f'{what} : ancre introuvable ou multiple ({s.count(old)})'
    return s.replace(old, new, 1)


def patch_camera():
    """Etat partage + regle « les pieds de Jak restent a l'ecran » (vector-into-frustum-nosmooth!) desactivee
    quand la camera orbitale regarde vers le haut : sinon la vue plonge vers ses pieds des que la camera est basse."""
    s = CAMERA.read_text()
    if MARK in s:
        print('camera.gc : deja patche'); return
    s = replace_once(s, ';; DECOMP BEGINS\n', ';; DECOMP BEGINS\n\n' + STATE, 'debut de camera.gc')
    s = replace_once(s, '      (vector-into-frustum-nosmooth! s1-0 arg1 (lerp-clamp arg3 (/ arg3 4) (-> arg0 underwater-blend value)))\n',
                     '      (if (not (and (nonzero? (-> *pc-orbit* active))\n'
                     '                    (< (- (-> *display* real-clock frame-counter) (-> *pc-orbit* stamp)) (seconds 0.1))\n'
                     '                    (< (-> *pc-orbit* pitch) 4.0)\n'
                     '                    )\n'
                     '               )\n'
                     '          (vector-into-frustum-nosmooth! s1-0 arg1 (lerp-clamp arg3 (/ arg3 4) (-> arg0 underwater-blend value)))\n'
                     '          )\n', 'cadrage des pieds')
    CAMERA.write_text(s)
    print('camera.gc : etat de la camera orbitale, cadrage des pieds libere vers le haut')


def main():
    patch_camera()
    s = PATH.read_text()
    if MARK in s:
        print('cam-states.gc : deja patche'); return
    s = replace_once(s, '(defbehavior cam-string-joystick camera-slave ()\n',
                     ORBIT + '(defbehavior cam-string-joystick camera-slave ()\n', 'cam-string-joystick')
    # 1. partie verticale d'origine (distance le long de la courbe) : seulement si la camera orbitale ne s'en charge pas
    s = replace_once(s, '  (let ((f28-0 (cam-dist-analog-input (the-as int (-> *cpad-list* cpads 0 righty)) 0.05))\n',
                     '  (if (not (pc-orbit-joystick))\n'
                     '  (let ((f28-0 (cam-dist-analog-input (the-as int (-> *cpad-list* cpads 0 righty)) 0.05))\n',
                     'distance au stick')
    s = replace_once(s, '''  (when (not (logtest? (-> *camera* settings master-options) (cam-master-options IGNORE_ANALOG)))
    ;; og:preserve-this
    (let ((f30-2 (analog-input-horizontal-third
                   (the-as int (-> *cpad-list* cpads 0 rightx))''', '''    )
  (when (not (logtest? (-> *camera* settings master-options) (cam-master-options IGNORE_ANALOG)))
    ;; og:preserve-this
    (let ((f30-2 (analog-input-horizontal-third
                   (the-as int (-> *cpad-list* cpads 0 rightx))''', 'rotation horizontale')
    # 2. correction de hauteur d'origine (fin de fonction) : inactive quand l'orbite fixe la hauteur
    s = replace_once(s, '''  (when (not (logtest? (cam-slave-options WIDE_FOV) (-> *camera* settings slave-options)))
    (let ((f0-101 (vector-length (-> self view-flat))))''', '''  (when (and (zero? (-> *pc-orbit* active))
             (not (logtest? (cam-slave-options WIDE_FOV) (-> *camera* settings slave-options)))
             )
    (let ((f0-101 (vector-length (-> self view-flat))))''', 'hauteur de fin')
    PATH.write_text(s)
    print('cam-states.gc : camera orbitale branchee')


if __name__ == '__main__':
    main()
