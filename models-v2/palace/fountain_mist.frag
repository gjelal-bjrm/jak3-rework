#version 410 core
// Voile de brume des quatre chutes du palais (remplace les grandes cartes de brume de l'original) :
//  - une gaine de gouttelettes autour de chaque chute, fine en haut, large en bas ;
//  - un nuage d'embruns au pied de chaque chute, qui roule au ras de l'eau ;
//  - bruit 3D qui descend avec l'eau et se disperse ; eclairage chaud des braseros.
// Marche de rayon limitee par la profondeur de la scene. On voit a travers : le decor derriere est
// legerement trouble et tremble dans la brume.
in vec3 view_ray;
out vec4 color;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
uniform vec4 fluid_viewport;
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform float fluid_time;
// FOUNTAIN_POSITIONS

bool skyDepth(float d){const float s=1./16777215.;return d<=1.5*s||abs(d-400.*s)<=1.5*s;}
vec3 unproject(vec2 uv,float depth){
  vec2 pixel=uv*vec2(textureSize(tex_T26,0));
  vec4 h=vec4((pixel-fluid_viewport.xy)/fluid_viewport.zw*2.-1.,depth*2.-1.,1.);
  h.y/=(512./416.)*.5;
  vec4 w=inverse(-pc_camera)*h;
  return w.xyz/w.w/4096.;
}
float hash(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 x){
  vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);
  return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
vec3 gLo,gHi;   // boite de calcul (posee par main)
// Densite de brume au point p (m) : somme des quatre chutes, nulle en approchant des faces de la boite
// (sinon la brume est coupee net : bande verticale a bord droit).
float mist(vec3 p){
  vec3 inside=min(p-gLo,gHi-p);
  float boxFade=smoothstep(0.,2.5,min(inside.x,inside.z))*smoothstep(0.,.8,min(inside.y,99.));
  if(boxFade<=0.)return 0.;
  float sheathSum=0.,cloudSum=0.;
  for(int k=0;k<4;k++){
    vec3 A=fountain_start[k],B=fountain_end[k];
    float h=clamp((A.y-p.y)/(A.y-B.y),0.,1.);                 // fraction de la hauteur de chute
    float s=(-.22+sqrt(.0484+3.12*h))/1.56;                    // inverse de fall=mix(s,s*s,.78)
    vec2 axis=mix(A.xz,B.xz,s);
    vec2 dxz=p.xz-axis;
    float R=.8+3.2*pow(h,1.5);                                 // gaine d'embruns : large en bas (jusqu'a 4 m)
    sheathSum+=exp(-dot(dxz,dxz)/(R*R))*smoothstep(.05,.35,h)*(1.-smoothstep(1.,1.08,h));
    vec3 e=p-B;
    float up=max(e.y+.2,0.);
    cloudSum+=exp(-dot(e.xz,e.xz)/5.5-up*up/1.6)*step(-.4,e.y);   // embruns au pied
  }
  // nappe basse sur les bassins, entre les chutes
  vec2 c=(fountain_end[0].xz+fountain_end[1].xz+fountain_end[2].xz+fountain_end[3].xz)*.25;
  vec2 o=p.xz-c;
  float low=max(p.y-fountain_end[0].y+.3,0.);
  float lowSum=(1.-smoothstep(3.,7.,length(o)))*exp(-low*low/2.5);
  // rideau d'embruns entre les chutes (la ou l'original avait ses cartes de brume) : fine pluie qui tombe
  // du plafond, plus dense en bas, bords doux
  vec3 cLo=vec3(1987.,241.5,-456.),cHi=vec3(2011.,262.,-438.8);
  vec3 ci=min(p-cLo,cHi-p);
  float curtain=smoothstep(0.,3.,min(ci.x,ci.z))*smoothstep(0.,2.,ci.y)*mix(.35,1.,exp(-(p.y-241.5)/7.));
  if(sheathSum+cloudSum+lowSum+curtain<.01)return 0.;
  // gaine : voiles etires qui filent vers le bas avec l'eau ; embruns : volutes plus rondes
  vec3 qs=p*vec3(.5,.18,.5)+vec3(0.,fluid_time*1.8,0.);        // grandes volutes etirees
  float ns=noise(qs)*.65+noise(qs*2.4+vec3(3.,fluid_time*1.1,7.))*.35;
  vec3 qc=p*vec3(.75,.38,.75)+vec3(0.,fluid_time*1.3,0.);
  float nc=noise(qc)*.6+noise(qc*2.3+vec3(7.,fluid_time*.9,3.))*.4;
  return (sheathSum*.70*smoothstep(.50,.88,ns)+cloudSum*1.9*smoothstep(.24,.80,nc)+lowSum*.12*smoothstep(.24,.8,nc)
          +curtain*.16*smoothstep(.38,.85,ns))*boxFade;
}
void main(){
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T26,0));
  vec3 rd=normalize(view_ray);
  vec3 eye=cam_trans.xyz/4096.;
  // boite englobante des quatre chutes
  vec3 lo=min(min(fountain_start[0],fountain_end[0]),min(fountain_start[1],fountain_end[1]));
  vec3 hi=max(max(fountain_start[0],fountain_end[0]),max(fountain_start[1],fountain_end[1]));
  lo=min(lo,min(min(fountain_start[2],fountain_end[2]),min(fountain_start[3],fountain_end[3])));
  hi=max(hi,max(max(fountain_start[2],fountain_end[2]),max(fountain_start[3],fountain_end[3])));
  lo-=vec3(10.,.6,10.);hi+=vec3(10.,1.,10.);
  gLo=lo;gHi=hi;
  vec3 inv=1./(abs(rd)+1e-6)*sign(rd+1e-9);
  vec3 ta=(lo-eye)*inv,tb=(hi-eye)*inv;
  float t0=max(max(min(ta.x,tb.x),min(ta.y,tb.y)),min(ta.z,tb.z));
  float t1=min(min(max(ta.x,tb.x),max(ta.y,tb.y)),max(ta.z,tb.z));
  t0=max(t0,.3);
  float depth=texture(tex_T26,uv).r;
  if(!skyDepth(depth))t1=min(t1,length(unproject(uv,depth)));
  if(t1<=t0)discard;
  const int N=26;
  float dt=(t1-t0)/float(N);
  float jitter=fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453);
  float T=1.;
  for(int i=0;i<N;i++){
    vec3 p=eye+rd*(t0+dt*(float(i)+jitter));
    float d=mist(p);
    T*=exp(-d*.80*dt);
    if(T<.02)break;
  }
  float alpha=1.-T;
  if(alpha<.004)discard;
  // on voit a travers : leger tremblement du decor dans la brume
  vec2 wobble=vec2(noise(vec3(gl_FragCoord.xy*.02,fluid_time*1.3))-.5,noise(vec3(gl_FragCoord.yx*.02,fluid_time*1.1+5.))-.5);
  vec2 px=vec2(1.)/vec2(textureSize(tex_T25,0));
  vec3 behind=texture(tex_T25,clamp(uv+wobble*px*7.*alpha,vec2(.001),vec2(.999))).rgb;
  // lumiere chaude des braseros, et lumiere qui traverse la brume par-derriere (verrieres) : la brume
  // n'assombrit pas un fond clair
  vec3 mistCol=mix(vec3(.80,.80,.76)*vec3(1.,.88,.72),behind*1.08+.03,.45);
  color=vec4(mix(behind,mistCol,alpha*.80),1.);
}
