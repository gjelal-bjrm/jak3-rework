"""Align the native WWD fruit controllers with their new solid render geometry."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REL = 'goal_src/jak3/levels/wascity/ctymark-obs.gc'
backup = HERE / 'fruit-contact-before'
backup.mkdir(exist_ok=True)
for tree in ('data', 'engine-src'):
    path = ROOT / tree / REL
    old = path.read_text()
    saved = backup / (tree + '-ctymark-obs.gc')
    if not saved.exists():
        shutil.copy2(path, saved)
    text = old
    if '(defun remaster-fruit-ground-radius' not in text:
        marker = '(define *fruit-check-ground-counter* 0)'
        helper = '''

;; The new solid fruit uses the native particle sizes. Match its lower surface
;; for ground probing, without changing omega (which also drives the impulse).
(defun remaster-fruit-ground-radius ((part sparticle-cpuinfo))
  (let* ((sprite (-> part sprite))
         (rx (* 0.49 (-> sprite sx)))
         (ry (* 0.44835 (-> sprite sy)))
         (s (sin (-> sprite rot)))
         (c (cos (-> sprite rot)))
         )
    (sqrtf (+ (* rx rx s s) (* ry ry c c)))
    )
  )
'''
        assert text.count(marker) == 1
        text = text.replace(marker, marker + helper)
        for part, before, after in ((1153, '1.1', '0.97'),
                                    (1157, '1.1', '0.84'),
                                    (1156, '1.25', '1.15'),
                                    (1155, '1', '0.88')):
            start = text.index(f'(defpart {part}\n')
            end = text.index('\n(defpart ', start + 1)
            section = text[start:end]
            needle = f'(:y (meters {before}))'
            assert section.count(needle) == 1, part
            section = section.replace(needle, f'(:y (meters {after}))')
            text = text[:start] + section + text[end:]
        changes = {
            '(set! (-> v1-11 radius) (-> s4-0 omega))':
            '(set! (-> v1-11 radius) (remaster-fruit-ground-radius s4-0))',
            '(+ (-> s5-0 origin trans y) (-> arg1 omega))':
            '(+ (-> s5-0 origin trans y) (remaster-fruit-ground-radius arg1))',
        }
        for a, b in changes.items():
            assert text.count(a) == 1, a
            text = text.replace(a, b)
        path.write_text(text, encoding='utf-8', newline='\n')

dgo = ROOT / 'data/out/jak3/iso/WWD.DGO'
if not (backup / 'WWD.DGO').exists():
    shutil.copy2(dgo, backup / 'WWD.DGO')
manifest = {'scope': 'WWD market fruit only',
            'heights_m': {'1153': .97, '1157': .84, '1156': 1.15, '1155': .88,
                          '1154': 1.25},
            'unchanged': ['native release impulses', 'omega', 'fruit counts',
                          'collision geometry', 'launcher durations'],
            'baseline_dgo_sha256': hashlib.sha256((backup/'WWD.DGO').read_bytes()).hexdigest(),
            'source_sha256': hashlib.sha256((ROOT/'data'/REL).read_bytes()).hexdigest()}
(HERE/'fruit-contact-source.json').write_text(json.dumps(manifest, indent=2))
print('WWD fruit contact source ready; native DGO rebuild still required')
