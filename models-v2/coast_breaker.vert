#version 410 core
layout(location=0) in vec4 source_position_scale;
layout(location=1) in vec4 source_quaternion_scale;
layout(location=2) in vec4 source_color;
layout(location=3) in vec4 source_episode;
layout(location=4) in vec4 source_origin;
uniform mat4 ocean_camera;
uniform vec3 ocean_eye;
uniform float ocean_time;
out vec3 breaker_world;
out vec2 breaker_uv;
flat out vec4 breaker_episode;
flat out vec4 breaker_tint;
mat3 nativeRotation(vec3 q) {
  float w=sqrt(abs(1.-dot(q,q)));
  return mat3(1.-2.*(q.y*q.y+q.z*q.z),2.*(q.x*q.y+q.z*w),2.*(q.x*q.z-q.y*w),
              2.*(q.x*q.y-q.z*w),1.-2.*(q.x*q.x+q.z*q.z),2.*(q.y*q.z+q.x*w),
              2.*(q.x*q.z+q.y*w),2.*(q.y*q.z-q.x*w),1.-2.*(q.x*q.x+q.y*q.y));
}
void main() {
  const ivec2 corners[6]=ivec2[6](ivec2(0,0),ivec2(1,0),ivec2(1,1),ivec2(0,0),ivec2(1,1),ivec2(0,1));
  int cell=gl_VertexID/6;
  breaker_uv=(vec2(cell%48,cell/48)+vec2(corners[gl_VertexID%6]))/vec2(48.,12.);
  float u=breaker_uv.x,v=breaker_uv.y,age=source_episode.x;
  int kind=int(source_episode.y+.1);
  bool impact=kind==2;
  float envelope=clamp(source_color.a*(kind<2?22.:2.0),0.,1.);
  float seed=source_episode.z*.619;
  mat3 basis=nativeRotation(source_quaternion_scale.xyz);
  float width=abs(source_position_scale.w),height=abs(source_quaternion_scale.w);
  float irregular=(.024*sin(u*17.3+seed-age*1.7)+.014*sin(u*35.1-seed+age*2.2))*sin(v*3.141593);
  // Native approach and froth are horizontal. Actual impacts are the separate
  // group480 splash sprites; their yaw is recovered from nearby approach waves.
  vec3 p=source_position_scale.xyz+basis[0]*(u-.5)*width+basis[2]*(v-.5+irregular)*height;
  if(impact) {
    p=source_origin.xyz+basis[0]*(u-.5)*width;
    p.y=8.99;
    float localAge=age+.13*sin(u*11.7+seed);
    // A sharp run-up front, with no suspended plateau at its apex. The return
    // accelerates under the same 9.81 m/s² used by the detached spray particles.
    float riseTime=clamp(localAge/.38,0.,1.);
    float runUp=.25+.75*(2.*riseTime-riseTime*riseTime);
    float fallingTime=max(localAge-.38,0.);
    float fallingDistance=4.905*fallingTime*fallingTime;
    float collapse=clamp(fallingDistance/max(height*.86,.1),0.,1.);
    float rise=max(runUp-collapse,0.);
    p.y+=(v+irregular)*height*rise;
    // The upper lip curls seaward as the run-up reaches its peak. This changes
    // the actual silhouette, rather than enlarging a flat smoke-like billboard.
    float curl=pow(v,3.)*height*(.13+.12*collapse)*smoothstep(.08,.38,localAge);
    p.y-=pow(v,3.)*height*.10*collapse;
    p+=basis[2]*(sin(v*3.141593)*1.15+curl);   // basis[2] = vers le large : la levre retombe cote mer
    envelope*=1.-smoothstep(.88,1.,collapse);
  } else if(kind==3) {
    p.y=9.05+.10*sin(v*5.+age)*sin(u*7.+seed);
  } else {
    float crest=exp(-pow((v-.60-irregular)/.19,2.));
    p.y=9.015+crest*(kind==0 ? .40+1.0*envelope : .14+.32*envelope)*(0.80+.20*sin(u*12.3+seed));
    p+=basis[2]*crest*.22;
  }
  breaker_world=p;
  breaker_episode=vec4(age,source_episode.y,seed,envelope);
  breaker_tint=vec4(clamp(source_color.rgb*2.,vec3(.25),vec3(1.)),1.);
  gl_Position=-ocean_camera*vec4((p-ocean_eye)*4096.,1.);
  gl_Position.y*=(512./416.)*.5;
}
