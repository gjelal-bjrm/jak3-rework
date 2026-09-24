#version 410 core
// Nuages volumiques du remaster (demi-resolution, accumulation temporelle).
//  - Couche de cumulus entre 1500 et 4200 m, sur une planete de 120 km de rayon (l'horizon reste a
//    distance finie). Densite : carte meteo 2D (ou sont les nuages, 2 echelles) x profil vertical
//    (base plate, sommet bombe, hauteur variable) x bruit 3D Perlin-Worley (masses) erode par un Worley
//    fin (bourgeonnements au sommet, bords effiloches a la base).
//  - Eclairage : transmittance vers le soleil (6 pas croissants), diffusion multiple approchee
//    (3 octaves), Henyey-Greenstein double lobe (lisere argente a contre-jour), effet "poudre" sur les
//    bords minces, ambiance du ciel natif (plus claire au sommet, plus sombre a la base).
//  - Perspective aerienne : les nuages lointains se fondent dans la brume d'horizon du niveau.
//  - Chaque image decale le point de depart des pas (bruit entrelace + nombre d'or) ; l'historique
//    reprojete par direction (les nuages sont a plusieurs km) moyenne ce decalage : ni bandes ni grain.
// Sortie : rgb = lumiere diffusee (premultipliee), a = transmittance.
in vec3 sky_ray;
out vec4 color;
uniform sampler2D tex_T25;          // ciel natif (instantane)
uniform sampler2D tex_T26;
uniform sampler3D cloud_noise;      // forme 3D
uniform sampler2D cloud_weather;    // carte meteo 2D
uniform sampler2D cloud_history;    // image precedente (meme tampon demi-resolution)
uniform vec4 fluid_viewport;
uniform mat4 sky_camera;
uniform mat4 cloud_prev_camera;
uniform vec3 cloud_eye;             // position de l'oeil (m)
uniform float sky_time;
uniform vec3 sky_sun;
uniform vec3 sky_moon;
uniform float cloud_frame;
uniform float cloud_history_valid;
// Parametres meteo
uniform float sky_coverage;         // 0..1 : part du ciel couverte
uniform float cloud_type;           // 0 = petits cumulus de beau temps, 1 = gros cumulus bourgeonnants
uniform float cloud_density;        // multiplicateur de densite
uniform float cloud_darkness;       // 0..1 : bases sombres (pluie, orage)
uniform vec2 cloud_wind;            // m/s (sens du vent)
uniform vec2 cloud_offset;          // deplacement cumule par le vent (m) : pas de saut quand le vent change

const float PLANET=120000.;
const float CLOUD_BASE=1500.,CLOUD_TOP=4200.;
const float SIGMA=.045;             // extinction par metre pour une densite 1

