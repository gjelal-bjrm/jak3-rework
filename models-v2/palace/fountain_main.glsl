// Chutes du plafond du palais (v3) : retour au rendu d'eau claire et vitreuse prefere par l'utilisateur
// (on voit a travers, deforme), rendu un peu plus present : bords plus lumineux, filets plus visibles qui
// filent vers le bas, eclats des braseros, un peu d'eau aeree seulement vers le pied.
void main() {
  vec2 screen=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec2 q=vec2(flow_uv.x*15.0,flow_uv.y*38.0-fluid_time*8.5);
  float turbulence=fluidNoise(q)+0.35*fluidNoise(q*vec2(2.1,2.8));
  vec3 N=normalize(normal+vec3(
    fluidNoise(q+vec2(0.18,0.0))-fluidNoise(q-vec2(0.18,0.0)),
    fluidNoise(q+vec2(0.0,0.18))-fluidNoise(q-vec2(0.0,0.18)),
    fluidNoise(q+9.1)-0.5)*0.85);
  vec3 V=normalize(cam_trans.xyz/4096.0-world);
  if(dot(N,V)<0.0)N=-N;
  vec2 offset=fluidProject(world+N*0.10*(turbulence-0.3)).xy-fluidProject(world).xy;
  vec2 maxOffset=vec2(4.0)/vec2(textureSize(tex_T25,0));
  offset=clamp(offset,-maxOffset,maxOffset);
  vec2 uv=clamp(screen+offset,vec2(0.001),vec2(0.999));
  if(texture(tex_T26,uv).r>gl_FragCoord.z)uv=screen;
  vec3 behind=texture(tex_T25,uv).rgb;
  float edge=pow(1.0-max(dot(N,V),0.0),3.0);
  float foam=smoothstep(0.62,1.0,turbulence)*(0.30+flow_uv.y*0.55);
  vec3 reflection=mix(vec3(0.30,0.36,0.36),vec3(0.78,0.82,0.78),foam)*vec3(1.0,0.93,0.84);
  vec3 result=mix(behind*vec3(0.92,0.97,0.98),reflection,0.26+0.44*edge+foam*0.55);
  // pied de la chute : l'eau s'ouvre en gerbe blanche et bouillonnante juste avant l'eau du bassin
  float foot=smoothstep(0.90,0.995,flow_uv.y);
  float boil=fluidNoise(vec2(flow_uv.x*22.0,flow_uv.y*90.0-fluid_time*14.0))*0.6+fluidNoise(vec2(flow_uv.x*47.0,flow_uv.y*160.0-fluid_time*20.0))*0.4;
  result=mix(result,vec3(0.92,0.92,0.89)*vec3(1.0,0.95,0.88),foot*(0.55+0.45*smoothstep(0.35,0.75,boil)));
  float glint=pow(max(dot(N,normalize(V+vec3(-0.3,0.8,-0.2))),0.0),64.0);
  result+=vec3(1.0,0.82,0.55)*glint*0.55;
  float nearFade=smoothstep(0.5,2.2,length(cam_trans.xyz/4096.0-world));
  result=mix(texture(tex_T25,screen).rgb,result,nearFade);
  color=vec4(result,1.0);
}
