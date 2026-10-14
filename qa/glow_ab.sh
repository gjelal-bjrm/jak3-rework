# usage : glow_ab.sh scene prefixe "vue1" "vue2" ... -> qa/<prefixe>.png (avant | maintenant)
scene=$1; pre=$2; shift 2
cd "C:/Users/Gjelal/Documents/OpenGoal/prototypes/spargus-arena-v0.1"
(python -u launch.py remaster --replace --scene $scene --hour ${HOUR:-13} --time-ratio 0 --weather beau-temps > qa/launch-$scene-remaster.log 2>&1 &)
sleep 5; for i in $(seq 1 100); do grep -aq "vitesse\|Traceback\|Erreur" qa/launch-$scene-remaster.log && break; sleep 3; done; sleep 30
E="(define-extern pc-remaster-lighting (function int none))"; i=0
for v in "$@"; do for f in 1031 7; do python qa_live.py $scene $pre-$f-$i "--freecam=$v" --keep-freecam --eval "$E;;(pc-remaster-lighting $f)" --wait 1.5 >/dev/null 2>&1; done; i=$((i+1)); done
python qa_live.py $scene $pre-reset --eval "$E;;(pc-remaster-lighting 7);;(remove-setting-by-arg0 *setting-control* 'mode-name)" --wait .3 >/dev/null 2>&1
cd qa && python -c "
import sys
from PIL import Image, ImageDraw
n=int(sys.argv[2]); p=sys.argv[1]
s=Image.new('RGB',(1920,540*n)); d=ImageDraw.Draw(s)
for i in range(n):
  for c,f in enumerate((1031,7)):
    s.paste(Image.open(f'live-{p}-{f}-{i}-00.png').convert('RGB').resize((960,540)),(c*960,i*540)); d.text((c*960+8,i*540+8),('avant','maintenant')[c],fill=(255,255,0))
s.save(f'{p}.png')" $pre $#
