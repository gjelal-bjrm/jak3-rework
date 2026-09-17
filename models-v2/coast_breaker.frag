#version 410 core
// Lame d'eau projetee contre un rocher : corps blanc charge d'air, base translucide, sommet dechire en doigts.
in vec3 breaker_world;
in vec2 breaker_uv;
flat in vec4 breaker_episode;
flat in vec4 breaker_tint;
uniform vec3 ocean_eye;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
out vec4 color;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){
  vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);
}
void main(){
  if(breaker_world.y<8.75)discard;
  float u=breaker_uv.x,v=breaker_uv.y,age=breaker_episode.x,seed=breaker_episode.z;
  int kind=int(breaker_episode.y+.1);
  if(kind!=2)discard;                       // seules les lames sur rochers sont dessinees
  float edge=smoothstep(0.,.10,u)*(1.-smoothstep(.90,1.,u));
  // Colonnes d'eau qui montent (bruit fin en largeur, etire en hauteur) et grain plus fin.
  float columns=noise(vec2(u*22.+seed,v*3.-age*2.2));
  float detail=noise(vec2(u*55.-seed,v*9.-age*4.));
  // Sommet dechire : hauteur du bord variable par colonne, doigts qui se separent.
  float top=.55+.40*noise(vec2(u*7.+seed,age*.7))+.08*noise(vec2(u*31.+seed,age*1.5));
  float body=smoothstep(top+.02,top-.14,v);
  // Base continue, puis colonnes distinctes separees par des trous : une nappe d'eau, pas un brouillard.
  float fingers=smoothstep(.38,.62,columns*.7+detail*.3);
  float coverage=body*mix(1.,fingers,smoothstep(.15,.45,v))*smoothstep(0.,.06,v);
  float streak=smoothstep(.62,.9,noise(vec2(u*40.+seed,v*2.-age*3.)));   // filets brillants qui montent
  // Air entraine : blanc dense vers le haut, eau verte translucide a la base.
  float aeration=clamp(smoothstep(.05,.55,v)*(.55+.45*detail)+streak*.35,0.,1.);
  vec3 normal=normalize(cross(dFdx(breaker_world),dFdy(breaker_world)));
  vec3 view=normalize(ocean_eye-breaker_world);
  if(dot(normal,view)<0.)normal=-normal;
  vec2 screen=(gl_FragCoord.xy-fluid_viewport.xy)/fluid_viewport.zw;
  vec2 bend=normal.xz*(.004+.003*detail);
  vec3 refracted=texture(tex_T25,clamp(screen+bend,vec2(.001),vec2(.999))).rgb;
  vec3 water=mix(refracted,vec3(.30,.44,.40),.35);
  vec3 white=vec3(.86,.90,.88)*mix(vec3(1.),breaker_tint.rgb,.15);
  vec3 light=normalize(vec3(-.32,.66,-.68));
  float rim=smoothstep(top-.18,top-.02,v)*(.5+.5*max(dot(normal,light),0.));
  vec3 rgb=mix(water,white,aeration)+vec3(.25,.22,.16)*rim;
  rgb*=mix(.72,1.,smoothstep(0.,.5,v));  // base plus sombre (eau chargee, moins eclairee)
  float alpha=coverage*mix(.5,.97,aeration)*edge*breaker_episode.w;
  float collapse=smoothstep(.55,1.5,age);   // la lame retombe et se disperse
  alpha*=1.-collapse*.55;
  float sceneDepth=texture(tex_T26,screen).r;
  float depthFade=clamp((gl_FragCoord.z-sceneDepth)/max(fwidth(gl_FragCoord.z)*1.7,0.000000025),0.,1.);
  alpha*=depthFade*(1.-smoothstep(150.,280.,length(ocean_eye-breaker_world)));
  if(alpha<.007)discard;
  color=vec4(rgb,alpha);
}
