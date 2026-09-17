"""Prepare palace-only fire volumes and retire their legacy particle layers."""
from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'fire-v1'
report=json.loads((ROOT/'desert-remaster/palace-fire.json').read_text())
fits={p['aid']:p for p in json.loads((HERE/'source-fit.json').read_text())['fits']}
settings={'group-waspala-crucible-fire':(.85,3.5),
          'group-waspala-wallfire':(1.20,5.0),'group-waspala-hanging-fire':(1.75,7.0)}
positions=[];shape=[];footprints=[];floors=[];planes=[]
for actor in report['actors']:
    x,y,z,_=actor['trans_m'];radius,height=settings[actor['group']]
    fit=fits[actor['aid']];y=fit['fuel_y']
    positions.append(f'vec4({x:.6f},{y:.6f},{z:.6f},{radius:.3f})')
    shape.append(f'{height:.3f}')
    footprints.append(f"{fit['fuel_radius']:.6f}")
    floors.append(f"{fit['fuel_floor']:.6f}")
    planes.extend('vec3('+','.join(f'{n:.8f}' for n in p)+')' for p in fit['fuel_planes'])
assert len(positions)==24
glsl='const int fire_count=24;\nconst vec4 fire_sources[24]=vec4[24]('+','.join(positions)+');\n'
glsl+='const float fire_heights[24]=float[24]('+','.join(shape)+');\n'
glsl+='const float fire_footprints[24]=float[24]('+','.join(footprints)+');\n'
glsl+='const float fire_floors[24]=float[24]('+','.join(floors)+');\n'
glsl+='const vec3 fire_fuel_planes[192]=vec3[192]('+','.join(planes)+');\n'
glsl+='''float fireFuelSurface(int id,vec2 xz) {
  float surface=-100.0;
  for(int face=0;face<8;face++) {
    vec3 plane=fire_fuel_planes[id*8+face];
    surface=max(surface,dot(plane.xy,xz)+plane.z);
  }
  return surface;
}
'''
(HERE/'positions.glsl').write_text(glsl)
path=ROOT/'data/goal_src/jak3/levels/wascity/palace/waspala-part.gc'
backup=HERE/'waspala-part-before-fire.gc'
if not backup.exists():shutil.copy2(path,backup)
source=path.read_text()
for n in (2731,2732,2733,2734,2736,2737,2738,2739,2740,2741):
    start=source.index(f'(defpart {n}\n');end=source.index('\n(defpart',start+1)
    block=source[start:end]
    block,count=re.subn(r'\(:num [^)]*\)','(:num 0.0)',block,count=1)
    assert count==1,n
    source=source[:start]+block+source[end:]
path.write_text(source)
for name in ('palace_fire.vert','palace_fire.frag','fire_lighting.vert','fire_lighting.frag',
             'fire_embers.vert','fire_embers.frag'):
    source=(HERE/name).read_text().replace('// FIRE_POSITIONS',glsl)
    source=source.replace('// FIRE_COMMON',(HERE/'common.glsl').read_text())
    for dest in (ROOT/'data/game/graphics/opengl_renderer/shaders',ROOT/'engine-src/game/graphics/opengl_renderer/shaders'):
        (dest/name).write_text(source)
print('Fire: 24 original actor positions, volume shaders, embers; 10 legacy palace particle layers retired')
