"""Patch the existing arena renderer with a material scoped to the actual lava plane."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
shader=Path('game/graphics/opengl_renderer/shaders')
# Start from the accepted V1, so this script is repeatable and retains its lighting.
vert=(ROOT/'variants/remaster-v1'/shader/'tfrag3.vert').read_text(encoding='utf-8')
frag=(ROOT/'variants/remaster-v1'/shader/'tfrag3.frag').read_text(encoding='utf-8')
vert=vert.replace('out vec3 arena_world;', 'out vec3 arena_world;\nout vec3 lava_view;\nflat out int arena_lava;')
vert=vert.replace('arena_world = position_in / 4096.0;', '''arena_world = position_in / 4096.0;
  lava_view = cam_trans.xyz / 4096.0 - arena_world;
  // Exact bounds from wasstada-background.glb, animated material slot 99.
  arena_lava = (abs(arena_world.y - 9.999542) < 0.002 &&
    arena_world.x >= 2186.13 && arena_world.x <= 2466.15 &&
    arena_world.z >= -644.11 && arena_world.z <= -364.08) ? 1 : 0;''')
frag=frag.replace('in vec3 arena_world;', 'in vec3 arena_world;\nin vec3 lava_view;\nflat in int arena_lava;')
helper=(ROOT/'liquids-v2/lava-material.glsl').read_text(encoding='utf-8')
frag=frag.replace('void main() {',helper+'\nvoid main() {')
old='color = vec4(arena_light, fragment_color.a) * T0;'
assert frag.count(old)==1
frag=frag.replace(old,'''if (arena_lava == 1) {
      color = vec4(shadeArenaLava(tex_coord.xy, lava_view), fragment_color.a * T0.a);
    } else {
      color = vec4(arena_light, fragment_color.a) * T0;
    }''')
(ROOT/'data'/shader/'tfrag3.vert').write_text(vert,encoding='utf-8')
(ROOT/'data'/shader/'tfrag3.frag').write_text(frag,encoding='utf-8')
print('Lava material: original flow, parallax, animated normals, emission and highlights')
