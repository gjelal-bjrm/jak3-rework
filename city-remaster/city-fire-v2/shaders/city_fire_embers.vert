#version 410 core
const int max_city_fires=64;
uniform int fire_count;
uniform vec4 fire_sources[max_city_fires];
uniform float fire_heights[max_city_fires];
uniform float fire_footprints[max_city_fires];
uniform float fire_seeds[max_city_fires];
uniform int fire_light_count;
uniform int fire_light_indices[8];
float fireFuelSurface(int id,vec2 xz) { return 0.0; }
float fireFloor(int id) { return 0.0; }

uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform float fire_time;
uniform float viewport_height;
out float heat;
void main() {
  int id=gl_VertexID/7,k=gl_VertexID%7;
  float seed=fire_seeds[id]*17.91+float(k)*2.73;
  float life=1.7+.4*sin(seed),age=mod(fire_time+seed,life);
  float r=fire_sources[id].w,H=fire_heights[id];
  vec3 p=fire_sources[id].xyz;
  p+=vec3(sin(seed)*r*.5,H*.22,cos(seed)*r*.5);
  p+=vec3(sin(age*2.7+seed)*age*.15,age*(.75+H*.22),cos(age*2.1+seed)*age*.12);
  gl_Position=-pc_camera*vec4(p*4096.0-cam_trans.xyz,1.0);
  gl_Position.y*=(512.0/416.0)*.5;
  float d=length(p-cam_trans.xyz/4096.0);
  gl_PointSize=clamp(viewport_height*.022/max(d,1.0),1.0,5.0);
  heat=(1.0-smoothstep(28.0,48.0,d))*smoothstep(0.0,.13,age)*(1.0-smoothstep(life*.3,life,age));
}