bool skyDepth(float depth){
  const float step24=1./16777215.;
  return depth<=1.5*step24 || abs(depth-400.*step24)<=1.5*step24;
}
vec2 project(vec3 ray){
  vec4 h=-sky_camera*vec4(ray*4096.,1.);
  h.y*=(512./416.)*.5;
  vec2 n=h.xy/h.w;
  return (fluid_viewport.xy+(n*.5+.5)*fluid_viewport.zw)/vec2(textureSize(tex_T25,0));
}
vec3 nativeSky(vec3 dir,vec3 fallback){
  vec2 uv=project(normalize(dir));
  if(any(lessThan(uv,vec2(.002)))||any(greaterThan(uv,vec2(.998))))return fallback;
  return skyDepth(texture(tex_T26,uv).r)?texture(tex_T25,uv).rgb:fallback;
}
float remap(float v,float l0,float h0,float l1,float h1){return l1+(v-l0)*(h1-l1)/max(h0-l0,1e-4);}
// Sortie de la sphere de rayon r depuis o (o a l'interieur).
float sphereExit(vec3 o,vec3 d,float r){
  float b=dot(o,d),c=dot(o,o)-r*r;
  return -b+sqrt(max(b*b-c,0.));
}
float henyeyGreenstein(float mu,float g){
  float g2=g*g;
  return (1.-g2)/(4.*3.14159*pow(max(1.+g2-2.*g*mu,1e-4),1.5));
}
// Carte meteo : couverture locale (0..1) et hauteur relative du sommet.
// foot = empreinte d'un pixel a cette distance (m) : niveau de detail explicite (les lectures dans la
// boucle n'ont pas de derivees fiables ; sans cela, le detail se replie en motifs en escalier).
float lodFor(float foot,float texelMetres){return max(log2(max(foot/texelMetres,1.)),0.);}
vec2 weather(vec2 xz,float foot){
  vec2 w=xz+cloud_offset;
  float big=textureLod(cloud_weather,w/16000.,lodFor(foot,16000./256.)).r;
  float mid=textureLod(cloud_weather,w/5200.+vec2(.37,.71),lodFor(foot,5200./256.)).r;
  float field=big*.55+mid*.45;
  float cov=clamp(remap(field,1.-sky_coverage*1.15,1.,0.,1.),0.,1.);
  float tall=clamp(textureLod(cloud_weather,w/9000.+vec2(.61,.13),lodFor(foot,9000./256.)).r*1.4-.2,0.,1.);
  return vec2(cov,tall);
}
// Densite au point monde p (m) d'altitude h. `cheap` : sans erosion fine (pas de lumiere).
float cloudDensity(vec3 p,float h,bool cheap,float foot){
  float hf=(h-CLOUD_BASE)/(CLOUD_TOP-CLOUD_BASE);
  if(hf<0.||hf>1.)return 0.;
  vec2 wx=weather(p.xz,foot);
  if(wx.x<=.002)return 0.;
  // profil vertical : base nette, sommet arrondi ; hauteur selon le type de nuage et la carte
  float top=mix(.22,.55,cloud_type)+mix(.0,.45,cloud_type)*wx.y;
  top*=.6+.4*wx.x;
  float profile=smoothstep(0.,.06,hf)*(1.-smoothstep(top*.45,top,hf));
  if(profile<=0.)return 0.;
  vec3 q=vec3(p.x,h,p.z)+vec3(cloud_offset.x,0.,cloud_offset.y);
  vec4 low=textureLod(cloud_noise,q/2600.,lodFor(foot,2600./64.));
  float lowFbm=low.g*.625+low.b*.25+low.a*.125;
  float base=remap(low.r,-(1.-lowFbm),1.,0.,1.);
  base*=profile;
  base=remap(base,1.-wx.x,1.,0.,1.)*wx.x;
  if(base<=0.)return 0.;
  if(!cheap){
    vec3 hi=textureLod(cloud_noise,q/650.+vec3(sky_time*.004,0.,0.),lodFor(foot,650./64.)).gba;
    float hiFbm=hi.r*.625+hi.g*.25+hi.b*.125;
    float hiMod=mix(hiFbm,1.-hiFbm,clamp(hf*6.,0.,1.));   // effiloche a la base, bourgeonne au sommet
    base=remap(base,hiMod*.32,1.,0.,1.);
  }
  return clamp(base,0.,1.)*cloud_density;
}
void main(){
  vec3 ray=normalize(sky_ray);
  float pixelAngle=max(length(dFdx(ray)),length(dFdy(ray)));   // avant toute branche
  // Sous l'horizon (le sol cache le ciel) : rien a calculer.
  if(ray.y<-.03){color=vec4(0.,0.,0.,1.);return;}
  vec3 sun=normalize(sky_sun),moon=normalize(sky_moon);
  float sunUp=clamp(sun.y*2.5,0.,1.);
  float dayness=smoothstep(-.08,.06,sun.y);
  vec3 sunColor=mix(vec3(1.,.55,.30),vec3(1.,.96,.90),sunUp);
  vec3 L=dayness>.02?sun:moon;
  vec3 lightColor=mix(vec3(.30,.36,.52)*.26,sunColor,dayness);
  // Couleurs d'ambiance tirees du ciel natif du niveau ; si la direction est cachee (batiment, hors
  // ecran), ciel de secours qui suit l'heure (sinon les nuages restent blancs la nuit)
  vec3 fallback=mix(vec3(.045,.055,.095),vec3(.55,.62,.75),dayness);
  fallback=mix(fallback,vec3(.62,.45,.40),(1.-sunUp)*dayness*.6);
  // Couleur du ciel natif juste derriere le nuage (le pixel lui-meme) : continue en azimut. Echantillonner
  // l'horizon dans la meme direction faisait des bandes verticales la ou un rocher ou une ile le cachait.
  vec3 own=nativeSky(ray,fallback);
  vec3 haze=own;
  vec3 zenith=own*vec3(.95,1.,1.08);
  // Traversee de la couche
  vec3 o=vec3(0.,PLANET+cloud_eye.y,0.);
  float t0=sphereExit(o,ray,PLANET+CLOUD_BASE),t1=sphereExit(o,ray,PLANET+CLOUD_TOP);
  t1=min(t1,t0+8000.);
  float T=1.;vec3 S=vec3(0.);float tWeighted=0.,wSum=0.;
  if(t0<60000.){
    const int N=64;
    float dt=(t1-t0)/float(N);
    // decalage de depart : bruit entrelace + nombre d'or par image (moyenne par l'historique)
    // bruit entrelace dont la position glisse a chaque image (motif different, pas seulement decale) :
    // la moyenne temporelle ne laisse pas de stries residuelles
    // depart aleatoire par pixel (sans orientation) + suite du nombre d'or dans le temps : chaque pixel
    // parcourt uniformement tous les decalages, sans motif spatial residuel
    vec3 hq=fract(vec3(gl_FragCoord.xyx)*.1031);hq+=dot(hq,hq.yzx+33.33);
    float jitter=fract(fract((hq.x+hq.y)*hq.z)+cloud_frame*.61803398);
    float mu=dot(ray,L);
    float sigma=SIGMA*mix(1.,1.5,cloud_darkness);
    for(int i=0;i<N;i++){
      float t=t0+dt*(float(i)+jitter);
      vec3 op=o+ray*t;
      float h=length(op)-PLANET;
      vec3 wp=cloud_eye+ray*t;
      // filtrage : empreinte du pixel ou fraction du pas (sinon le detail fin, echantillonne tous les
      // 125 m, fait des stries)
      float foot=max(t*pixelAngle,dt*.35);
      float dens=cloudDensity(wp,h,false,foot);
      if(dens<=.003)continue;
      float hf=clamp((h-CLOUD_BASE)/(CLOUD_TOP-CLOUD_BASE),0.,1.);
      // transmittance vers la lumiere : 6 pas croissants (60 m ... 1,9 km)
      float tauL=0.,stepL=60.;vec3 lp=wp;float lh=h;
      for(int j=0;j<6;j++){
        lp+=L*stepL;lh+=L.y*stepL;
        tauL+=cloudDensity(lp,lh,true,max(foot,stepL*.5))*stepL;
        stepL*=2.;
      }
      // diffusion multiple approchee (Wrenninge) : 3 octaves
      float lum=0.,a=1.,b=1.,c=1.;
      for(int k=0;k<3;k++){
        lum+=a*(henyeyGreenstein(mu,.55*c)*.7+henyeyGreenstein(mu,-.2*c)*.3)*exp(-tauL*sigma*b);
        a*=.5;b*=.35;c*=.5;
      }
      float powder=1.-exp(-dens*dt*sigma*1.6);
      vec3 direct=lightColor*lum*11.*mix(.55,1.,powder);
      vec3 ambient=mix(haze*.55,zenith*1.15,smoothstep(0.,.7,hf))*mix(1.,.45,cloud_darkness);
      vec3 radiance=direct+ambient;
      float stepT=exp(-dens*sigma*dt);
      float absorbed=T*(1.-stepT);
      S+=radiance*absorbed;
      tWeighted+=t*absorbed;wSum+=absorbed;
      T*=stepT;
      if(T<.01)break;
    }
  }
  // Perspective aerienne : fondu dans la brume d'horizon selon la distance moyenne
  float alpha=1.-T;
  if(wSum>1e-4){
    float dist=tWeighted/wSum;
    float fog=1.-exp(-dist/22000.);
    vec3 col=S/max(alpha,1e-4);
    col=mix(col,haze,fog);
    alpha*=1.-fog*.55;
    S=col*alpha;
  }
  vec4 current=vec4(S,1.-alpha);
  // Accumulation temporelle : historique reprojete par direction (w = 0 : direction a l'infini)
  vec4 h=-cloud_prev_camera*vec4(ray,0.);
  h.y*=(512./416.)*.5;
  vec2 prev=h.xy/max(h.w,1e-6)*.5+.5;
  bool inside=h.w>0. && all(greaterThanEqual(prev,vec2(0.))) && all(lessThanEqual(prev,vec2(1.)));
  if(cloud_history_valid>.5 && inside){
    vec4 hist=texture(cloud_history,prev);
    current=mix(hist,current,.07);
  }
  color=current;
}
