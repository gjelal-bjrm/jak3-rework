"""Package palace ImageGen masters without changing their painted colour or composition."""
from pathlib import Path
from PIL import Image, ImageStat
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'terrain-v1'
ORIGINAL=ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3/textures'
DEST=ROOT/'data/custom_assets/jak3/texture_replacements'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
snapshot=ROOT/'variants/remaster-before-palace'
if not snapshot.exists():
    shutil.copytree(ROOT/'variants/remaster',snapshot)
    shutil.copy2(ROOT/'variant-hashes.json',HERE/'variant-hashes-before-palace.json')

entries={}
for manifest in sorted(HERE.glob('*results.json')):
    for entry in json.loads(manifest.read_text()):
        entries[entry['key']]=entry
report=[]
for key,entry in entries.items():
    source=ORIGINAL/entry['page']/entry['file']
    master=HERE/'masters'/(key+'.png')
    master.parent.mkdir(exist_ok=True)
    if not master.exists():shutil.copy2(entry['generated_path'],master)
    original=Image.open(source).convert('RGBA')
    generated=Image.open(master).convert('RGB')
    # Uniform integer scale preserves the PS2 UV atlas layout. Alpha retains the
    # original leaf/glass silhouettes and the engine's 0..128 opacity convention.
    scale=min(8,max(1,1024//max(original.size)))
    size=(original.width*scale,original.height*scale)
    texture=generated.resize(size,Image.Resampling.LANCZOS)
    source_alpha=original.getchannel('A')
    alpha_min,alpha_max=source_alpha.getextrema()
    alpha=source_alpha.resize(size,Image.Resampling.BICUBIC).point(lambda value:min(alpha_max,max(alpha_min,value)))
    texture.putalpha(alpha)
    placements=[]
    for page in sorted(ORIGINAL.glob('waspala-*')):
        candidate=page/entry['file']
        if not candidate.exists():continue
        other=Image.open(candidate).convert('RGBA')
        if other.size!=original.size or other.tobytes()!=original.tobytes():continue
        output=DEST/page.name/entry['file']
        output.parent.mkdir(parents=True,exist_ok=True)
        texture.save(output,optimize=True)
        placements.append({'path':output.relative_to(DEST).as_posix(),'sha256':sha(output)})
    assert placements,entry['file']
    assert max(alpha.getextrema())<=128,entry['file']
    report.append({'key':key,'original':str(source),'original_sha256':sha(source),
                   'master':str(master),'master_sha256':sha(master),'tool':entry['tool'],
                   'prompt':entry['prompt'],'original_size':original.size,'size':size,
                   'original_mean_rgb':ImageStat.Stat(original.convert('RGB')).mean,
                   'master_mean_rgb':ImageStat.Stat(generated).mean,
                   'alpha_extrema':alpha.getextrema(),'placements':placements})
(HERE/'texture-validation.json').write_text(json.dumps(report,indent=2))
print(f'Palace: {len(report)} remastered materials, {sum(len(x["placements"]) for x in report)} placements; original liquid and fire textures preserved')
