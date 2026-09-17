"""Idempotent palace material layer, also invoked after the liquid shader installer."""
from pathlib import Path
import re,shutil
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'terrain-v1'
REL=Path('game/graphics/opengl_renderer/shaders')
material_source=ROOT/'terrain-v2/materials.glsl'
if not material_source.exists():material_source=HERE/'materials.glsl'
helper=material_source.read_text()
backup=HERE/'shaders-before-palace';backup.mkdir(exist_ok=True)
call='    color.rgb = shadePalaceMaterial(color.rgb,T0.rgb,arena_world);'
glass_call='    if (palace_material==4) color.a *= mix(.48,1.0,smoothstep(.36,.49,T0.a));'
for name in ('tfrag3.frag','tie_wind.frag','etie_base.frag','shrub.frag','shrub.vert'):
    path=ROOT/'data'/REL/name
    if not (backup/name).exists():shutil.copy2(path,backup/name)
    source=path.read_text()
    source=re.sub(r'// PALACE_MATERIAL_BEGIN.*?// PALACE_MATERIAL_END\n?', '',source,flags=re.S)
    source=source.replace(call+'\n','')
    source=source.replace(glass_call+'\n','')
    source=source.replace('vec4 T0 = palaceAlbedo(tex_coord.xy);','vec4 T0 = texture(tex_T0, tex_coord.xy);')
    if name=='shrub.vert':
        if 'out vec3 arena_world;' not in source:
            source=source.replace('out vec4 fragment_color;','out vec3 arena_world;\nout vec4 fragment_color;')
            source=source.replace('void main() {','void main() {\n  arena_world=position_in/4096.0;')
    else:
        if name=='shrub.frag' and 'in vec3 arena_world;' not in source:
            source=source.replace('in vec4 fragment_color;','in vec3 arena_world;\nin vec4 fragment_color;')
        source=source.replace('void main() {',helper+'\nvoid main() {')
        anchor='color = fragment_color * T0;' if name=='shrub.frag' else 'color = vec4(arena_light, fragment_color.a) * T0;'
        assert source.count(anchor)==1,name
        source=source.replace(anchor,anchor+'\n'+call+'\n'+glass_call)
    for root in (ROOT/'data',ROOT/'engine-src'):(root/REL/name).write_text(source)
for name in ('tfrag3.vert','tie_wind.vert','etie_base.vert','shrub.vert'):
    path=ROOT/'data'/REL/name
    source=path.read_text()
    if 'out vec3 palace_smooth_normal;' not in source:
        source=source.replace('void main() {','layout (location = 5) in vec3 palace_normal_in;\nout vec3 palace_smooth_normal;\n\nvoid main() {\n  palace_smooth_normal=palace_normal_in;')
    if name in ('tfrag3.vert','etie_base.vert','tie_wind.vert'):
        if 'layout (location = 3) in vec4 palace_tie_normal;' not in source:
            source=source.replace('layout (location = 5)', 'layout (location = 3) in vec4 palace_tie_normal;\nlayout (location = 5)')
        source=source.replace('palace_smooth_normal=palace_normal_in;',
            'palace_smooth_normal=dot(palace_normal_in,palace_normal_in)>.1 ? palace_normal_in : palace_tie_normal.xyz;')
    for root in (ROOT/'data',ROOT/'engine-src'):(root/REL/name).write_text(source)
print('Palace materials: original palette, smooth natural-rock normals, surface relief and transparent glass')
foliage=ROOT/'models-v1/apply_foliage.py'
if foliage.exists():
    import runpy
    runpy.run_path(str(foliage))
