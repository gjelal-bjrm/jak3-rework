#version 410 core
// FIRE_POSITIONS
// FIRE_COMMON
out vec4 color;
void main() {
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  float depth=texture(tex_T26,uv).r;
  vec3 scene=texture(tex_T25,uv).rgb;
  if(depth<.00001){color=vec4(scene,1);return;}
  vec3 P=fireUnproject(uv,depth),eye=cam_trans.xyz/4096.0;
  vec3 V=normalize(eye-P),N=normalize(cross(dFdx(P),dFdy(P)));
  if(dot(N,V)<0.0)N=-N;
  vec3 light=vec3(0);vec2 distortion=vec2(0);
  vec3 ray=normalize(P-eye);
  for(int i=0;i<fire_count;i++) {
    vec3 source=fire_sources[i].xyz+vec3(0,fire_heights[i]*.28,0);
    vec3 delta=source-P;
    float d=length(delta),r=fire_sources[i].w;
    if(d<7.0) {
      float visible=1.0;
      for(int k=1;k<=4;k++) {
        vec3 probe=mix(P+N*.08,source,float(k)/5.0);
        vec3 projected=fireProject(probe);
        if(any(lessThan(projected.xy,vec2(.001)))||any(greaterThan(projected.xy,vec2(.999))))continue;
        float z=texture(tex_T26,projected.xy).r;
        if(z>projected.z && length(fireUnproject(projected.xy,z)-probe)>.3){visible=.05;break;}
      }
      float attenuation=(1.0-smoothstep(3.0,7.0,d))/(1.0+d*d*.7);
      light+=vec3(1.0,.30,.047)*max(dot(N,delta/max(d,.01)),0.0)*attenuation*firePulse(i)*visible*.38;
    }
    vec3 hotCentre=fire_sources[i].xyz+vec3(0,fire_heights[i]*.85,0);
    float along=dot(hotCentre-eye,ray);
    if(along>0.0 && along<length(P-eye)) {
      vec3 q=eye+along*ray-hotCentre;
      float plume=exp(-dot(q.xz,q.xz)/(r*r*.6)-q.y*q.y/(fire_heights[i]*fire_heights[i]*.5));
      distortion+=vec2(sin(q.y*11.0-fire_time*7.1+float(i)),cos(q.y*8.0-fire_time*5.3))*plume*.7;
    }
  }
  vec2 shift=distortion/vec2(textureSize(tex_T25,0));
  vec2 shifted=clamp(uv+shift,vec2(.001),vec2(.999));
  if(abs(length(fireUnproject(shifted,texture(tex_T26,shifted).r)-eye)-length(P-eye))<1.0)
    scene=texture(tex_T25,shifted).rgb;
  color=vec4(scene+scene*light,1.0);
}
