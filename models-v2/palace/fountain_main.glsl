// Chutes du plafond du palais (v2) : eau aeree qui tombe de 23 m. Elle accelere (les filets
// s'etirent et filent de plus en plus vite), blanchit, puis se defait en filets et en trous vers le bas ;
// on voit a travers, deforme. Eclairage chaud des braseros et de la verriere.
void main() {
  vec2 screen=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  float s=flow_uv.y;                                   // 0 en haut, 1 au pied de la chute
  float speed=5.0+11.0*s;                              // chute libre : de plus en plus vite
  vec2 q=vec2(flow_uv.x*24.0,s*13.0-fluid_time*speed*0.55);          // longs filets verticaux
  float strands=fluidNoise(q)*0.6+fluidNoise(q*vec2(2.3,1.7)+5.1)*0.4;
  float fine=fluidNoise(q*vec2(4.1,3.2)+9.7);
  vec3 bump=vec3(fluidNoise(q+vec2(0.2,0.0))-fluidNoise(q-vec2(0.2,0.0)),0.0,
                 fluidNoise(q+vec2(0.0,0.2))-fluidNoise(q-vec2(0.0,0.2)));
  vec3 N=normalize(normal+bump*0.9);
  vec3 V=normalize(cam_trans.xyz/4096.0-world);
  if(dot(N,V)<0.0)N=-N;
  float facing=max(dot(normalize(normal),V),0.0);
  // Longues stries verticales qui filent vers le bas ; peu de contraste (eau aeree, pas de taches).
  float streak=fluidNoise(vec2(flow_uv.x*18.0,s*6.0-fluid_time*speed*0.30))*0.5
              +fluidNoise(vec2(flow_uv.x*40.0,s*14.0-fluid_time*speed*0.62)+3.0)*0.5;
  float white=0.60+0.40*smoothstep(0.20,0.85,streak);
  float breakup=smoothstep(0.35,1.0,s);
  // en haut l'eau sort claire (vitreuse), elle blanchit en tombant, se desagrege un peu en bas
  float opacity=mix(0.28,0.82,smoothstep(0.02,0.30,s))*(1.0-0.40*breakup*(1.0-streak));
  opacity*=smoothstep(0.0,0.55,facing);                 // silhouette douce
  // ce qu'on voit a travers, deforme par l'eau
  vec2 offset=fluidProject(world+N*0.12*(streak-0.5)).xy-fluidProject(world).xy;
  vec2 maxOffset=vec2(6.0)/vec2(textureSize(tex_T25,0));
  offset=clamp(offset,-maxOffset,maxOffset);
  vec2 uv=clamp(screen+offset,vec2(0.001),vec2(0.999));
  if(texture(tex_T26,uv).r>gl_FragCoord.z)uv=screen;
  vec3 behind=texture(tex_T25,uv).rgb;
  vec3 light=vec3(0.82,0.72,0.60);                     // salle sombre eclairee par les braseros
  vec3 waterCol=vec3(0.92,0.93,0.90)*white*light;
  vec3 result=mix(behind*vec3(0.90,0.95,0.97),waterCol,opacity);
  float solid=opacity;
  // eclats dores sur les filets (lumiere des braseros)
  float glint=pow(max(dot(N,normalize(V+vec3(-0.3,0.8,-0.2))),0.0),56.0);
  result+=vec3(1.0,0.78,0.45)*glint*0.45*solid;
  float nearFade=smoothstep(0.5,2.2,length(cam_trans.xyz/4096.0-world));
  result=mix(texture(tex_T25,screen).rgb,result,nearFade);
  color=vec4(result,1.0);
}
