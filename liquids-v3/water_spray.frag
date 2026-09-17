#version 410 core
in float opacity;
out vec4 color;
void main() {
  vec2 p=gl_PointCoord*2.0-1.0;
  float r=dot(p,p);
  if (r>1.0) discard;
  float rim=pow(r,3.0)*0.4;
  float glint=exp(-dot(p-vec2(-0.3,-0.4),p-vec2(-0.3,-0.4))*22.0);
  vec3 tint=mix(vec3(0.33,0.41,0.40),vec3(0.85,0.91,0.88),rim+glint*0.85);
  color=vec4(tint,opacity*(1.0-smoothstep(0.60,1.0,r)));
}
