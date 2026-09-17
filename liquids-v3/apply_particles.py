"""Replace the remaining original flame geyser with molten ballistic droplets."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'data/goal_src/jak3/levels/wascity/wasstadium/wasstada-part.gc'
baseline=ROOT/'liquids-v3/wasstada-part-v2.gc'
if not baseline.exists():
    shutil.copy2(path,baseline)
source=baseline.read_text()
begin=source.index('(defpartgroup group-wasstada-lava-geyser-flame')
end=source.index('(defpartgroup group-wasstada-lava-steam')
replacement=''';; The old five-meter flame cards are replaced by smaller molten jets.
(defpartgroup group-wasstada-lava-geyser-flame
  :id 490
  :duration (seconds 3)
  :flags (sp0 sp4 sp9)
  :bounds (static-bspherem 0 0 0 10)
  :parts ((sp-item 1931 :fade-after (meters 100) :period (seconds 2.8) :length (seconds 0.18)))
  )

(defpart 1931
  :init-specs ((:texture (lava-drop-01 wasstada-sprite))
    (:birth-func 'birth-func-texture-group)
    (:num 1.0 1.5)
    (:x (meters -0.28) (meters 0.56))
    (:z (meters -0.28) (meters 0.56))
    (:scale-x (meters 0.10) (meters 0.18))
    (:rot-z (degrees -18) (degrees 36))
    (:scale-y (meters 0.20) (meters 0.30))
    (:r 128.0)
    (:g 128.0)
    (:b 128.0)
    (:a 128.0)
    (:vel-y (meters 0.065) (meters 0.055))
    (:rotvel-z (degrees -0.4) (degrees 0.8))
    (:fade-g -0.18)
    (:fade-b -0.40)
    (:fade-a -0.50)
    (:accel-y (meters -0.0027))
    (:timer (seconds 1.8))
    (:flags (launch-along-z))
    (:userdata :data (new 'static 'boxed-array :type int32 5 1 0 #x24f00000 #x24f00100 #x24f00200 #x24f00300))
    (:func 'check-drop-group-center)
    (:conerot-x (degrees 0) (degrees 22))
    (:rotate-y (degrees 0) (degrees 360))
    )
  )

'''
source=source[:begin]+replacement+source[end:]
start=source.index('(defpart 1932\n')
stop=source.index('(defpart 1933\n')
steam=source[start:stop]
for before,after in [
    ('(:scale-x (meters 3) (meters 3))','(:scale-x (meters 0.65) (meters 1.1))'),
    ('(:r 200.0 55.0)','(:r 145.0 20.0)'),
    ('(:g 60.0 60.0)','(:g 88.0 25.0)'),
    ('(:b 20.0)','(:b 58.0)'),
    ('(:fade-a 0.8)','(:fade-a 0.22)'),
    ('(:vel-y (meters 0.0033333334) (meters 0.0033333334))',
     '(:vel-y (meters 0.006) (meters 0.012))'),
]:
    assert before in steam,before
    steam=steam.replace(before,after)
source=source[:start]+steam+source[stop:]
assert '(sp-item 1935' not in source
path.write_text(source)
print('Geyser 1931 rebuilt: molten droplets, ballistic arcs, cooling; lighter steam; no floating crust')
