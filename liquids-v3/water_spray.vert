#version 410 core
uniform vec4 fluid_contacts[32];
uniform float fluid_strength[32];
uniform float fluid_time;
uniform mat4 pc_camera;
uniform vec3 camera_position;
uniform float viewport_height;
uniform int fountain_active;
// IMPACT_POSITIONS
out float opacity;
float hash(float n) { return fract(sin(n*127.1)*43758.5453); }
void main() {
  int event = min(gl_VertexID/24,31);
  float seed = float(gl_VertexID)+fluid_contacts[event].w*7.7;
  float age = fluid_time-fluid_contacts[event].w;
  float energy = clamp(fluid_strength[event]/0.075,0.2,2.2);
  vec3 origin=fluid_contacts[event].xyz;
  bool active=fluid_strength[event]>0.0 &&
    (gl_VertexID%24 < (fluid_strength[event]>0.085 ? 24 : 10));
  bool impact=gl_VertexID>=32*24;
  if(impact) {
    int source=(gl_VertexID-32*24)/12;
    if(source>=water_impact_count || fountain_active==0) {
      gl_Position=vec4(2.0,2.0,2.0,1.0);gl_PointSize=1.0;opacity=0.0;return;
    }
    float phase=fluid_time*1.8+hash(float(gl_VertexID))*3.0;
    seed=float(gl_VertexID)+floor(phase)*17.3;
    age=fract(phase)*0.56;
    energy=0.60;
    origin=water_impacts[source];
    active=true;
  }
  float angle = hash(seed)*6.28318;
  vec2 direction = vec2(cos(angle),sin(angle));
  float vy = mix(1.2,2.8,hash(seed+19.0))*sqrt(energy);
  float life = 2.0*vy/9.8;
  if (!active || age<0.0 || age>life) {
    gl_Position = vec4(2.0,2.0,2.0,1.0);
    gl_PointSize=1.0; opacity=0.0; return;
  }
  vec3 P = origin;
  P.xz += direction*(0.19+age*mix(0.5,1.4,hash(seed+23.0)));
  P.y += 0.025+vy*age-4.9*age*age;
  gl_Position = -pc_camera*vec4(P*4096.0-camera_position,1.0);
  gl_Position.y *= (512.0/416.0)*0.5;
  gl_PointSize=clamp(viewport_height*(impact?0.055:0.075)*mix(0.45,1.0,hash(seed+2.0))
    /max(length(camera_position/4096.0-P),0.5),1.1,8.0);
  opacity=(1.0-smoothstep(life*0.65,life,age))*0.72;
}
