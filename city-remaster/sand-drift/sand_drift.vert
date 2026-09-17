#version 410 core
// Poussiere de Spargus : la bouffee native (sprite rond) est redessinee en un petit nuage de sable,
// deux lobes face camera (couche 0 : lobe principal, couche 1 : lobe secondaire decale), qui garde la
// taille, la position et l'enveloppe d'opacite de la particule d'origine.
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
out vec2 drift_light;    // direction du soleil projetee dans le plan du lobe
float hash1(float n){return fract(sin(n*127.1)*43758.5453);}
void main(){
  const vec2 corners[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(1,1),vec2(-1,-1),vec2(1,1),vec2(-1,1));
  int layer=gl_VertexID/6;
  vec2 c=corners[gl_VertexID%6];drift_uv=c;
  float sx=abs(source_position_scale.w),seed=source_extra.x;
  vec3 centre=source_position_scale.xyz;
  vec3 toEye=normalize(drift_eye-centre);
  vec3 right=normalize(cross(vec3(0.,1.,0.),toEye)+vec3(.0001,0.,0.));
  vec3 up=normalize(cross(toEye,right));
  float radius=sx*1.15;
  if(layer==1){
    // lobe secondaire : plus petit, decale selon la graine, un peu plus haut (le sable se souleve)
    float a=hash1(seed+3.)*6.2832;
    centre+=right*cos(a)*sx*.55+up*(.25+hash1(seed+5.)*.35)*sx;
    radius=sx*.75;
  }
  vec3 p=centre+right*c.x*radius+up*c.y*radius;
  drift_world=p;
  drift_alpha=clamp(source_color.a*16.,0.,1.)*(layer==0?1.:.7);
  drift_seed=seed+float(layer)*13.7;
  drift_layer=float(layer);
  vec3 sun=normalize(vec3(-.32,.66,-.68));
  drift_light=vec2(dot(sun,right),dot(sun,up));
  gl_Position=-drift_camera*vec4((p-drift_eye)*4096.,1.);
  gl_Position.y*=(512./416.)*.5;
}
