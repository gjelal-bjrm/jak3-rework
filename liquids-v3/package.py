"""Package tested V3; retain original/V1 shaders and the rejected V2 archive."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
SHADER='game/graphics/opengl_renderer/shaders/'
files=json.loads((ROOT/'variant-files.json').read_text())
hashes=json.loads((ROOT/'variant-hashes.json').read_text())
archive=ROOT/'variants/remaster-liquids-v2'
if not archive.exists():
    shutil.copytree(ROOT/'variants/remaster',archive)
    (ROOT/'liquids-v3/variant-hashes-before-v3.json').write_text(json.dumps(hashes,indent=2))
added=['generic.frag','merc2.frag','merc2.vert','liquid_bloom.vert','liquid_bloom.frag',
       'water_spray.vert','water_spray.frag','fountain.vert','fountain.frag','palace-shore.bin',
       'palace_fire.vert','palace_fire.frag','fire_lighting.vert','fire_lighting.frag',
       'fire_embers.vert','fire_embers.frag','shrub.vert','shrub.frag']
for name in added:
    relative=SHADER+name
    if relative not in files: files.append(relative)
    for variant in ('original','remaster-v1'):
        dest=ROOT/'variants'/variant/relative
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            if name in ('shrub.vert','shrub.frag'):
                source=ROOT/'terrain-v1/shaders-before-palace'/name
            elif name in ('generic.frag','merc2.frag','merc2.vert'):
                source=ROOT/'liquids-v3'/(Path(name).stem+'-original'+Path(name).suffix)
            else:
                # Unused by the official engine; included to keep snapshot switching complete.
                source=ROOT/'data'/relative
            shutil.copy2(source,dest)
        hashes[variant][relative]=hashlib.sha256(dest.read_bytes()).hexdigest()
# GOAL effects must switch with the renderer, including the official comparison.
palace='out/jak3/iso/WASPALA.DGO'
if palace not in files: files.append(palace)
for variant in ('original','remaster-v1'):
    dest=ROOT/'variants'/variant/palace
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT.parents[1]/'active/jak3/data'/palace,dest)
    hashes[variant][palace]=hashlib.sha256(dest.read_bytes()).hexdigest()
for relative in files:
    dest=ROOT/'variants/remaster'/relative
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'data'/relative,dest)
    hashes['remaster'][relative]=hashlib.sha256(dest.read_bytes()).hexdigest()
runtime=ROOT/'runtime/liquids-v3/gk.exe'
runtime.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'engine-build/bin/Release/gk.exe',runtime)
manifest={'base':'OpenGOAL v0.3.6','revision':'Prototype liquides V3',
          'runtime':runtime.relative_to(ROOT).as_posix(),
          'sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),
          'routes':{scene:hashlib.sha256((ROOT/'routes/remaster'/scene/'GAME.CGO').read_bytes()).hexdigest()
                    for scene in ('arena','palace')}}
(ROOT/'liquids-v3/runtime-manifest.json').write_text(json.dumps(manifest,indent=2))
(ROOT/'variant-files.json').write_text(json.dumps(files,indent=2))
(ROOT/'variant-hashes.json').write_text(json.dumps(hashes,indent=2))
print(f'Packaged V3: {len(files)} files and isolated runtime; original/V1 preserved')
