from pathlib import Path
import json
import shutil
import hashlib

ROOT = Path(__file__).resolve().parent
ACTIVE = ROOT.parents[1] / 'active/jak3/data'
DATA = ROOT / 'data'
files = [f'game/graphics/opengl_renderer/shaders/{shader}.{extension}'
         for shader in ('tfrag3', 'tie_wind', 'etie_base') for extension in ('vert', 'frag')]
files += ['out/jak3/fr3/wasstada.fr3', 'out/jak3/fr3/wasstadb.fr3', 'out/jak3/iso/WASSTADA.DGO']
for variant, source in (('original', ACTIVE), ('remaster', DATA)):
    for relative in files:
        target = ROOT / 'variants' / variant / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
(ROOT / 'variant-files.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
hashes = {variant: {relative: hashlib.sha256((ROOT / 'variants' / variant / relative).read_bytes()).hexdigest()
                    for relative in files} for variant in ('original', 'remaster')}
(ROOT / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')

# Both A/B profiles receive identical graphics settings and separate save directories.
profile_source = ROOT / 'profiles/original/OpenGOAL/jak3/settings'
for variant in ('original', 'remaster'):
    target = ROOT / 'profiles' / variant / 'OpenGOAL/jak3/settings'
    target.mkdir(parents=True, exist_ok=True)
    pc = (profile_source / 'pc-settings.gc').read_text(encoding='utf-8')
    import re
    replacements = {'msaa':'4', 'window-size':'1600 900', 'game-size':'1600 900',
                    'hires-clouds?':'#t', 'use-vis?':'#f', 'discord-rpc?':'#f'}
    for key, value in replacements.items():
        pc = re.sub(r'\(' + re.escape(key) + r' [^)]*\)', f'({key} {value})', pc)
    (target / 'pc-settings.gc').write_text(pc, encoding='utf-8')
    (target / 'display-settings.json').write_text(json.dumps({'version':'1.2','display_id':0,'display_mode':0,'window_xpos':50,'window_ypos':50}, indent=2), encoding='utf-8')
    inp = profile_source / 'input-settings.json'
    if variant != 'original' and inp.exists():
        shutil.copy2(inp, target / inp.name)
print('Original/remaster variants prepared with matching settings')
