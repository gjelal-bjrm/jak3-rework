"""Extend the accepted contact response to Spargus sea, retaining palace logic."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'data/goal_src/jak3/engine/common-obs/water.gc'
backup = ROOT / 'models-v2/before/water-before-ocean.gc'
if not backup.exists():
    backup.write_bytes(path.read_bytes())
source = backup.read_text()
helper = '''
(define-extern pc-remaster-water-contact (function vector none))
(define-extern pc-remaster-water-stroke (function vector int none))
(defun remaster-spargus-water? ((this water-control))
  (and (= (-> this process) *target*)
       (logtest? (water-flag use-ocean) (-> this flags))
       (> (-> this process root trans x) (meters 1400.0))
       (< (-> this process root trans x) (meters 2400.0))
       (> (-> this process root trans z) (meters -1200.0))
       (< (-> this process root trans z) (meters 400.0))
       (< (fabs (- (-> this surface-height) (meters 9.0))) (meters 2.0))))
'''
source = source.replace(';; DECOMP BEGINS', ';; DECOMP BEGINS\n' + helper, 1)
source = source.replace('(not (remaster-palace-water? this))',
                        '(not (or (remaster-palace-water? this) (remaster-spargus-water? this)))')
start = source.index('(defmethod water-control-method-10 ')
end = source.index('(defmethod start-bobbing!', start)
method = source[start:end]
anchor = '    0\n    (none)'
assert method.count(anchor) == 1
contact = '''    (when (and (remaster-spargus-water? this)
               (logtest? (water-flag touch-water) (-> this flags))
               (> (- (-> this process root trans y) (-> this surface-height)) (meters -2.8)))
      (let ((packet (new-stack-vector0)))
        (vector-copy! packet (-> this process root trans))
        (set! (-> packet y) (meters 9.0))
        (set! (-> packet w) (-> this process control transv y))
        (pc-remaster-water-contact packet)
        (when (logtest? (water-flag swimming) (-> this flags))
          (vector<-cspace! packet (-> this process control lhand-cspace))
          (pc-remaster-water-stroke packet 0)
          (vector<-cspace! packet (-> this process control rhand-cspace))
          (pc-remaster-water-stroke packet 1))))
'''
source = source[:start] + method.replace(anchor, contact + anchor) + source[end:]
path.write_text(source)
print('Spargus: collision-driven water contacts connected; original player spray suppressed locally')
