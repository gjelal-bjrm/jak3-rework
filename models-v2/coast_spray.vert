#version 410 core
layout(location=0) in vec4 source_position_scale;
layout(location=1) in vec4 source_quaternion_scale;
layout(location=2) in vec4 source_color;
layout(location=3) in vec4 source_episode;
layout(location=4) in vec4 source_origin;
uniform mat4 ocean_camera;
uniform vec3 ocean_eye;
uniform vec4 fluid_viewport;
out vec2 droplet_uv;
out float opacity;
out float mist;
out vec3 droplet_world;
float hash(float n){return fract(sin(n*127.1)*43758.5453);}
mat3 nativeRotation(vec3 q) {
  float w=sqrt(abs(1.-dot(q,q)));
  return mat3(1.-2.*(q.y*q.y+q.z*q.z),2.*(q.x*q.y+q.z*w),2.*(q.x*q.z-q.y*w),
              2.*(q.x*q.y-q.z*w),1.-2.*(q.x*q.x+q.z*q.z),2.*(q.y*q.z+q.x*w),
              2.*(q.x*q.z+q.y*w),2.*(q.y*q.z-q.x*w),1.-2.*(q.x*q.x+q.y*q.y));
}
vec4 project(vec3 p){
  vec4 result=-ocean_camera*vec4((p-ocean_eye)*4096.,1.);
  result.y*=(512./416.)*.5;return result;
}
void main(){
  const vec2 corners[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(1,1),vec2(-1,-1),vec2(1,1),vec2(-1,1));
  float id=float(gl_VertexID/6),seed=source_episode.z*19.7+id*7.13;
  bool drops=int(source_episode.y+.1)==4;
  droplet_uv=corners[gl_VertexID%6];
  mist=id>=128.?1.:0.;                       // 128 gouttes, 64 bouffees de brume
  // One staggered burst per original impact episode, without cyclic respawn.
  float launchPhase=hash(seed+1.);
  float launch=.035+launchPhase*.34;
  float age=source_episode.x-launch;
  mat3 basis=nativeRotation(source_quaternion_scale.xyz);
  vec3 lateral=normalize(vec3(basis[0].x,0.,basis[0].z)+vec3(.0001,0,0));
  vec3 outward=normalize(-vec3(basis[2].x,0.,basis[2].z)+vec3(0,0,.0001));
  vec3 p=source_origin.xyz+lateral*(hash(seed+2.)-.5)*abs(source_position_scale.w)*.88;
  // Preserve the approved launch-height distribution while concentrating the
  // throw into the impact's first 0.375 s instead of feeding upward spray for 1.1 s.
  p.y=9.15+abs(source_quaternion_scale.w)*.32*smoothstep(0.,.80952381,launchPhase)+hash(seed+3.)*.85;
  float launchHeight=p.y-9.0;
  vec3 velocity=lateral*(hash(seed+4.)-.5)*3.4+outward*(.8+hash(seed+5.)*2.2);
  velocity.y=5.0+hash(seed+6.)*4.6;         // gouttes a 1,3-4,7 m de haut, pas au-dessus des maisons
  p+=velocity*max(age,0.);
  p.y-=4.905*max(age,0.)*max(age,0.);
  if(drops) {
    // These sources already have native upward velocity and gravity. Replace
    // each cloud by distinct drops following that ballistic source trajectory.
    p=source_position_scale.xyz+lateral*(hash(seed+2.)-.5)*min(abs(source_position_scale.w)*.65,2.5);
    p+=outward*(hash(seed+3.)-.5)*1.3;
    p.y+=(hash(seed+4.)-.5)*1.5;
  }
  vec3 currentVelocity=velocity-vec3(0,9.81*max(age,0.),0);
  droplet_world=p;
  vec4 centre=project(p),next=project(p+currentVelocity*.012);
  vec2 direction=normalize((next.xy/max(abs(next.w),.001)-centre.xy/max(abs(centre.w),.001))*fluid_viewport.zw+vec2(.001));
  vec2 side=vec2(-direction.y,direction.x);
  float distanceToEye=max(length(p-ocean_eye),.5);
  float radius=mix(.03+hash(seed+7.)*.04,.30+hash(seed+8.)*.35,mist);   // gouttes fines, pas de capsules
  vec2 extent=(side*droplet_uv.x+direction*droplet_uv.y*mix(1.65,1.,mist));
  centre.xy+=extent*vec2(1.,fluid_viewport.z/fluid_viewport.w)*radius/distanceToEye*centre.w;
  gl_Position=centre;
  float lifetime=(velocity.y+sqrt(velocity.y*velocity.y+19.62*launchHeight))/9.81;
  opacity=smoothstep(0.,.09,age)*(1.-smoothstep(lifetime*.68,lifetime,age));
  opacity*=clamp(source_color.a*2.4,0.,1.)*mix(.72,.16,mist);
  if(drops)opacity=clamp(source_color.a*2.4,0.,1.)*.62;
  opacity*=1.-smoothstep(110.,220.,distanceToEye);
  if((!drops&&(age<0.||age>lifetime))||p.y<9.0||(drops&&id>=28.))opacity=0.;
}
