// Meteo sur le decor (tfrag / tie) : sol mouille, flaques, ronds de pluie, neige au sol.
// Uniformes fournis par weather_bind_world (WeatherWorld.h), a chaque dessin.
uniform float weather_wet;          // 0..1 : sol mouille (monte vite sous la pluie, seche en minutes)
uniform float weather_puddles;      // 0..1 : etendue des flaques
uniform float weather_snow;         // 0..1 : neige tombee
uniform float weather_rain;         // 0..1 : pluie en cours (ronds dans les flaques)
uniform float weather_time;
uniform float weather_flash;        // eclair
uniform vec3 weather_sky;           // ciel reflechi a cette heure et par ce temps
uniform vec3 weather_sun_dir;
uniform vec3 weather_sun_color;
float wxHash(vec2 p){p=fract(p*vec2(.1031,.1030));p+=dot(p,p.yx+33.33);return fract((p.x+p.y)*p.x);}
vec2 wxHash2(vec2 p){vec3 q=fract(vec3(p.xyx)*vec3(.1031,.1030,.0973));q+=dot(q,q.yzx+33.33);return fract((q.xx+q.yz)*q.zy);}
float wxNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(wxHash(i),wxHash(i+vec2(1,0)),f.x),mix(wxHash(i+vec2(0,1)),wxHash(i+vec2(1,1)),f.x),f.y);}
// Ronds de pluie : un impact par cellule de ~0,4 m (deux grilles decalees), chacun a son rythme.
// Renvoie la pente de la surface (xy, perturbation de la normale) et l'eclat des cretes (z).
vec3 wxRipples(vec2 p,float t){
  vec2 slope=vec2(0.);float crest=0.;
  for(int layer=0;layer<2;layer++){
    vec2 q=p*2.6+float(layer)*vec2(.37,.61);
    vec2 c=floor(q),f=fract(q);
    for(int j=-1;j<=1;j++)for(int i=-1;i<=1;i++){
      vec2 o=vec2(i,j);vec2 h=wxHash2(c+o+float(layer)*17.);
      vec2 d=o+.15+.7*h-f;
      float ph=fract(t*(.9+.5*h.x)+h.y*7.);
      float len=length(d);
      float x=(len-ph*.9)*14.;
      float ring=sin(x*3.14159)*exp(-x*x)*(1.-ph)*(1.-ph);
      slope+=d/max(len,1e-3)*ring;
      crest+=max(ring,0.);
    }
  }
  return vec3(slope,crest);
}
vec3 weatherSurface(vec3 color,vec3 lit,vec3 P,vec3 N){
  if(weather_wet<.003&&weather_snow<.003)return color;
  vec3 E=cam_trans.xyz/4096.;
  vec3 V=normalize(E-P);float dist=length(E-P);
  if(dot(N,V)<0.)N=-N;
  float up=smoothstep(.45,.9,N.y);
  if(weather_wet>.003){
    // materiau poreux mouille : plus sombre
    float porous=weather_wet*(.45+.55*up);
    color*=mix(1.,.62,porous);
    // flaques dans les creux : bruit a grande echelle, seulement sur le plat
    float n=wxNoise(P.xz*.23)*.62+wxNoise(P.xz*.9+3.7)*.38;
    float th=mix(.82,.64,weather_puddles);
    float puddle=smoothstep(th,th+.06,n)*smoothstep(.93,.985,N.y)*smoothstep(.05,.3,weather_puddles);
    // ronds de pluie dans les flaques (plus faibles sur le sol simplement mouille)
    vec3 Nw=N;float crest=0.;
    float near=1.-smoothstep(12.,30.,dist);
    if(weather_rain>.02&&near>0.){
      vec3 rp=wxRipples(P.xz,weather_time)*weather_rain*near;
      Nw=normalize(N+vec3(rp.x,0.,rp.y)*mix(.12,.35,puddle));
      crest=rp.z*mix(.25*porous,1.,puddle);
    }
    float NdV=max(dot(Nw,V),0.);
    float fres=.02+.98*pow(1.-NdV,5.);
    vec3 R=reflect(-V,Nw);
    // ciel reflechi : plus sombre vers l'horizon (facades), plus clair au zenith : les rides se voient
    vec3 sky=weather_sky*(.45+1.05*clamp(R.y,0.,1.));
    float spec=pow(max(dot(R,normalize(weather_sun_dir)),0.),mix(60.,600.,puddle));
    // eau stagnante : fond assombri, reflet presque miroir aux angles rasants
    color=mix(color,color*.55,puddle);
    float refl=mix(fres*.55*porous,mix(.30,.95,fres),puddle);
    color=mix(color,sky,clamp(refl,0.,1.));
    color+=weather_sky*crest*.28;
    color+=weather_sun_color*spec*(porous*.25+puddle*1.4);
    color+=vec3(.7,.75,.9)*weather_flash*refl*.15;
  }
  if(weather_snow>.003){
    // Neige fraiche sur une ville portuaire : couche fine au debut (le bois se devine), congeres etirees
    // par le vent, plaques fondues (bois mouille sombre), joints et creux sombres qui gardent moins de
    // neige, relief granuleux qui accroche la lumiere, paillettes.
    float light=dot(lit,vec3(.3,.59,.11));
    float albedo=clamp(dot(color,vec3(.3,.59,.11))/max(light,.05),0.,1.5);   // clarte de la texture
    vec2 w=vec2(P.x*.93+P.z*.37,P.z*.93-P.x*.37);                          // axes du vent
    float drift=wxNoise(w*vec2(.16,.6))*.6+wxNoise(w*vec2(.45,1.6)+5.3)*.4;
    float depth=weather_snow*up*(.45+1.1*drift);                          // epaisseur relative
    float seams=smoothstep(.22,.7,albedo);                                 // joints / creux de la texture
    float cover=smoothstep(.12,.8,depth*mix(.35,1.,seams));
    // plaques de neige fondue : bois mouille, un peu brillant
    // (contours irreguliers : bruit deforme par un second bruit, bordure de neige mouillee grise)
    vec2 warp=vec2(wxNoise(P.xz*1.3),wxNoise(P.xz*1.3+7.))*1.6;
    float slushN=wxNoise(P.xz*.5+warp+11.)*.65+wxNoise(P.xz*2.4+warp*.5+2.)*.35;
    float thin=(1.-smoothstep(.9,1.3,depth))*up*weather_snow;
    float slush=smoothstep(.71,.81,slushN)*thin;
    float rim=smoothstep(.63,.73,slushN)*thin-slush;
    vec3 wetWood=color*.80;
    float fresS=.02+.98*pow(1.-max(dot(N,V),0.),5.);
    wetWood=mix(wetWood,weather_sky*(.45+1.05*clamp(reflect(-V,N).y,0.,1.)),fresS*.6);
    color=mix(color,wetWood,slush*.85);
    cover*=1.-slush;
    // relief granuleux (attenue au loin, pas de scintillement)
    float near=1.-smoothstep(6.,22.,dist);
    float g0=wxNoise(P.xz*6.5),gx=wxNoise((P.xz+vec2(.06,0.))*6.5),gz=wxNoise((P.xz+vec2(0.,.06))*6.5);
    vec3 bn=normalize(vec3((g0-gx)*.9*near,1.,(g0-gz)*.9*near));
    vec3 L=normalize(weather_sun_dir);
    float relief=1.+.55*(dot(bn,L)-L.y)*step(0.,L.y);
    float grain=1.+(wxNoise(P.xz*23.)-.5)*.10*near;
    // couleur : blanc legerement bleute a l'ombre, suit l'eclairage de la scene
    vec3 snowCol=mix(vec3(.80,.86,.97),vec3(.95,.96,.98),clamp(light*1.2,0.,1.));
    // albedo de la neige ~3 fois celui du bois : nettement plus claire que le decor, meme par temps gris
    snowCol*=clamp(light*1.35+.03,.03,1.05)*relief*grain;
    // couche mince : la texture transparait
    snowCol=mix(color*.9+snowCol*.35,snowCol,smoothstep(.25,.9,depth));
    vec2 gc=floor(P.xz*55.);
    float sparkle=step(.988,wxHash(gc+floor(dot(V,vec3(13.,7.,11.)))))*near;
    snowCol+=weather_sun_color*sparkle*.5;
    snowCol=mix(snowCol,snowCol*.72+wetWood*.2,clamp(rim,0.,1.));   // neige mouillee en bordure des plaques
    color=mix(color,snowCol,cover);
  }
  return color;
}
