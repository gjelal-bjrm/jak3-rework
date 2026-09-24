#version 410 core
// Precipitations en vraie 3D : chaque instance est une goutte (trainee), un flocon ou un grain de sable
// dans une boite qui suit la camera. Les positions sont fixes dans le monde (parallaxe correcte quand la
// camera bouge) et replongent dans la boite par modulo. Test de profondeur materiel contre la scene :
// les gouttes passent derriere les murs et les toits.
// Largeur tenue a >= 1,2 pixel, l'opacite compensant (pas de scintillement des gouttes lointaines).
uniform mat4 pc_camera;
uniform vec4 cam_trans;             // unites du jeu (4096 / m)
uniform float wx_time;
uniform int wx_kind;                // 0 pluie, 1 neige, 2 sable
uniform int wx_layer;               // 0 couche proche, 1 rideau lointain
uniform vec3 wx_box;                // m
uniform vec2 wx_wind;               // m/s
uniform vec2 wx_viewport;           // pixels
out vec2 local;                     // x : -1..1 en travers ; y : 0..1 le long (ou -1..1 pour un flocon)
out float fade;

float hash(uint n){n=(n<<13U)^n;n=n*(n*n*15731U+789221U)+1376312589U;return float(n&0x7fffffffU)/float(0x7fffffff);}
vec4 project(vec3 rel){vec4 h=-pc_camera*vec4(rel*4096.,1.);h.y*=(512./416.)*.5;return h;}
vec2 toPixels(vec4 h){return h.xy/h.w*wx_viewport*.5;}

void main(){
  uint id=uint(gl_InstanceID)+uint(wx_layer)*1000003U;
  vec3 r=vec3(hash(id*3U+11U),hash(id*3U+12U),hash(id*3U+13U));
  float s=hash(id+90001U),s2=hash(id+70001U);
  vec3 eye=cam_trans.xyz/4096.;
  vec3 vel;float len,width;
  if(wx_kind==0){        // pluie : 7 a 9,5 m/s, trainee = flou de mouvement
    vel=vec3(wx_wind.x*.9,-mix(7.,9.5,s),wx_wind.y*.9);
    len=mix(.45,.75,s2);width=mix(.0018,.003,s);
  }else if(wx_kind==1){  // neige : chute lente, derive
    vel=vec3(wx_wind.x*.8,-mix(.65,1.35,s),wx_wind.y*.8);
    len=0.;width=mix(.012,.028,s2*s2);
  }else{                 // sable : grains rapides a l'horizontale, legere turbulence
    vel=vec3(wx_wind.x,-.3+.8*(s-.5),wx_wind.y)*mix(.75,1.25,s);
    len=mix(.12,.35,s2);width=mix(.0012,.0025,s);
  }
  vec3 p=r*wx_box+vel*wx_time;
  if(wx_kind==1){float ph=s*6.2831;p.x+=.35*sin(wx_time*1.3+ph);p.z+=.35*cos(wx_time*1.05+ph*1.7);p.y+=.08*sin(wx_time*2.3+ph);}
  if(wx_kind==2){float ph=s2*6.2831;p.y+=.25*sin(wx_time*3.1+ph);}
  vec3 q=mod(p-eye,wx_box)-wx_box*.5;       // position dans la boite centree sur l'oeil
  // fondu aux bords de la boite et tout pres de l'oeil
  vec3 edge=abs(q)/(wx_box*.5);
  fade=1.-smoothstep(.72,1.,max(max(edge.x,edge.z),edge.y*.9));
  vec3 rel=q;
  if(wx_kind==0)rel.y+=wx_box.y*.2;         // pluie : plus de gouttes au-dessus de l'oeil
  float d=length(rel);
  fade*=smoothstep(.35,1.2,d);
  // la couche lointaine laisse le centre a la couche proche (pas de double densite pres de l'oeil)
  if(wx_layer==1)fade*=smoothstep(4.,7.,length(q.xz));
  vec3 dir=length(vel)>0.?normalize(vel):vec3(0.,-1.,0.);
  vec4 ha=project(rel);
  if(ha.w<.3||fade<=0.){gl_Position=vec4(2.,2.,2.,1.);local=vec2(0.);return;}
  // pixels par metre a cette distance
  vec4 hx=project(rel+vec3(.1,0.,0.)),hz=project(rel+vec3(0.,0.,.1)),hy=project(rel+vec3(0.,.1,0.));
  vec2 pa=toPixels(ha);
  float ppm=max(max(length(toPixels(hx)-pa),length(toPixels(hz)-pa)),length(toPixels(hy)-pa))*10.;
  float widthPx=width*ppm;
  float drawn=max(widthPx,wx_kind==1?1.6:1.2);
  fade*=min(1.,widthPx/drawn);
  vec2 corner=vec2[6](vec2(-1,0),vec2(1,0),vec2(1,1),vec2(-1,0),vec2(1,1),vec2(-1,1))[gl_VertexID];
  vec2 pos;float z;
  if(wx_kind==1){
    vec2 c=corner*vec2(1.,2.)-vec2(0.,1.);   // carre -1..1
    pos=pa+c*drawn*.5;local=c;z=ha.z/ha.w;
  }else{
    vec4 hb=project(rel-dir*len);
    if(hb.w<.3)hb=ha;
    vec2 pb=toPixels(hb);
    vec2 axis=pb-pa;float l=length(axis);
    axis=l>1e-3?axis/l:vec2(0.,1.);
    l=max(l,drawn*1.5);
    vec2 nrm=vec2(-axis.y,axis.x);
    pos=pa+axis*l*corner.y+nrm*corner.x*drawn*.5;
    local=corner;z=mix(ha.z/ha.w,hb.z/hb.w,corner.y);
  }
  gl_Position=vec4(pos/(wx_viewport*.5),z,1.);
}
