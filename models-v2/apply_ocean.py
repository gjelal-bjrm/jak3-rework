from pathlib import Path
import re,shutil,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
rel=Path('game/graphics/opengl_renderer/shaders');swell=(HERE/'ocean_swell.glsl').read_text()
helper=(HERE/'ocean.glsl').read_text().replace('// OCEAN_SWELL_INSERT',swell)
for name in ('ocean_common.frag','direct_basic_textured.frag'):
    path=ROOT/'data'/rel/name;old=HERE/'before'/name
    if not old.exists():shutil.copy2(path,old)
    source=old.read_text()
    source=source.replace('void main() {','uniform int modern_ocean;\nvoid main() {\n  if(modern_ocean!=0)discard;',1)
    for folder in ('data','engine-src'):(ROOT/folder/rel/name).write_text(source)
vertex='''#version 410 core
uniform mat4 ocean_camera;
uniform vec3 ocean_eye;
uniform float ocean_time;
uniform int ocean_horizon_pass;
out vec3 ocean_world;
'''+swell+'''
float radius(int row) {
  if(row<=64)return float(row)*1.5;
  if(row<=112)return 96.+float(row-64)*8.;
  if(row<=160)return 480.+float(row-112)*32.;
  // A logarithmic tail reaches the optical horizon without adding triangles.
  // The former 10,208 m edge exposed the legacy far-ocean fill behind it.
  return exp2(mix(log2(2016.),20.,float(row-160)/32.));
}
void main() {
  if(ocean_horizon_pass!=0) {
    vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
    vec2 clip=p*2.-1.;
    vec4 h=vec4(clip.x,clip.y/((512./416.)*.5),0.,1.);
    vec4 relative=inverse(-ocean_camera)*h;
    // Unnormalised rays interpolate linearly at a fixed projected depth.
    // Invert the uniform camera at three vertices, not at every screen pixel.
    ocean_world=relative.xyz/relative.w;
    gl_Position=vec4(clip,0.,1.);return;
  }
  const ivec2 corner[6]=ivec2[6](ivec2(0,0),ivec2(1,0),ivec2(1,1),ivec2(0,0),ivec2(1,1),ivec2(0,1));
  int cell=gl_VertexID/6;ivec2 c=corner[gl_VertexID%6];
  int row=cell/384+c.x;int sector=cell%384+c.y;
  float angle=float(sector)*6.28318530718/384.;
  vec2 centre=floor(ocean_eye.xz/8.)*8.;
  vec2 xz=centre+radius(row)*vec2(cos(angle),sin(angle));
  float meshFootprint=max(radius(row)*6.28318530718/384.,(radius(min(row+1,192))-radius(max(row-1,0)))*.5);
  vec3 wave=oceanSwellFiltered(xz,meshFootprint);
  wave+=oceanContacts(xz)*(1.-smoothstep(2.,5.,meshFootprint));
  ocean_world=vec3(xz.x,9.+wave.x,xz.y);
  gl_Position=-ocean_camera*vec4((ocean_world-ocean_eye)*4096.,1.);
  gl_Position.y*=(512./416.)*.5;
  // OpenGOAL's finite world projection clips at the original far depth. The
  // regional sea extends beyond that depth, like the original sky-based ocean.
  // Clamp only its far Z, retain near clipping, and leave foreground Z intact.
  if(gl_Position.w>0.)gl_Position.z=max(gl_Position.z,gl_Position.w*(-1.+2.e-7));
}
'''
fragment='#version 410 core\n#define OCEAN_SURFACE_GEOMETRY\nout vec4 color;\nuniform vec4 fog_color;\n'+helper+'''
void main() {
  gl_FragDepth=gl_FragCoord.z;
  if(ocean_horizon_pass!=0)color=shadeOceanHorizon();
  else {
    if(!oceanContainsPoint(ocean_world.xz))discard;
    gl_FragDepth=oceanVisibleDepth(gl_FragCoord.z);
    color=vec4(shadeModernOcean(),1.);
  }
}
'''
for name,source in (('modern_ocean_surface.vert',vertex),('modern_ocean_surface.frag',fragment)):
    for folder in ('data','engine-src'):(ROOT/folder/rel/name).write_text(source)
extra=('ocean_underwater.vert','ocean_underwater.frag','coast_spray.vert','coast_spray.frag',
       'coast_breaker.vert','coast_breaker.frag')
for name in extra:
    for folder in ('data','engine-src'):
        shutil.copy2(HERE/name,ROOT/folder/rel/name)
files=json.loads((ROOT/'variant-files.json').read_text());hashes=json.loads((ROOT/'variant-hashes.json').read_text())
import hashlib
for name in ('ocean_common.frag','direct_basic_textured.frag','modern_ocean_surface.vert','modern_ocean_surface.frag')+extra:
    relative=(rel/name).as_posix()
    if relative not in files:files.append(relative)
    for variant in ('original','remaster-v1'):
        target=ROOT/'variants'/variant/relative
        if not target.exists():shutil.copy2(HERE/'before'/name if (HERE/'before'/name).exists() else ROOT/'data'/rel/name,target)
        hashes[variant][relative]=hashlib.sha256(target.read_bytes()).hexdigest()
(ROOT/'variant-files.json').write_text(json.dumps(files,indent=2))
(ROOT/'variant-hashes.json').write_text(json.dumps(hashes,indent=2))
print('Spargus ocean optical shader installed in near, middle and far native paths')
