#version 410 core
in float heat;
out vec4 color;
void main() {
  vec2 p=gl_PointCoord*2.0-1.0;
  float a=(1.0-smoothstep(.1,1.0,dot(p,p)))*heat;
  if(a<.01)discard;
  color=vec4(mix(vec3(.65,.055,.005),vec3(1.0,.50,.10),heat)*a,a);
}
