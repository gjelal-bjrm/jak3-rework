"""Install a bounded, root-anchored palm movement in the native vertex shaders."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1];REL=Path('game/graphics/opengl_renderer/shaders')
helper='''// PALACE_FOLIAGE_BEGIN
uniform int palace_foliage;
uniform float palace_time;
vec3 palaceFoliagePosition(vec3 position,vec2 uv) {
  if(palace_foliage==0)return position;
  vec3 p=position/4096.0;
  float reach=clamp(1.0-uv.y,0.0,1.0);
  reach=reach*reach;
  float phase=dot(p.xz-vec2(2000,-440),vec2(.21,.17));
  float sway=.040*sin(palace_time*.85+phase)+.016*sin(palace_time*1.61+phase*.43);
  float flutter=.009*sin(palace_time*3.1+uv.x*13.0+uv.y*7.0+phase);
  return position+vec3(sway,.35*sway+flutter,.45*sway)*reach*4096.0;
}
// PALACE_FOLIAGE_END
'''
for name in ('tfrag3.vert','etie_base.vert','tie_wind.vert','shrub.vert'):
    path=ROOT/'data'/REL/name;source=path.read_text()
    source=re.sub(r'// PALACE_FOLIAGE_BEGIN.*?// PALACE_FOLIAGE_END\n?', '',source,flags=re.S)
    source=source.replace('  vec3 palace_position=palaceFoliagePosition(position_in,tex_coord_in.xy);\n','')
    source=source.replace('palace_position','position_in')
    head,body=source.split('void main() {',1)
    body=body.replace('position_in','palace_position')
    source=head+helper+'\nvoid main() {\n  vec3 palace_position=palaceFoliagePosition(position_in,tex_coord_in.xy);'+body
    for root in ('data','engine-src'):(ROOT/root/REL/name).write_text(source)
print('Palace palm movement installed; attachment points remain fixed')
