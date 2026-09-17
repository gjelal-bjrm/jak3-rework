"""Install the new material shaders on top of the accepted scenery lighting."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SHADER = Path('game/graphics/opengl_renderer/shaders')
base = ROOT/'variants/remaster-v1'/SHADER
shore=(ROOT/'shore-v4/shoreline.glsl').read_text()
fire_reflection=(ROOT/'fire-v1/reflections.glsl').read_text().replace(
    '// FIRE_POSITIONS',(ROOT/'fire-v1/positions.glsl').read_text())
fluid=(ROOT/'liquids-v3/fluids.glsl').read_text().replace('// PALACE_FIRE_REFLECTION_HELPER',fire_reflection)
helper=shore+(ROOT/'liquids-v3/impact_positions.glsl').read_text()+fluid
vert = (base/'tfrag3.vert').read_text()
frag = (base/'tfrag3.frag').read_text()
def heated_scenery(source):
    old = 'return mix(baked, rebuilt, 0.62 * weight);'
    assert source.count(old)==1
    return source.replace(old, '''vec3 heatBounce = vec3(0.70,0.17,0.022)
      * exp(-max(p.y-10.0,0.0)/7.0) * weight * visibility
      * (0.45+0.55*max(-n.y,0.0));
  return mix(baked, rebuilt, 0.62 * weight)+heatBounce;''')
frag = heated_scenery(frag)
vert = vert.replace('uniform int decal;', 'uniform int decal;\nuniform int fluid_kind;\nuniform float fluid_time;')
vert = vert.replace('arena_world = position_in / 4096.0;', '''arena_world = position_in / 4096.0;
  vec3 fluid_position = position_in;
  if (fluid_kind == 1) {
    vec2 p = arena_world.xz-vec2(2320.0,-505.0);
    float rise = 0.105*sin(p.x*0.18+p.y*0.11+fluid_time*0.42)
               + 0.065*sin(p.y*0.23-p.x*0.07-fluid_time*0.31);
    fluid_position.y += rise*4096.0;
    arena_world.y += rise;
  }''')
vert = vert.replace('vec3 vert = position_in - cam_trans.xyz;', 'vec3 vert = fluid_position - cam_trans.xyz;')
frag = frag.replace('void main() {', helper+'\nvoid main() {')
frag = frag.replace('vec3 arena_light = arenaRelight(fragment_color.rgb, arena_world);',
'''vec3 arena_light = arenaRelight(fragment_color.rgb, arena_world);
  vec3 surface_normal = normalize(cross(dFdx(arena_world),dFdy(arena_world)));''')
old = 'color = vec4(arena_light, fragment_color.a) * T0;'
assert frag.count(old)==1
frag = frag.replace(old, '''if (fluid_kind == 1) {
      color = vec4(shadeModernLava(arena_world),1.0);
    } else if (fluid_kind == 2) {
      color = vec4(shadeModernWater(arena_world,surface_normal,
        T0*vec4(1.0,1.0,1.0,fragment_color.a*2.0)),1.0);
    } else {
      color = vec4(arena_light, fragment_color.a) * T0;
    }''')
# Refraction already includes the scene's fog. Applying fog twice washes out the basin.
frag = frag.replace('color.rgb = mix(color.rgb, fog_color.rgb, clamp(fogginess * fog_color.a, 0, 1));',
'''if (fluid_kind != 2)
    color.rgb = mix(color.rgb, fog_color.rgb, clamp(fogginess * fog_color.a, 0, 1));''')
generic_base = ROOT/'liquids-v3/generic-original.frag'
if not generic_base.exists():
    generic_base.write_text((ROOT/'data'/SHADER/'generic.frag').read_text())
generic = generic_base.read_text().replace('void main() {',
    helper+'''\nvoid main() {
  if (fluid_kind == 2) {
    vec2 uv = gl_FragCoord.xy / vec2(textureSize(tex_T25, 0));
    vec3 P = fluidUnproject(uv, gl_FragCoord.z);
    vec3 N = normalize(cross(dFdx(P), dFdy(P)));
    color = vec4(shadeModernWater(P, N, texture(tex_T0, tex_coord)), 1.0);
    return;
  }
''')
merc_base = ROOT/'liquids-v3/merc2-original.frag'
if not merc_base.exists():
    merc_base.write_text((ROOT/'data'/SHADER/'merc2.frag').read_text())
merc = merc_base.read_text().replace('void main() {',
    helper+'''\nvoid main() {
  if (fluid_kind == 2) {
    vec2 uv = gl_FragCoord.xy / vec2(textureSize(tex_T25, 0));
    vec3 P = fluidUnproject(uv, gl_FragCoord.z);
    vec3 N = normalize(cross(dFdx(P), dFdy(P)));
    color = vec4(shadeModernWater(P, N, texture(tex_T0, vtx_st)), 1.0);
    return;
  }
''')
merc_vert_base=ROOT/'liquids-v3/merc2-original.vert'
if not merc_vert_base.exists():
    merc_vert_base.write_text((ROOT/'data'/SHADER/'merc2.vert').read_text())
merc_vert=merc_vert_base.read_text().replace('void main() {','''
uniform int fluid_kind;
uniform float fluid_time;
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform vec4 fluid_contacts[32];
uniform float fluid_strength[32];
void main() {''')
merc_vert=merc_vert.replace('gl_Position = transformed;',
    'gl_Position = transformed;\n'+(ROOT/'liquids-v3/water_displacement.glsl').read_text())
for destination in (ROOT/'data'/SHADER, ROOT/'engine-src'/SHADER):
    (destination/'tfrag3.vert').write_text(vert)
    (destination/'tfrag3.frag').write_text(frag)
    (destination/'generic.frag').write_text(generic)
    (destination/'merc2.frag').write_text(merc)
    (destination/'merc2.vert').write_text(merc_vert)
    (destination/'fountain.vert').write_text((ROOT/'liquids-v3/fountain.vert').read_text().replace(
        '// FOUNTAIN_POSITIONS',(ROOT/'liquids-v3/fountain_positions.glsl').read_text()))
    (destination/'fountain.frag').write_text((ROOT/'liquids-v3/fountain.frag').read_text().replace(
        '// FLUID_HELPERS',helper))
    for name in ('liquid_bloom.vert','liquid_bloom.frag','water_spray.vert','water_spray.frag'):
        text=(ROOT/'liquids-v3'/name).read_text()
        if name=='water_spray.vert':
            text=text.replace('// IMPACT_POSITIONS',(ROOT/'liquids-v3/impact_positions.glsl').read_text())
        (destination/name).write_text(text)
    for name in ('tie_wind.frag','etie_base.frag'):
        (destination/name).write_text(heated_scenery((base/name).read_text()))
print('V3: per-pixel lava flow, water refraction, depth-aware SSR, caustics and contact foam')
import runpy
palace_installer=ROOT/'terrain-v1/apply_materials.py'
if palace_installer.exists():runpy.run_path(str(palace_installer))
