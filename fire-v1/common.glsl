uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform float fire_time;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
vec3 fireProject(vec3 P) {
  vec4 h=-pc_camera*vec4(P*4096.0-cam_trans.xyz,1.0);
  h.y*=(512.0/416.0)*0.5;
  vec3 n=h.xyz/h.w;
  return vec3((fluid_viewport.xy+(n.xy*.5+.5)*fluid_viewport.zw)/vec2(textureSize(tex_T25,0)),n.z*.5+.5);
}
vec3 fireUnproject(vec2 uv,float depth) {
  vec4 h=vec4((uv*vec2(textureSize(tex_T25,0))-fluid_viewport.xy)/fluid_viewport.zw*2.0-1.0,depth*2.0-1.0,1.0);
  h.y/=(512.0/416.0)*0.5;
  vec4 w=inverse(-pc_camera)*h;
  return w.xyz/w.w/4096.0+cam_trans.xyz/4096.0;
}
float fireHash(vec3 p) {
  p=fract(p*.1031);p+=dot(p,p.yzx+33.33);
  return fract((p.x+p.y)*p.z);
}
float fireNoise(vec3 p) {
  vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
  return mix(mix(mix(fireHash(i),fireHash(i+vec3(1,0,0)),f.x),
                 mix(fireHash(i+vec3(0,1,0)),fireHash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(fireHash(i+vec3(0,0,1)),fireHash(i+vec3(1,0,1)),f.x),
                 mix(fireHash(i+vec3(0,1,1)),fireHash(i+vec3(1)),f.x),f.y),f.z);
}
float firePulse(int id) {
  float s=float(id)*17.83;
  return .83+.12*sin(fire_time*3.13+s)+.06*sin(fire_time*7.71+s*1.7)+.04*sin(fire_time*11.17+s*.3);
}
