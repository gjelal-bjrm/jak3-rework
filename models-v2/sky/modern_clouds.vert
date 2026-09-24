#version 410 core
// Nuages volumiques : triangle plein ecran dans le tampon demi-resolution ; rayon de vue reconstruit
// depuis la matrice camera du prototype (identique a modern_sky.vert).
uniform mat4 sky_camera;
out vec3 sky_ray;
void main(){
  vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
  vec2 clip=p*2.-1.;
  vec4 h=vec4(clip.x,clip.y/((512./416.)*.5),0.,1.);
  vec4 relative=inverse(-sky_camera)*h;
  sky_ray=relative.xyz/relative.w;
  gl_Position=vec4(clip,0.,1.);
}
