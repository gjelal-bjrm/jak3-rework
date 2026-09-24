#version 410 core
// Atmosphere meteo : triangle plein ecran ; rayon de vue reconstruit depuis la camera du prototype.
uniform mat4 pc_camera;
out vec3 view_ray;
void main(){
  vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
  vec2 clip=p*2.-1.;
  vec4 h=vec4(clip.x,clip.y/((512./416.)*.5),0.,1.);
  vec4 r=inverse(-pc_camera)*h;
  view_ray=r.xyz/r.w;
  gl_Position=vec4(clip,0.,1.);
}
