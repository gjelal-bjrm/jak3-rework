"""Connect the palace's genuine water contacts to the new renderer."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
goal = ROOT/'data/goal_src/jak3'
path = goal/'levels/wascity/palace/waspala-obs.gc'
backup = ROOT/'liquids-v3/waspala-obs-before-contacts.gc'
if not backup.exists():
    backup.write_text(path.read_text())
source = backup.read_text()
base = (goal/'engine/common-obs/water-anim.gc').read_text()
state = base[base.index('(defstate idle (water-anim)'):base.index('(defmethod move-to-point!')]
state = state.replace('(defstate idle (water-anim)', '(defstate idle (water-anim-waspala)')
contact = '''
;; Render-only response, driven by Jak's actual collision water control.
(define-extern pc-remaster-water-contact (function vector none))
'''
state = state.replace(':trans (behavior ()', ''':trans (behavior ()
    (when (and *target*
               (logtest? (water-flag touch-water) (-> *target* water flags))
               (< (fabs (- (-> *target* water surface-height) (-> self root trans y))) (meters 0.30))
               (< (- (-> *target* root trans y) (-> *target* water surface-height)) (meters 0.15))
               (> (- (-> *target* root trans y) (-> *target* water surface-height)) (meters -2.2)))
      (let ((packet (new 'stack-no-clear 'vector)))
        (vector-copy! packet (-> *target* root trans))
        (set! (-> packet y) (-> *target* water surface-height))
        ;; In shallow water, the floor can zero velocity on the contact frame.
        ;; The water controller keeps the actual previous/current foot positions.
        (set! (-> packet w)
          (fmin (-> *target* control transv y)
            (/ (- (-> *target* water bottom 0 y) (-> *target* water bottom 1 y))
               (fmax 0.001 (seconds-per-frame)))))
        (pc-remaster-water-contact packet)))''')
anchor = '(deftype waspala-paddle-wheel (process-drawable)'
assert source.count(anchor) == 1
source = source.replace(anchor,contact+state+anchor)
path.write_text(source)
print('Palace water: Jak contacts connected to surface ripples and spray')
