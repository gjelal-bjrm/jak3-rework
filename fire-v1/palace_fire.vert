#version 410 core
// FIRE_POSITIONS
uniform mat4 pc_camera;
uniform vec4 cam_trans;
out vec3 proxy_world;
flat out int fire_id;
void main() {
  fire_id=gl_InstanceID;
  vec3 base=fire_sources[fire_id].xyz;
  float r=fire_sources[fire_id].w,H=fire_heights[fire_id];
  vec3 centre=base+vec3(0,H*.85,0);
  vec3 forward=normalize(centre-cam_trans.xyz/4096.0);
  vec3 right=normalize(cross(forward,vec3(0,1,0)));
  vec3 up=normalize(cross(right,forward));
  const vec2 corners[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(1,1),vec2(-1,-1),vec2(1,1),vec2(-1,1));
  // Conservative screen-facing proxy; density is evaluated in world-space volume.
  vec2 c=corners[gl_VertexID];
  proxy_world=centre+right*c.x*(r*2.4)+up*c.y*(H*1.05+r);
  gl_Position=-pc_camera*vec4(proxy_world*4096.0-cam_trans.xyz,1.0);
  gl_Position.y*=(512.0/416.0)*.5;
}
