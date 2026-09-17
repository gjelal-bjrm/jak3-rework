"""Local effects changes, based on the untouched original GOAL sources."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT.parents[1]/'active/jak3/data'
BASE = Path('goal_src/jak3/levels/wascity')

def particle_edit(source, number, replacements):
    start = source.index(f'(defpart {number}\n')
    end = source.index('\n(def',start+1)
    block = source[start:end]
    for old,new in replacements:
        assert block.count(old)==1, (number,old)
        block = block.replace(old,new)
    return source[:start]+block+source[end:]

relative = BASE/'wasstadium/wasstada-obs.gc'
source = (ACTIVE/relative).read_text(encoding='utf-8')
for number, old_num, new_num, old_scale, new_scale in [
    (1928,'2.0 10.0','3.0 5.0','0.2) (meters 0.8','0.12) (meters 0.36'),
    (1929,'0.1 0.5','0.08 0.24','0.2) (meters 1','0.08) (meters 0.26')]:
    changes=[(f'(:num {old_num})',f'(:num {new_num})'),
             (f'(:scale-x (meters {old_scale}))',f'(:scale-x (meters {new_scale}))'),
             ('(:r 255.0)','(:r 128.0)'),('(:g 80.0 100.0)','(:g 128.0)'),('(:b 0.0)','(:b 128.0)'),
             # Particle fields must remain in increasing sp-field-id order.
             ('(:rotvel-z (degrees -2) (degrees 4))',
              '(:rotvel-z (degrees -0.6) (degrees 1.2))\n    (:fade-g -0.18)\n    (:fade-b -0.35)\n    (:fade-a -0.5)')]
    if number==1929:
        changes.append(('(:vel-y (meters 0.0016666667) (meters 0.013333334))',
                        '(:vel-y (meters 0.005) (meters 0.02))'))
    source=particle_edit(source,number,changes)
(ROOT/'data'/relative).write_text(source,encoding='utf-8')

relative = BASE/'wasstadium/wasstada-part.gc'
source = (ACTIVE/relative).read_text(encoding='utf-8')
# These flat, almost black sprites grow for seconds and look like detached shadows.
# Keep the genuine heat distortion (1934); cooled regions belong to the lava material.
old = ':parts ((sp-item 1934 :falloff-to (meters 100)) (sp-item 1935 :flags (is-3d)))'
assert source.count(old) == 1
source = source.replace(old, ':parts ((sp-item 1934 :falloff-to (meters 100)))')
source = particle_edit(source,1930,[
    ('(:num 2.0 10.0)','(:num 3.0 5.0)'),
    ('(:scale-x (meters 0.2) (meters 0.8))','(:scale-x (meters 0.12) (meters 0.36))'),
    ('(:r 255.0)','(:r 128.0)'),('(:g 80.0 100.0)','(:g 128.0)'),('(:b 0.0)','(:b 128.0)'),
    ('(:rotvel-z (degrees -2) (degrees 4))',
     '(:rotvel-z (degrees -0.6) (degrees 1.2))\n    (:fade-g -0.18)\n    (:fade-b -0.35)\n    (:fade-a -0.5)')])
(ROOT/'data'/relative).write_text(source,encoding='utf-8')

relative = BASE/'wasstadium/wasstada-texture.gc'
source = (ACTIVE/relative).read_text(encoding='utf-8')
weights=iter([0.70,0.70,0.20,0.20,0.10,0.10])
source,n=re.subn(r':w 0\.333\)',lambda m:f':w {next(weights):.2f})',source)
assert n==6
source=source.replace('float 2 0.5 3.25','float 2 0.5 1.25')
source=source.replace('float 2 -1.3 2.5','float 2 -1.3 1.5')
(ROOT/'data'/relative).write_text(source,encoding='utf-8')

relative=BASE/'palace/waspal-texture.gc'
source=(ACTIVE/relative).read_text(encoding='utf-8')
# Finer basin ripples, retaining the original layer clocks and seamless wraps.
cut=source.index(':tex-name "waspala-waterfall-dest"')
basin=source[:cut]
basin,n=re.subn(r'(:[a-z]+-st-scale \(new \'static \'vector2 :data \(new \'static \'array float 2 )1\.0 1\.0',r'\g<1>2.0 2.0',basin)
assert n==6,n
source=basin+source[cut:]
(ROOT/'data'/relative).write_text(source,encoding='utf-8')

relative=BASE/'palace/waspala-part.gc'
source=(ACTIVE/relative).read_text(encoding='utf-8')
changes={
2705:[('(:r 255.0)','(:r 100.0)'),('(:g 55.0 200.0)','(:g 120.0 10.0)'),('(:b 0.0 1 64.0)','(:b 145.0)')],
2706:[('(:r 45.0)','(:r 70.0)'),('(:g 35.0)','(:g 95.0)'),('(:b 30.0)','(:b 112.0)'),('(:scale-x (meters 0.4) (meters 0.7))','(:scale-x (meters 0.18) (meters 0.35))')],
2709:[('(:r 70.0)','(:r 58.0)'),('(:g 55.0)','(:g 86.0)'),('(:b 40.0)','(:b 104.0)'),('(:a 128.0)','(:a 70.0)')],
2710:[('(:r 70.0)','(:r 62.0)'),('(:g 55.0)','(:g 94.0)'),('(:b 40.0)','(:b 116.0)'),('(:a 32.0 120.0)','(:a 20.0 45.0)')],
}
for number,replacements in changes.items():
    source=particle_edit(source,number,replacements)
(ROOT/'data'/relative).write_text(source,encoding='utf-8')
print('Arena lava layers and droplets; palace water ripples and fountain spray patched')
