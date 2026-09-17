#version 410 core
// Nuage de sable : forme ronde erodee par du bruit (comme le sprite d'origine, en plus fin), grain,
// eclairage par le soleil (cote clair / cote ombre), fondu doux au contact du decor.
in vec2 drift_uv;
in float drift_alpha;
in float drift_seed;
in float drift_layer;
in vec3 drift_world;
in vec2 drift_light;
uniform float drift_time;
uniform vec3 drift_eye;
uniform vec3 drift_fog;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T26;
out vec4 color;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){
  vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);
}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<4;i++){v+=a*noise(p);p=p*2.07+vec2(3.1,1.7);a*=.5;}return v;}
void main(){
  vec2 uv=drift_uv;float t=drift_time,s=drift_seed;
  float r=length(uv);
  // Contour erode : le rayon varie avec un bruit lent (volutes) ; le sable tourbillonne doucement.
  float ang=atan(uv.y,uv.x);
  float edge=.72+.20*fbm(vec2(ang*1.6+s,t*.35+s*.7))-.08;
  float body=1.-smoothstep(edge-.35,edge,r);
  // Texture interne : volutes qui montent et derivent, grain fin.
  float volutes=fbm(uv*2.6+vec2(s,-t*.45+s*.3));
  float grain=noise(uv*22.+vec2(t*1.3,s*9.));
  float density=body*(.55+.45*smoothstep(.30,.75,volutes))*(.8+.2*grain);
  // Eclairage : plus clair vers le soleil, ombre douce a l oppose ; legere transparence au centre.
  float lit=.5+.5*dot(normalize(uv+vec2(.0001)),normalize(drift_light+vec2(.0001)))*min(r*1.4,1.);
  vec3 sandLit=vec3(.86,.78,.62),sandShade=vec3(.55,.47,.36);
  vec3 sand=mix(sandShade,sandLit,lit);
  float alpha=density*drift_alpha*(drift_layer<.5?.55:.42);
  // Particule douce : fondu au contact du sol et des murs.
  vec2 screen=(gl_FragCoord.xy-fluid_viewport.xy)/fluid_viewport.zw;
  float sceneDepth=texture(tex_T26,screen).r;
  alpha*=clamp((gl_FragCoord.z-sceneDepth)/max(fwidth(gl_FragCoord.z)*3.,0.00000004),0.,1.);
  alpha*=1.-smoothstep(90.,150.,length(drift_world-drift_eye));
  if(alpha<.006)discard;
  color=vec4(mix(sand,drift_fog,.18),alpha);
}
