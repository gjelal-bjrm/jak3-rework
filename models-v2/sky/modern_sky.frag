#version 410 core
// Ciel moderne de Jak 3 (remaster), v3.
//  1. Degrade d'ambiance natif du niveau conserve (identite de chaque zone, cycle jour-nuit natif).
//  2. Nuages : couche 2D eclairee a 1450 m, nuages individuels de tailles et formes variees (cumulus
//     moyens et petits) qui derivent lentement ; epaisseur analytique selon l'inclinaison du regard,
//     relief par gradient de densite, ombre propre vers le soleil, poudre et lisere argente ; filtrage
//     par l'empreinte du pixel (pas d'aliasing a l'horizon). Cirrus etires en haute altitude.
//  3. Soleil : disque, couronne, lueur ; ciel eclairci et rechauffe autour ; masque par les nuages.
//  4. Etoile du jour fidele a l'original (coeur clair, halo violet, aigrettes), masquee par les nuages
//     qui passent devant.
in vec3 sky_ray;
out vec4 color;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
uniform vec4 fluid_viewport;
uniform mat4 sky_camera;
uniform float sky_time;
uniform float sky_hour;
uniform vec3 sky_sun;
uniform vec3 sky_green_sun;
uniform vec3 sky_moon;
uniform vec3 sky_day_star;
uniform float sky_day_star_on;
uniform float sky_coverage;
uniform float sky_dark_jak;      // 0..1 : reaction de l'etoile a Dark Jak (lissee par le moteur)
uniform float sky_progress;      // 0..1 : avancement de l'histoire (le vaisseau approche)
uniform float sky_turbulence;    // scintillement atmospherique (1 = desert, .35 = port)

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
float hash(vec2 p){vec3 q=fract(vec3(p.xyx)*.1031);q+=dot(q,q.yzx+33.33);return fract((q.x+q.y)*q.z);}
float noise(vec2 p){
  vec2 i=floor(p),f=fract(p);f=f*f*f*(f*(f*6.-15.)+10.);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);
}
float fbm(vec2 p){
  float v=0.,a=.5;mat2 r=mat2(.8,.6,-.6,.8);
  for(int i=0;i<4;i++){v+=a*noise(p);p=r*p*2.07+vec2(7.1,3.7);a*=.5;}
  return v;
}
// Echantillon natif du ciel dans une direction (couleur d'ambiance), ou repli sur la couleur du pixel.
vec3 nativeSky(vec3 dir,vec3 fallback){
  vec2 uv=project(normalize(dir));
  if(any(lessThan(uv,vec2(.002)))||any(greaterThan(uv,vec2(.998))))return fallback;
  return skyDepth(texture(tex_T26,uv).r)?texture(tex_T25,uv).rgb:fallback;
}
// ---- Nuages ----
// Nuages individuels de tailles et formes variees (cumulus moyens 600-900 m, petits 250-400 m) qui
// derivent a ~4 m/s, sur une couche a 1450 m. Rendu en couche 2D eclairee (pas de traversee par pas :
// une traversee echantillonnee bandait des que les nuages devenaient petits et nets). L'epaisseur est
// analytique : plus le regard rase, plus il traverse de nuage.
const float CLOUD_HEIGHT=1450.;
// fbm dont les octaves trop fines pour l'espacement d'echantillonnage sont eteintes (anti-aliasing).
// w = espacement / longueur d'onde de l'octave : une octave est eteinte avant Nyquist (w = .5).
float fbmLod(vec2 p,float cell){
  float v=0.,a=.5,w=cell;mat2 r=mat2(.8,.6,-.6,.8);
  for(int i=0;i<4;i++){
    v+=a*noise(p)*(1.-smoothstep(.22,.55,w));
    p=r*p*2.07+vec2(7.1,3.7);a*=.5;w*=2.07;
  }
  return v;
}
float puffField(vec2 xz,float scale,float seedOffset,float cell){
  vec2 p=xz*scale+seedOffset;
  float c=cell*scale;
  vec2 warp=vec2(fbmLod(p*1.3+3.1,c*1.3),fbmLod(p*1.3-2.7,c*1.3))-.5;
  p+=warp*.55;                                  // contours irreguliers
  return fbmLod(p,c)+(fbmLod(p*3.3+vec2(1.7,9.2),c*3.3)-.5)*.30;
}
// Densite de la couche (0..1) au point plan xz (m). cell = empreinte de filtrage (m).
float cloudLayer(vec2 xz,float coverage,float cell){
  vec2 wind=vec2(sky_time*3.8,sky_time*1.4);   // m
  float medium=puffField(xz+wind,1./780.,0.,cell);
  float small=puffField(xz+wind*1.25,1./330.,17.3,cell);
  // Seuils calibres sur la distribution du champ (mediane .49, p90 .66) : couverture .58 -> ~35 % de
  // cumulus moyens et ~18 % de petits ; couverture .44 -> ~22 % et ~10 %.
  float thM=.75-coverage*.35,thS=.82-coverage*.35;
  float m=smoothstep(thM,thM+.16,medium);
  float sm=smoothstep(thS,thS+.13,small)*.85;
  return max(m,sm);
}
float henyeyGreenstein(float mu,float g){
  float g2=g*g;
  return (1.-g2)/(4.*3.14159*pow(1.+g2-2.*g*mu,1.5));
}
void main(){
  vec2 screen=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec3 native=texture(tex_T25,screen).rgb;
  if(!skyDepth(texture(tex_T26,screen).r)){color=vec4(native,1.);return;}
  vec3 ray=normalize(sky_ray);
  vec3 sun=normalize(sky_sun),moon=normalize(sky_moon);
  float sunUp=clamp(sun.y*2.5,0.,1.);
  float dayness=smoothstep(-.08,.06,sun.y);             // 0 nuit, 1 jour
  vec3 sunColor=mix(vec3(1.,.55,.28),vec3(1.,.96,.88),sunUp);
  // Lumiere principale des nuages : soleil le jour, lune la nuit.
  vec3 L=dayness>.02?sun:moon;
  vec3 lightColor=mix(vec3(.30,.36,.52)*.55,sunColor,dayness);
  vec3 horizonRay=normalize(vec3(ray.x,max(.03,ray.y*.15),ray.z));
  vec3 haze=nativeSky(horizonRay,native);
  vec3 zenith=nativeSky(vec3(ray.x*.25,1.,ray.z*.25),native);
  vec3 result=native;
  // ---- Diffusion vers le soleil dans le ciel clair
  float toSun=max(dot(ray,sun),0.);
  result+=sunColor*haze*pow(toSun,4.)*.20*(1.+1.6*(1.-sunUp))*(1.-.6*clamp(ray.y*3.,0.,1.))*dayness;
  // Lune : lueur douce autour du disque natif, la nuit seulement.
  float toMoon=max(dot(ray,moon),0.);
  result+=vec3(.62,.68,.85)*(pow(toMoon,70.)*.22+pow(toMoon,9.)*.035)*(1.-dayness)*step(0.,moon.y+.02);
  // ---- Nuages (couche 2D eclairee)
  float cloudAlpha=0.;vec3 cloudColor=vec3(0);
  float pixelAngle=max(length(dFdx(ray)),length(dFdy(ray)));   // hors de toute branche (derivees)
  if(ray.y>.008){
    float t=CLOUD_HEIGHT/max(ray.y,.008);
    vec2 xz=ray.xz*t;
    float far=exp(-t*.000045);                             // fondu dans la brume au loin
    if(far>.01){
      // empreinte d'un pixel sur la couche (tres allongee pres de l'horizon) : filtre anti-aliasing
      float cell=pixelAngle*CLOUD_HEIGHT/max(ray.y*ray.y,1e-4);
      float d=cloudLayer(xz,sky_coverage,cell);
      if(d>.001){
        // epaisseur optique : un cumulus de ~450 m, traverse obliquement (1/ray.y), plafonne
        float slant=1./max(ray.y,.12);
        float tau=d*2.6*slant;
        cloudAlpha=(1.-exp(-tau))*far*smoothstep(.008,.05,ray.y);
        // relief : gradient de la densite -> normale de la face inferieure/bord (bosses)
        float e=max(cell,25.)*1.5;
        float dx=cloudLayer(xz+vec2(e,0.),sky_coverage,cell)-cloudLayer(xz-vec2(e,0.),sky_coverage,cell);
        float dz=cloudLayer(xz+vec2(0.,e),sky_coverage,cell)-cloudLayer(xz-vec2(0.,e),sky_coverage,cell);
        vec3 n=normalize(vec3(-dx*380./e,1.,-dz*380./e));
        // ombre portee par le nuage sur lui-meme : densite vers le soleil
        vec2 toward=L.xz/max(L.y,.15)*380.;
        float dSun=cloudLayer(xz+toward,sky_coverage,cell);
        float shadow=exp(-dSun*2.2);
        float powder=1.-exp(-d*3.5);                       // bords fins lumineux, coeur mat
        float mu=dot(ray,L);
        float phase=henyeyGreenstein(mu,.40)*.7+henyeyGreenstein(mu,-.15)*.3+.05;
        float ndl=clamp(dot(n,L)*.5+.5,0.,1.);
        // le dessous est dans l'ombre du nuage lui-meme : les bords et le cote du soleil s'eclairent
        vec3 ambient=mix(haze*.72,zenith*1.20,.5)*(.62+.38*(1.-d*.7));
        vec3 direct=lightColor*shadow*phase*8.5*(.30+.70*powder)*ndl;
        cloudColor=ambient+direct;
        // lisere argente : diffusion avant a travers les bords minces
        float rim=pow(toSun,20.)*cloudAlpha*(1.-cloudAlpha)*3.0*dayness;
        cloudColor+=sunColor*rim;
        cloudColor=mix(cloudColor,haze,1.-far);
      }
    }
    result=mix(result,cloudColor,cloudAlpha);
    // ---- Cirrus (haute couche etiree, tres fine)
    if(ray.y>.04){
      float y=max(ray.y,.04);
      vec2 q=ray.xz/y*8000.+vec2(sky_time*22.,sky_time*4.);
      mat2 stretch=mat2(.96,.28,-.28,.96);
      q=stretch*q;q.y*=3.4;
      float pixelAngleC=max(length(dFdx(ray)),length(dFdy(ray)));
      float footC=pixelAngleC*8000./max(y*y,1e-4)*3.4;
      float c=fbmLod(q*.00015,footC*.00015)*.6+fbmLod(q*.00068+vec2(3.3,1.1),footC*.00068)*.4;
      float cirrus=smoothstep(.56,.80,c)*smoothstep(.04,.2,ray.y)*exp(-length(ray.xz/y)*.10);
      vec3 cirrusColor=mix(mix(zenith*1.3,vec3(.94,.95,.98),.5),sunColor,.35*pow(toSun,3.))*mix(.35,1.,dayness);
      result=mix(result,cirrusColor,cirrus*.40*(1.-cloudAlpha*.7));
    }
  }
  // ---- Soleil (au-dessus des nuages minces : les nuages epais l'attenuent)
  {
    float c=dot(ray,sun);
    float disc=smoothstep(.99990,.99997,c);
    float corona=pow(max(c,0.),600.)*.7+pow(max(c,0.),2500.)*.6;
    float glow=pow(max(c,0.),40.)*.35+pow(max(c,0.),7.)*.06;
    float occlusion=1.-cloudAlpha;
    result+=sunColor*((disc*1.5+corona)*occlusion*step(0.,sun.y+.05)+glow*(.6+.4*sunUp)*(1.-cloudAlpha*.5))*max(dayness,.15);
  }
  // ---- Etoile du jour : fidele a l'original (coeur clair, halo violet, quatre aigrettes), avec :
  //  - progression : le vaisseau approche au fil de l'histoire (taille +40 %, pulsation plus rapide) ;
  //  - Dark Jak : l'etoile repond a l'eco noir (plus intense, halo violet profond) puis se calme ;
  //  - scintillement atmospherique : eclat et position tremblent legerement (air chaud du desert).
  if(sky_day_star_on>.5){
    vec3 ds=normalize(sky_day_star);
    vec3 right=normalize(cross(ds,vec3(0.,1.,0.)));vec3 up=cross(right,ds);
    float tw1=noise(vec2(sky_time*5.7,2.3))-.5,tw2=noise(vec2(sky_time*6.9,7.1))-.5;
    ds=normalize(ds+(right*tw1+up*tw2)*.0011*sky_turbulence);          // tremblement angulaire (~0,06 deg)
    float twinkle=1.+.22*sky_turbulence*(noise(vec2(sky_time*8.3,11.7))-.5)*2.;
    float c=dot(ray,ds);
    if(c>.993){
      float angle=acos(clamp(c,-1.,1.));
      vec2 local=vec2(dot(ray,right),dot(ray,up));
      float grow=1.+.40*sky_progress;
      float pulse=.94+.06*sin(sky_time*(1.1+.9*sky_progress));
      vec3 core=vec3(1.,.97,1.);
      vec3 violet=mix(vec3(.66,.42,1.),vec3(.52,.16,1.),sky_dark_jak);
      float disc=smoothstep(.0062*grow,.0030*grow,angle);
      float halo=exp(-angle*angle/(2.*pow(.0085*grow,2.)))*.85+exp(-angle*angle/(2.*pow(.020*grow,2.)))*.30;
      float spikes=(exp(-abs(local.x)*700./grow)*exp(-abs(local.y)*28./grow)+exp(-abs(local.y)*700./grow)*exp(-abs(local.x)*28./grow))*smoothstep(.07*grow,.0,angle);
      float intensity=twinkle*(1.+.9*sky_dark_jak);
      vec3 star=(core*disc*2.0*pulse+violet*halo*pulse+mix(violet,core,.4)*spikes*.7)*intensity;
      // Dark Jak : lueur violette diffuse supplementaire autour de l'etoile
      star+=violet*exp(-angle*angle/(2.*.035*.035))*.35*sky_dark_jak;
      float behindClouds=1.-cloudAlpha;   // les nuages passent devant l'etoile
      result+=star*behindClouds;
    }
  }
  color=vec4(result,1.);
}
