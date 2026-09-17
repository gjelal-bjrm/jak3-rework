"""Suppress legacy Jak water particles only in the palace prototype volumes."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'data/goal_src/jak3/engine/common-obs/water.gc'
backup=ROOT/'liquids-v3/water-before-v3.gc'
if not backup.exists():backup.write_text(path.read_text())
s=backup.read_text()
helper='''
;; Keep all original water physics/sounds; replace Jak's visual emitters here only.
(defun remaster-palace-water? ((this water-control))
  (and (= (-> this process) *target*)
       (logtest? (water-flag use-water-anim) (-> this flags))
       (> (-> this process root trans x) (meters 1950.0))
       (< (-> this process root trans x) (meters 2065.0))
       (> (-> this process root trans z) (meters -535.0))
       (< (-> this process root trans z) (meters -395.0))
       (> (-> this surface-height) (meters 240.0))
       (< (-> this surface-height) (meters 244.0))))

'''
s=s.replace(';; DECOMP BEGINS',';; DECOMP BEGINS\n'+helper,1)
counts={}
for flag in ('part-splash','part-rings','part-drip'):
    old=f'(logtest? (water-flag {flag}) (-> this flags))'
    counts[flag]=s.count(old)
    assert counts[flag]>0
    s=s.replace(old,f'(and (not (remaster-palace-water? this)) {old})')
s=s.replace('(if (and (not (handle->process (-> this ripple)))',
            '(if (and (not (remaster-palace-water? this)) (not (handle->process (-> this ripple)))',1)
path.write_text(s)
print('Original Jak visual emitters disabled in palace:',counts)
