#version 410 core
// Rayon de mission : partie 0 = puits de lumiere (quad vertical tourne vers la camera autour de l'axe du
// rayon), partie 1 = lueur au sol (quad horizontal centre sur la base).
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform vec4 beam_base;      // xyz base (m), w rayon (m)
uniform int beam_part;
out vec3 world;
out vec2 local;              // partie 0 : x en travers (-1.3..1.3 rayons), y hauteur (m) ; partie 1 : x,z (rayons)
void main(){
  const vec2 c[6]=vec2[6](vec2(-1,0),vec2(1,0),vec2(1,1),vec2(-1,0),vec2(1,1),vec2(-1,1));
  vec2 k=c[gl_VertexID];
  vec3 base=beam_base.xyz;float r=beam_base.w;
  vec3 eye=cam_trans.xyz/4096.;
  if(beam_part==0){
    vec2 toEye=eye.xz-base.xz;
    vec2 side=length(toEye)>1e-3?normalize(vec2(-toEye.y,toEye.x)):vec2(1,0);
    float H=420.;
    float across=k.x*1.3;
    world=base+vec3(side.x*across*r,-1.5+k.y*H,side.y*across*r);
    local=vec2(across,k.y*H-1.5);
  }else{
    vec2 q=vec2(k.x,k.y*2.-1.)*3.2;
    world=base+vec3(q.x*r,.06,q.y*r);
    local=q;
  }
  gl_Position=-pc_camera*vec4(world*4096.-cam_trans.xyz,1.);
  gl_Position.y*=(512./416.)*.5;
}
