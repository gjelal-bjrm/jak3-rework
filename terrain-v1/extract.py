"""Rebuild native FR3 assets from the user's extracted ISO, without compiling GOAL code."""
from pathlib import Path
import subprocess,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
protected=[DATA/p for p in ('out/jak3/iso/WASPALA.DGO','out/jak3/iso/GAME.CGO',
                           'goal_src/jak3/levels/wascity/palace/waspala-part.gc',
                           'game/graphics/opengl_renderer/shaders/palace_fire.frag')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p):sha(p) for p in protected}
exe=ROOT.parents[1]/'versions/official/v0.3.6/extractor.exe'
with (ROOT/'terrain-v1/extraction.log').open('w') as log:
    result=subprocess.run([str(exe),str(DATA/'iso_data/jak3'),'--game','jak3','--proj-path',str(DATA),
                           '--folder','--decompile'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,f'Extractor exited {result.returncode}; see terrain-v1/extraction.log'
assert all(sha(Path(p))==value for p,value in before.items()),'GOAL or shader changed during texture extraction'
# Texture extraction rebuilds original topology. Reapply authored Blender models
# before packaging so a later HD texture does not silently erase the new shapes.
models=ROOT/'models-v1'
if (models/'native-model-validation.json').exists():
    import sys,shutil
    level=DATA/'out/jak3/fr3/waspala.fr3'
    clean=models/'waspala-after-texture-extraction.fr3';shutil.copy2(level,clean)
    result=subprocess.run([sys.executable,str(models/'apply_models.py'),str(clean),str(level)])
    assert result.returncode==0,'Blender model reapplication failed'
report={'protected_files_unchanged':before,
        'levels':{p.name:sha(p) for p in (DATA/'out/jak3/fr3').glob('*.fr3') if p.stem in ('waspala','wasstada','wasstadb','game')}}
(ROOT/'terrain-v1/extraction-validation.json').write_text(json.dumps(report,indent=2))
print('FR3 extraction completed; accepted GOAL effects and fire shader unchanged')
