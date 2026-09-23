#version 410 core
// Ciel moderne : triangle plein ecran ; le rayon de vue (axes monde, depuis l'oeil) est reconstruit
// depuis la matrice camera du prototype, comme la passe d'horizon de la mer.
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
