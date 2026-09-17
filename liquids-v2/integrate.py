"""Integrate generated liquid materials; preserve engine alpha conventions."""
from pathlib import Path
from PIL import Image
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT.parents[1] / 'active/jak3/data'
TEXTURES = ACTIVE / 'decompiler_out/jak3/textures'
DEST = ROOT / 'data/custom_assets/jak3/texture_replacements'
MASTER = ROOT / 'liquids-v2/masters'
MASTER.mkdir(exist_ok=True)
manifest = json.loads((ROOT/'liquids-v2/generation-manifest.json').read_text())
for item in manifest:
    source = Path(re.search(r'as (C:.*?\.png) by default', item['output_hint']).group(1))
    shutil.copy2(source, MASTER/(item['key']+'.png'))
report = []

def save(image, relative):
    path = DEST / relative
    path.parent.mkdir(parents=True,exist_ok=True)
    image.save(path)
    report.append({'file':relative,'size':list(image.size),'alpha_extrema':image.getchannel('A').getextrema(),
                   'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})

for key, relative in [('lava','wasstada-alpha/wstd-lava-base.png'),
                      ('water','waspala-water/waspala-water.png'),
                      ('waterfall','waspala-water/waspala-waterfall.png')]:
    original = Image.open(TEXTURES/relative).convert('RGBA')
    # These animated output sizes are fixed in this release of the renderer.
    # Keep matching source dimensions; new detail is designed to survive them.
    # The painted lava experiment was rejected. Its master is retained for history;
    # the dedicated lava material now consumes the original animated source.
    replacement = original.copy() if key == 'lava' else Image.open(MASTER/(key+'.png')).convert('RGBA').resize(original.size,Image.Resampling.LANCZOS)
    replacement.putalpha(original.getchannel('A'))
    save(replacement,relative)

atlas = Image.open(MASTER/'drops.png').convert('RGBA')
assert atlas.getchannel('A').getextrema() == (0,255), 'Real alpha channel required'
w,h = atlas.size
for i in range(4):
    x,y = (i%2)*w//2,(i//2)*h//2
    sprite = atlas.crop((x,y,x+w//2,y+h//2)).resize((128,128),Image.Resampling.LANCZOS)
    sprite.putalpha(sprite.getchannel('A').point(lambda a: round(a*128/255)))
    save(sprite,f'wasstada-sprite/lava-drop-{i+1:02}.png')

config = ROOT/'data/decompiler/config/jak3/ntsc_v1/inputs.jsonc'
source = config.read_text(encoding='utf-8')
source,n = re.subn(r'"levels_to_extract"\s*:\s*\[[^\]]*\]',
                   '"levels_to_extract": ["WASSTADA.DGO", "WASSTADB.DGO", "WASPALA.DGO"]',source)
assert n==1
config.write_text(source,encoding='utf-8')
(ROOT/'liquids-v2/texture-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(f'{len(report)} liquid textures integrated')
