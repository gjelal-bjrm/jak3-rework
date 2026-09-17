"""Derive fountain jets/impacts from the original level actors and tune their spray."""
from pathlib import Path
import json, re
ROOT=Path(__file__).resolve().parents[1]
actors=json.loads((ROOT/'data/decompiler_out/jak3/entities/waspala-actors.json').read_text())
jets={}; impacts={}; small=[]
for a in actors:
    name=a['lump'].get('art-name','')
    if 'group-waspala-water-spout' in name: jets[int(name[-1])]=a['trans'][:3]
    if 'group-waspala-water-splash' in name: impacts[int(name[-1])]=a['trans'][:3]
    if name=='group-waspala-waterfall-base': small.append(a['trans'][:3])
def vec(p): return 'vec3('+','.join(f'{x:.6f}' for x in p)+')'
# Two original splash group numbers are crossed; pair by the spouts' orientation.
ends=[impacts[i] for i in (1,2,4,3)]
out='const vec3 fountain_start[4]=vec3[4]('+','.join(vec(jets[i]) for i in range(1,5))+');\n'
out+='const vec3 fountain_end[4]=vec3[4]('+','.join(map(vec,ends))+');\n'
(ROOT/'liquids-v3/fountain_positions.glsl').write_text(out)
points=list(impacts.values())+small
out=f'const int water_impact_count={len(points)};\n'
out+=f'const vec3 water_impacts[{len(points)}]=vec3[{len(points)}]('+','.join(map(vec,points))+');\n'
(ROOT/'liquids-v3/impact_positions.glsl').write_text(out)
path=ROOT/'data/goal_src/jak3/levels/wascity/palace/waspala-part.gc'
backup=ROOT/'liquids-v3/waspala-part-before-fountains.gc'
if not backup.exists(): backup.write_text(path.read_text())
s=backup.read_text()
# The continuous jets are now geometry; remove the enormous flickering mist cards.
for n in range(1,5):
    start=s.index(f'(defpartgroup group-waspala-water-spout{n}')
    end=s.index('\n(defpart',start+1)
    block=s[start:end]
    block=re.sub(r'\(sp-item 2723[^\n]*\)\n    ', '', block)
    s=s[:start]+block+s[end:]
def change(n, replacements):
    global s
    start=s.index(f'(defpart {n}\n');end=s.index('\n(defpart',start+1)
    block=s[start:end]
    for old,new in replacements:
        assert old in block,(n,old)
        block=block.replace(old,new)
    s=s[:start]+block+s[end:]
# Foot of small waterfalls: scattered droplets and faint neutral spray.
change(2709,[('(:texture (dirtpuff01 level-default-sprite))','(:texture (water-drops level-default-sprite))'),
 ('(:num 4.0)','(:num 1.6)'),('(:scale-x (meters 0.1) (meters 0.1))','(:scale-x (meters 0.035) (meters 0.065))'),
 ('(:r 58.0)','(:r 92.0)'),('(:g 86.0)','(:g 100.0)'),('(:b 104.0)','(:b 102.0)'),
 ('(:a 70.0)','(:a 48.0)'),
 ('(:scalevel-x (meters 0.0033333334) (meters 0.0033333334))','(:scalevel-x (meters 0.0006))'),
 ('(:timer (seconds 0.135))','(:vel-y (meters 0.012) (meters 0.012))\n    (:vel-z (meters 0.006) (meters 0.008))\n    (:accel-y (meters -0.002))\n    (:fade-a -1.5)\n    (:timer (seconds 0.35))')])
change(2710,[('(:num 0.2)','(:num 0.07)'),('(:r 62.0)','(:r 90.0)'),('(:g 94.0)','(:g 97.0)'),('(:b 116.0)','(:b 98.0)'),('(:a 20.0 45.0)','(:a 8.0 10.0)'),('(:timer (seconds 2))','(:timer (seconds 0.75))')])
change(2705,[('(:scale-x (meters 1) (meters 5))','(:scale-x (meters 0.12) (meters 0.25))'),('(:r 100.0)','(:r 95.0)'),('(:g 120.0 10.0)','(:g 101.0 4.0)'),('(:b 145.0)','(:b 104.0)')])
change(2706,[('(:scale-x (meters 0.18) (meters 0.35))','(:scale-x (meters 0.045) (meters 0.10))'),('(:r 70.0)','(:r 92.0)'),('(:g 95.0)','(:g 100.0)'),('(:b 112.0)','(:b 103.0)')])
change(2724,[('(:scale-x (meters 0.4) (meters 0.7))','(:scale-x (meters 0.045) (meters 0.11))'),('(:r 45.0)','(:r 92.0)'),('(:g 35.0)','(:g 99.0)'),('(:b 30.0)','(:b 101.0)'),('(:a 32.0 120.0)','(:a 24.0 36.0)'),('(:scalevel-x (meters 0.0033333334))','(:scalevel-x (meters 0.0004))')])
change(2727,[('(:num 0.5)','(:num 0.10)'),('(:r 70.0)','(:r 96.0)'),('(:g 55.0)','(:g 102.0)'),('(:b 40.0)','(:b 103.0)'),('(:a 32.0 120.0)','(:a 12.0 15.0)'),('(:scalevel-x (meters 0.06666667) (meters 0.06666667))','(:scalevel-x (meters 0.015) (meters 0.01))')])
# GOAL's particle initializer requires increasing field IDs.
change(2709,[('(:a 48.0)\n    (:scalevel-x', '(:a 48.0)\n    (:vel-y (meters 0.012) (meters 0.012))\n    (:vel-z (meters 0.006) (meters 0.008))\n    (:scalevel-x'),
 ('(:scalevel-y :copy scalevel-x)\n    (:vel-y (meters 0.012) (meters 0.012))\n    (:vel-z (meters 0.006) (meters 0.008))\n    (:accel-y (meters -0.002))\n    (:fade-a -1.5)',
  '(:scalevel-y :copy scalevel-x)\n    (:fade-a -1.5)\n    (:accel-y (meters -0.002))')])
# Retire the old flat impact cards now that animated surface foam/spray replace them.
change(2710,[('(:num 0.07)','(:num 0.0)')])
change(2727,[('(:num 0.10)','(:num 0.0)')])
# Their small drops are now emitted in world space by water_spray, with gravity.
change(2709,[('(:num 1.6)','(:num 0.0)')])
change(2724,[('(:num 0.5 0.5)','(:num 0.0)')])
# Ceiling drips should not be metre-wide blinking cards.
change(2719,[('(:num 1.0 1.0)','(:num 0.0)')])
change(2720,[('(:scale-x (meters 0.5) (meters 1))','(:scale-x (meters 0.025) (meters 0.045))'),
 ('(:r 45.0)','(:r 92.0)'),('(:g 35.0)','(:g 99.0)'),('(:b 30.0)','(:b 101.0)'),
 ('(:a 32.0 120.0)','(:a 20.0 24.0)'),('(:scalevel-x (meters 0.0033333334))','(:scalevel-x (meters 0.0002))')])
path.write_text(s)
print(f'Fountains: 4 continuous jets, {len(points)} animated impact zones, finer spray')
