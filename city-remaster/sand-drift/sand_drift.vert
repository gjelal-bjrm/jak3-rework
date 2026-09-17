#version 410 core
// Sable porte par le vent : chaque bouffee native dirtpuff01 devient une nappe au ras du sol
// (couche 0) et un voile souleve face camera (couche 1), allonges dans le sens du vent.
layout(location=0) in vec4 source_position_scale;   // xyz (m), w = echelle native (m)
layout(location=1) in vec4 source_color;             // rgba natif (a = enveloppe de la bouffee)
layout(location=2) in vec4 source_extra;             // x = graine, y = echelle y
uniform mat4 drift_camera;
uniform vec3 drift_eye;
uniform float drift_time;
out vec2 drift_uv;
out float drift_alpha;
out float drift_seed;
out float drift_layer;
out vec3 drift_world;
void main(){
  const vec2 corners[6]=vec2[6](vec2(0,0),vec2(1,0),vec2(1,1),vec2(0,0),vec2(1,1),vec2(0,1));
  int layer=gl_VertexID/6;
  vec2 c=corners[gl_VertexID%6];drift_uv=c;
  float sx=abs(source_position_scale.w),seed=source_extra.x;
  vec2 wind=normalize(vec2(.12,1.));                 // vent de Spargus : vers +z (derive native)
  vec2 side=vec2(-wind.y,wind.x);
  vec3 centre=source_position_scale.xyz;
  vec3 p;
  if(layer==0){
    float L=3.6*sx+1.2,W=1.4*sx+.5;
    p=centre+vec3(wind.x,0.,wind.y)*(c.x-.5)*L+vec3(side.x,0.,side.y)*(c.y-.5)*W;
    p.y=centre.y-.35+.04*sin(seed*7.+drift_time*2.);
  } else {
    vec3 toEye=normalize(drift_eye-centre);
    vec3 right=normalize(cross(vec3(0.,1.,0.),toEye)+vec3(.0001,0.,0.));
    float W=2.4*sx+.8,H=.8+.45*sx;
    p=centre+right*(c.x-.5)*W+vec3(0.,c.y*H-.3,0.);
  }
  drift_world=p;
  drift_alpha=clamp(source_color.a*16.,0.,1.)*(layer==0?1.:.5);
  drift_seed=seed+float(layer)*13.7;
  drift_layer=float(layer);
  gl_Position=-drift_camera*vec4((p-drift_eye)*4096.,1.);
  gl_Position.y*=(512./416.)*.5;
}
