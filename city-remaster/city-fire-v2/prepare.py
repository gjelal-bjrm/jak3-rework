"""Generate city shaders from the accepted palace recipe without changing palace files."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SHADERS=('palace_fire.vert','palace_fire.frag','fire_lighting.vert','fire_lighting.frag','fire_embers.vert','fire_embers.frag')
NAMES={'palace_fire':'city_fire','fire_lighting':'city_fire_lighting','fire_embers':'city_fire_embers'}
def main():
    before={};outputs={}
    common=(ROOT/'fire-v1/common.glsl').read_text().replace('float s=float(id)*17.83;','float s=fire_seeds[id]*17.83;')
    positions=(HERE/'positions.glsl').read_text()
    for name in SHADERS:
      original=ROOT/'fire-v1'/name;before[str(original)]=hashlib.sha256(original.read_bytes()).hexdigest()
      source=original.read_text().replace('// FIRE_POSITIONS',positions).replace('// FIRE_COMMON',common)
      source=source.replace('fire_floors[fire_id]','fireFloor(fire_id)')
      source=source.replace('float seed=float(fire_id)*7.913;','float seed=fire_seeds[fire_id]*7.913;')
      source=source.replace('float seed=float(id)*17.91+float(k)*2.73;','float seed=fire_seeds[id]*17.91+float(k)*2.73;')
      if name=='palace_fire.frag':
        # Same 48-sample near volume; fewer samples only once the whole flame is small.
        source=source.replace('float stepSize=(farT-nearT)/48.0;','int samples=length(base-eye)>90.0 ? 24 : 48;\n  float stepSize=(farT-nearT)/float(samples);')
        source=source.replace('for(int i=0;i<48;i++,t+=stepSize) {','for(int i=0;i<48;i++,t+=stepSize) {\n    if(i>=samples)break;')
        source=source.replace('color=vec4(radiance,opacity);','float fade=1.0-smoothstep(200.0,300.0,length(base-eye));\n  color=vec4(radiance,opacity)*fade;')
      if name=='fire_lighting.frag':
        source=source.replace('for(int i=0;i<fire_count;i++) {','for(int light_index=0;light_index<8;light_index++) {\n    if(light_index>=fire_light_count)break;\n    int i=fire_light_indices[light_index];')
        source=source.replace('fire_time*7.1+float(i)','fire_time*7.1+fire_seeds[i]')
      if name=='fire_embers.vert':
        source=source.replace('heat=smoothstep','heat=(1.0-smoothstep(28.0,48.0,d))*smoothstep')
      newname=name
      for old,new in NAMES.items():
        if newname.startswith(old):newname=newname.replace(old,new,1);break
      dest=HERE/'shaders'/newname;dest.parent.mkdir(exist_ok=True);dest.write_text(source)
      outputs[newname]=hashlib.sha256(dest.read_bytes()).hexdigest()
    (HERE/'shader-provenance.json').write_text(json.dumps({'accepted_recipe_sources':before,'outputs':outputs,
      'changes':'Uniform active attachments, actor-stable phase, 8 nearby lights, 24 far samples, original 200–300 m fade; same near flame recipe, opaque clipping and premultiplied blend.'},indent=2)+'\n')
    print('Generated 6 city-only shaders; accepted palace shader files were not modified')
if __name__=='__main__':main()
