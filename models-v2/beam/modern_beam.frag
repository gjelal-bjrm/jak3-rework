#version 410 core
// Rayon de mission (remplace le cylindre jaune natif) : lumiere doree translucide et additive.
//  - epaisseur traversee d'un cylindre (plus lumineux au centre, bords qui s'effacent), coeur plus vif ;
//  - filets de lumiere qui montent lentement ; scintillement doux ;
//  - s'estompe en hauteur (reste visible de loin comme repere : renforce avec la distance) ;
//  - fondu doux la ou il traverse le sol ou un objet (profondeur de la scene) ;
//  - lueur au sol : halo doux et anneau qui pulse.
in vec3 world;
in vec2 local;
out vec4 color;
uniform sampler2D tex_T26;
uniform vec4 fluid_viewport;
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform vec4 beam_base;
uniform float beam_alpha;
uniform int beam_part;
uniform float beam_time;
float hash(vec2 p){vec3 q=fract(vec3(p.xyx)*.1031);q+=dot(q,q.yzx+33.33);return fract((q.x+q.y)*q.z);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
bool skyDepth(float d){const float s=1./16777215.;return d<=1.5*s||abs(d-400.*s)<=1.5*s;}
float sceneDistance(){
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T26,0));
  float d=texture(tex_T26,uv).r;
  if(skyDepth(d))return 1e6;
  vec2 px=uv*vec2(textureSize(tex_T26,0));
  vec4 h=vec4((px-fluid_viewport.xy)/fluid_viewport.zw*2.-1.,d*2.-1.,1.);
  h.y/=(512./416.)*.5;
  vec4 w=inverse(-pc_camera)*h;
  return length(w.xyz/w.w/4096.);
}
void main(){
  vec3 eye=cam_trans.xyz/4096.;
  float dist=length(world-eye);
  // fondu au contact du decor (pas d'arete nette la ou le rayon entre dans le sol)
  float soft=clamp((sceneDistance()-dist)/1.2,0.,1.);
  vec3 gold=vec3(1.,.82,.42);
  if(beam_part==0){
    float u=local.x,h=local.y;
    float thick=sqrt(max(0.,1.-u*u));
    float core=exp(-u*u*7.);
    float body=thick*.45+core*.75;
    // filets qui montent
    float n=noise(vec2(u*2.6+3.,h*.18-beam_time*1.1))*.6+noise(vec2(u*5.3,h*.45-beam_time*1.9)+7.)*.4;
    body*=.72+.55*n;
    // hauteur : fort pres du sol, s'efface en montant, fine trace jusqu'au ciel
    float up=exp(-max(h,0.)/38.)*.85+exp(-max(h,0.)/220.)*.22;
    up*=smoothstep(-1.5,.4,h);
    float far=mix(1.,2.4,smoothstep(40.,220.,dist));          // repere visible de loin
    float flick=.93+.07*sin(beam_time*3.1)+.04*sin(beam_time*7.3);
    float I=body*up*far*flick*beam_alpha*.55*soft;
    if(I<.002)discard;
    color=vec4(gold*I+vec3(1.,.95,.8)*core*up*I*.35,0.);
  }else{
    float r=length(local);
    float halo=exp(-r*r*.55)*.32;
    float pulse=fract(beam_time*.35);
    float ring=exp(-pow((r-(.6+pulse*2.4))/.22,2.))*(1.-pulse)*.35;
    float I=(halo+ring)*beam_alpha*smoothstep(3.2,2.4,r);          // au ras du sol : pas de fondu de contact
    if(I<.002)discard;
    color=vec4(gold*I,0.);
  }
}
