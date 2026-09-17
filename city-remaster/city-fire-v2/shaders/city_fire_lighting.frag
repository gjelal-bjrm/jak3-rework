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
  float s=fire_seeds[id]*17.83;
  return .83+.12*sin(fire_time*3.13+s)+.06*sin(fire_time*7.71+s*1.7)+.04*sin(fire_time*11.17+s*.3);
}

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
  for(int light_index=0;light_index<8;light_index++) {
    if(light_index>=fire_light_count)break;
    int i=fire_light_indices[light_index];
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
      distortion+=vec2(sin(q.y*11.0-fire_time*7.1+fire_seeds[i]),cos(q.y*8.0-fire_time*5.3))*plume*.7;
    }
  }
  vec2 shift=distortion/vec2(textureSize(tex_T25,0));
  vec2 shifted=clamp(uv+shift,vec2(.001),vec2(.999));
  if(abs(length(fireUnproject(shifted,texture(tex_T26,shifted).r)-eye)-length(P-eye))<1.0)
    scene=texture(tex_T25,shifted).rgb;
  color=vec4(scene+scene*light,1.0);
}
