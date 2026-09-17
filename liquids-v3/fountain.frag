#version 410 core
out vec4 color;
in vec3 world;
in vec3 normal;
in vec2 flow_uv;
// FLUID_HELPERS
void main() {
  vec2 screen=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec2 q=vec2(flow_uv.x*15.0,flow_uv.y*38.0-fluid_time*7.0);
  float turbulence=fluidNoise(q)+0.35*fluidNoise(q*vec2(2.1,2.8));
  vec3 N=normalize(normal+vec3(
    fluidNoise(q+vec2(0.18,0.0))-fluidNoise(q-vec2(0.18,0.0)),
    fluidNoise(q+vec2(0.0,0.18))-fluidNoise(q-vec2(0.0,0.18)),
    fluidNoise(q+9.1)-0.5)*0.85);
  vec3 V=normalize(cam_trans.xyz/4096.0-world);
  if(dot(N,V)<0.0)N=-N;
  vec2 offset=fluidProject(world+N*0.10*(turbulence-0.3)).xy-fluidProject(world).xy;
  vec2 maxOffset=vec2(3.0)/vec2(textureSize(tex_T25,0));
  offset=clamp(offset,-maxOffset,maxOffset);
  vec2 uv=clamp(screen+offset,vec2(0.001),vec2(0.999));
  if(texture(tex_T26,uv).r>gl_FragCoord.z)uv=screen;
  vec3 behind=texture(tex_T25,uv).rgb;
  float edge=pow(1.0-max(dot(N,V),0.0),4.0);
  float foam=smoothstep(0.65,1.03,turbulence)*(0.35+flow_uv.y*0.45);
  vec3 reflection=mix(vec3(0.23,0.30,0.30),vec3(0.69,0.76,0.73),foam);
  vec3 result=mix(behind,reflection,0.10+0.26*edge+foam*0.44);
  float glint=pow(max(dot(N,normalize(V+vec3(-0.3,0.8,-0.2))),0.0),64.0);
  result+=vec3(0.5,0.51,0.45)*glint*0.20;
  float nearFade=smoothstep(0.5,2.2,length(cam_trans.xyz/4096.0-world));
  result=mix(texture(tex_T25,screen).rgb,result,nearFade);
  color=vec4(result,1.0);
}
