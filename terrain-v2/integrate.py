"""Integrate the revised palace set, including native high-resolution leaf alpha."""
from pathlib import Path
from PIL import Image
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'terrain-v2'
ORIGINAL=ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/textures'
DEST=ROOT/'data/custom_assets/jak3/texture_replacements'
entries={}
for directory in (ROOT/'terrain-v1',HERE):
    for manifest in sorted(directory.glob('*results.json')):
        for entry in json.loads(manifest.read_text()):
            entry=dict(entry)
            master=directory/'masters'/(entry['key']+'.png');master.parent.mkdir(exist_ok=True)
            if not master.exists():shutil.copy2(entry['generated_path'],master)
            entry['master']=str(master);entries[entry['key']]=entry
report=[]
for key,entry in entries.items():
    source=ORIGINAL/entry['page']/entry['file']
    original=Image.open(source).convert('RGBA')
    generated=Image.open(entry['master']).convert('RGBA')
    longest=1024
    scale=longest/max(original.size)
    size=tuple(round(v*scale) for v in original.size)
    if entry.get('alpha')=='generated_cutout':
        assert generated.getchannel('A').getextrema()[0]==0, key+' has no cutout alpha'
        texture=generated.resize(size,Image.Resampling.LANCZOS)
        texture.putalpha(texture.getchannel('A').point(lambda a:round(a*128/255)))
    else:
        texture=generated.convert('RGB').resize(size,Image.Resampling.LANCZOS)
        low,high=original.getchannel('A').getextrema()
        alpha=original.getchannel('A').resize(size,Image.Resampling.BICUBIC).point(lambda a:min(high,max(low,a)))
        texture.putalpha(alpha)
    placements=[]
    for page in ORIGINAL.glob('waspala-*'):
        candidate=page/entry['file']
        if not candidate.exists():continue
        other=Image.open(candidate).convert('RGBA')
        if other.size!=original.size or other.tobytes()!=original.tobytes():continue
        dest=DEST/page.name/entry['file'];dest.parent.mkdir(parents=True,exist_ok=True)
        texture.save(dest,optimize=True)
        placements.append({'path':dest.relative_to(DEST).as_posix(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    assert placements and texture.getchannel('A').getextrema()[1]<=128,key
    report.append({**entry,'size':size,'original_size':original.size,'placements':placements,
      'alpha_mode':entry.get('alpha','source'),'alpha_range':texture.getchannel('A').getextrema()})
(HERE/'texture-validation.json').write_text(json.dumps(report,indent=2))
print(f'Revised palace: {len(report)} textures, {sum(e["alpha_mode"]=="generated_cutout" for e in report)} new foliage cutouts')
