#version 410 core
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform float fluid_time;
// FOUNTAIN_POSITIONS
out vec3 world;
out vec3 normal;
out vec2 flow_uv;
void main() {
  const int segments=64;
  const int sides=10;
  int jet=gl_VertexID/(segments*sides*6);
  int vertex=gl_VertexID%(segments*sides*6);
  int face=vertex/6;
  int segment=face/sides;
  int side=face%sides;
  const ivec2 corner[6]=ivec2[6](ivec2(0,0),ivec2(1,0),ivec2(1,1),ivec2(0,0),ivec2(1,1),ivec2(0,1));
  ivec2 c=corner[vertex%6];
  float s=float(segment+c.y)/float(segments);
  float a=float(side+c.x)/float(sides)*6.283185;
  vec3 start=fountain_start[jet],end=fountain_end[jet];
  float fall=mix(s,s*s,0.78);
  vec3 centre=vec3(mix(start.xz,end.xz,s).x,mix(start.y,end.y,fall),mix(start.xz,end.xz,s).y);
  vec3 tangent=normalize(vec3(end.x-start.x,(end.y-start.y)*(0.22+1.56*s),end.z-start.z));
  vec3 sideward=normalize(cross(tangent,vec3(0,1,0)));
  vec3 across=normalize(cross(tangent,sideward));
  float radius=mix(0.14,0.32,s)*(1.0+0.23*sin(s*69.0-fluid_time*9.0+a*3.0+float(jet))
    +0.10*sin(s*133.0-fluid_time*14.0-a*5.0));
  centre += sideward*sin(s*45.0-fluid_time*6.0+float(jet))*0.035*s;
  normal=sideward*cos(a)+across*sin(a);
  world=centre+normal*radius;
  flow_uv=vec2(a/6.283185,s);
  gl_Position=-pc_camera*vec4(world*4096.0-cam_trans.xyz,1.0);
  gl_Position.y *= (512.0/416.0)*0.5;
}
