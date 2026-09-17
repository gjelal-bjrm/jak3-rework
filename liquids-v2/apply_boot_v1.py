"""Boot the isolated prototype directly at the opening playable tutorial."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
source = ROOT.parents[1] / 'active/jak3/data/goal_src/jak3/engine/level/level.gc'
target = ROOT / 'data/goal_src/jak3/engine/level/level.gc'
text = source.read_text(encoding='utf-8')
old = '(lambda () (play #t #t) (none))'
assert text.count(old) == 1
new = '''(lambda ()
      (play #t #t)
      ;; Isolated Spargus prototype: same spawn and clock for both A/B variants.
      (when *debug-segment*
        (process-spawn-function process
          (lambda :behavior process ()
        (stack-size-set! (-> self main-thread) 2048)
        ;; Let play-boot return and the initial game processes initialize first.
        (dotimes (frame 120) (suspend))
        (start 'play (get-continue-by-name *game-info* "game-start"))
        (send-event (ppointer->process *time-of-day*) 'change 'ratio 0.0)
        (send-event (ppointer->process *time-of-day*) 'change 'hour 9)
        (send-event (ppointer->process *time-of-day*) 'change 'minutes 0)
        (send-event (ppointer->process *time-of-day*) 'change 'seconds 0)
        (send-event (ppointer->process *time-of-day*) 'change 'frames 0)
        (set! *cheat-mode* #f)
        (format 0 "SPARGUS-PROTOTYPE: game-start, fixed 09:00 lighting~%")
        ;; Capture the real rendered frame after the tutorial has settled.
        (dotimes (frame 180) (suspend))
        (pc-screen-shot))
          :name "spargus-prototype-capture"))
      (none))'''
target.write_text(text.replace(old, new), encoding='utf-8')
capture_path = Path('goal_src/jak3/pc/debug/capture-pc.gc')
capture = (ROOT.parents[1] / 'active/jak3/data' / capture_path).read_text(encoding='utf-8')
capture = capture.replace("'screen-shot-settings 1920 1080 16", "'screen-shot-settings 1920 1080 4")
(ROOT / 'data' / capture_path).write_text(capture, encoding='utf-8')
print('Prototype boot patched')
