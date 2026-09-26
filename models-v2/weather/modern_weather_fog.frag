#version 410 core
// Atmosphere meteo (apres le decor, les particules et la mer ; avant l'interface) :
//  - voile de pluie / neige : densite uniforme, les lointains se fondent dans le gris du ciel couvert ;
//  - brouillard matinal : brouillard de hauteur exponentiel (epais au ras de l'eau, ciel visible au-dessus),
//    integre analytiquement le long du rayon ;
//  - tempete de sable : nuee ocre animee par rafales qui defilent dans le sens du vent, plus dense au sol ;
//  - desert : poussiere chaude qui derive avec le vent, air chaud qui fait onduler les lointains et l'horizon.
// Le soleil eclaire le brouillard vers l'avant (halo). Sortie premultipliee (ONE, ONE_MINUS_SRC_ALPHA).
in vec3 view_ray;
out vec4 color;
uniform sampler2D tex_T25;          // image de la scene (copie) : brume de chaleur
uniform sampler2D tex_T26;          // profondeur de la scene (copie)
uniform vec4 fluid_viewport;
uniform mat4 pc_camera;
uniform vec3 wx_eye;                // m
uniform float wx_time;
uniform vec3 wx_sun;                // direction du soleil (ou de la lune)
uniform vec3 wx_sun_color;          // lumiere directe restante
uniform vec3 wx_fog_color;          // couleur du voile (ciel couvert a cette heure)
uniform vec3 wx_sand_color;
uniform float wx_fog;               // 0..1 : voile de la meteo (1 = brouillard matinal)
uniform float wx_rain;              // 0..1
uniform float wx_snow;              // 0..1
uniform float wx_ground_level;      // m
uniform float wx_ground_height;     // decroissance du brouillard (m)
uniform float wx_sand;              // 0..1
uniform vec2 wx_wind;               // m/s
uniform float wx_flash;             // eclair
uniform float wx_arena;             // 0..1 : brume de l'arene (fumee et chaleur de la lave)
uniform float wx_arena_level;       // m : niveau de la lave
uniform float wx_desert;            // 0..1 : brume chaude du desert (perspective aerienne facon Genshin)
uniform float wx_heat;              // 0..1 : air chaud du desert en plein jour (ondulation des lointains, mirage)
uniform float wx_dsky;             // 0..1 : ciel du desert (pas la ville : ses nuages restent intacts)
uniform float wx_day;              // 0..1 : soleil assez haut (pas d'effet a l'aube, au couchant ni la nuit)

bool skyDepth(float d){const float s=1./16777215.;return d<=1.5*s||abs(d-400.*s)<=1.5*s;}
mat4 invCam;
vec3 unproject(vec2 uv,float depth){
  vec2 pixel=uv*vec2(textureSize(tex_T26,0));
  vec4 h=vec4((pixel-fluid_viewport.xy)/fluid_viewport.zw*2.-1.,depth*2.-1.,1.);
  h.y/=(512./416.)*.5;
  vec4 w=invCam*h;
  return w.xyz/w.w/4096.;
}
float hash(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 x){
  vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);
  return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
void main(){
  invCam=inverse(-pc_camera);
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T26,0));
  float depth=texture(tex_T26,uv).r;
  vec3 rd=normalize(view_ray);
  bool sky=skyDepth(depth);
  float dist=3000.;
  if(!sky) dist=min(length(unproject(uv,depth)),3000.);
  // Air chaud du desert (plein jour) : au ras du sable, l'air chaud fait onduler les lointains et le bord de
  // l'horizon (mirage). On decale l'image : cellules d'air qui montent, en coordonnees angulaires (stables quand
  // la camera tourne). Rien pres de la camera ; un objet proche n'est jamais tire dans le lointain.
  bool heat=false; vec3 heatBase=vec3(0.);
  if(wx_heat>0.){
    float graze=sky?1.-smoothstep(0.,.03,rd.y):1.-smoothstep(.01,.10,abs(rd.y));   // rayons rasants seulement
    float w=wx_heat*graze*smoothstep(60.,350.,dist);
    if(w>.002){
      float t=wx_time;
      vec3 a=rd*vec3(240.,520.,240.)+vec3(0.,-t*3.,t*.35);
      vec3 b=rd*vec3(620.,1150.,620.)+vec3(7.,-t*5.,3.+t*.5);
      vec2 d=vec2(noise(a)-.5+.5*(noise(b)-.5),noise(a+vec3(19.,0.,11.))-.5+.5*(noise(b+vec3(11.,5.,0.))-.5));
      vec2 px=d*w*vec2(1.8,3.6)*(fluid_viewport.w/1080.);
      vec2 cand=uv+px/vec2(textureSize(tex_T25,0));
      float dc=texture(tex_T26,cand).r;
      float distC=skyDepth(dc)?3000.:min(length(unproject(cand,dc)),3000.);
      if(distC>dist*.75||distC>500.){heat=true;heatBase=texture(tex_T25,cand).rgb;}
    }
  }
  // Ciel du desert (plein jour) : bleu plus franc en haut, blanc-bleute lumineux a l'horizon (air sec, pas de
  // voile gris) ; les nuages (peu satures) et le soleil restent tels quels ; lueur chaude du cote du soleil
  float dayF=wx_day*clamp(length(wx_sun_color)/1.2,0.,1.);
  bool desertSky=wx_dsky>0.&&sky&&dayF>0.;
  vec3 scene=heatBase;
  if(desertSky){
    if(!heat) scene=texture(tex_T25,uv).rgb;
    float e=max(rd.y,0.);
    vec3 skyT=mix(vec3(.78,.87,.96),vec3(.25,.47,.90),smoothstep(0.,.45,e));
    // couleur du ciel vise, a la meme luminosite relative : la fumee du volcan et ses bords restent un degrade
    // noir -> azur (pas d'anneau gris) ; pres de l'horizon, la bande gris-brun (nuages lointains, degrade
    // d'origine) devient blanc-bleute ; les nuages blancs et le soleil (plus clairs que le ciel vise) restent
    float lumT=dot(skyT,vec3(.2126,.7152,.0722)),lumS=dot(scene,vec3(.2126,.7152,.0722));
    float ref=mix(.55,.88,smoothstep(.05,.35,e));
    float k=clamp(lumS/(lumT*ref),0.,1.);
    vec3 target=mix(vec3(lumS),skyT*k,smoothstep(.55,.98,k));   // voile de fumee : gris, pas un halo bleu sature
    float cloud=smoothstep(.06,.22,lumS-lumT);
    float hue=max(smoothstep(-.02,.06,scene.b-scene.r),1.-smoothstep(.15,.30,e));   // en hauteur : pixels bleutes
    scene=mix(scene,target,.85*(1.-cloud)*hue*wx_dsky*dayF);
    float mu0=max(dot(rd,normalize(wx_sun)),0.);
    float hz=1.-smoothstep(0.,.25,e);
    scene+=wx_dsky*dayF*hz*hz*.30*pow(mu0,4.)*vec3(1.,.90,.72);
  }
  bool replace=heat||desertSky;
  // voile uniforme (1/m) : pluie ~ 2 km de visibilite, neige ~ 1 km
  float haze=.00030*wx_fog+.0011*wx_rain+.0022*wx_snow;
  float tauFog=haze*dist;
  // brouillard de hauteur (brouillard matinal) : integrale de d0*exp(-(h-h0)/H) le long du rayon
  float groundFog=.022*clamp((wx_fog-.4)/.6,0.,1.);
  if(groundFog>0.){
    float k=1./wx_ground_height;
    float base=groundFog*exp(-(wx_eye.y-wx_ground_level)*k);
    float a=rd.y*k;
    tauFog+=abs(a)<1e-5?base*dist:base*(1.-exp(-dist*a))/a;
  }
  // sable : densite de base x rafales (bruit 3D qui defile avec le vent), concentree pres du sol
  float tauSand=0.;
  if(wx_sand>0.){
    float tMid=min(dist,28.);
    vec3 p=wx_eye+rd*tMid; p.xz-=wx_wind*wx_time; p.y-=wx_time*.6;
    float gust=noise(p*vec3(.045,.08,.045))*.65+noise(p*vec3(.13,.2,.13)+17.)*.35;
    gust=.45+1.1*gust;
    float low=exp(-max(rd.y,0.)*2.2);           // le ciel au-dessus reste un peu plus clair
    tauSand=wx_sand*wx_sand*.020*min(dist,400.)*gust*mix(.55,1.,low);
  }
  // Arene de Spargus : fumee de la lave toujours presente. Voile leger dans tout le cirque, nappe plus dense
  // au ras de la lave (integrale d'une densite qui decroit avec la hauteur), qui derive et ondule lentement.
  float tauArena=0.;
  if(wx_arena>0.){
    vec3 pm=wx_eye+rd*min(dist,40.); pm.xz-=vec2(.7,.4)*wx_time; pm.y-=wx_time*.35;
    float drift=.55+.9*(noise(pm*vec3(.05,.09,.05))*.7+noise(pm*vec3(.16,.22,.16)+9.)*.3);
    float k=1./9.;
    float base=.009*exp(-(wx_eye.y-wx_arena_level)*k);
    float a=rd.y*k;
    float layer=abs(a)<1e-5?base*dist:base*(1.-exp(-dist*a))/a;
    tauArena=wx_arena*(.0022*min(dist,600.)+min(layer,1.5))*drift;
  }
  // Desert : brume chaude et lumineuse, plus dense au ras du sable (densite qui decroit avec la hauteur), qui
  // fond les lointains dans une lumiere doree : profondeur des dunes et des rochers au loin. Le ciel reste net.
  float tauDesert=0.;
  if(wx_desert>0.){
    float k=1./140.;
    float base=.00050*exp(-(wx_eye.y-22.)*k);
    float a=rd.y*k;
    float layer=abs(a)<1e-6?base*dist:base*(1.-exp(-dist*a))/a;
    float skyCut=sky?0.:1.;   // le ciel a sa propre couleur (plus haut), pas un voile qui le griserait
    // voiles de poussiere qui derivent avec le vent (l'air bouge) : densite +-30 %
    vec3 pd=wx_eye+rd*min(dist,90.); pd.xz-=vec2(3.2,1.9)*wx_time;
    float drift=noise(pd*vec3(.018,.05,.018))*.7+noise(pd*vec3(.05,.1,.05)+5.)*.3;
    tauDesert=wx_desert*min(layer,1.4)*skyCut*(.72+.56*drift);
  }
  float tau=tauFog+tauSand+tauArena+tauDesert;
  if(tau<1e-4){color=replace?vec4(scene,1.):vec4(0.);return;}
  float f=1.-exp(-tau);
  vec3 L=normalize(wx_sun);
  float mu=max(dot(rd,L),0.);
  vec3 fogCol=wx_fog_color+wx_sun_color*(pow(mu,8.)*.55+pow(mu,48.)*.6);
  vec3 sandCol=wx_sand_color+wx_sun_color*vec3(1.,.8,.55)*(pow(mu,5.)*.45);
  // fumee grise et chaude, eclairee en orange par la lave (plus fort pres du sol et loin de la camera)
  float lowRay=exp(-max(rd.y,-.2)*2.5);
  vec3 smokeCol=mix(vec3(.46,.40,.36),vec3(.95,.42,.14),.42*lowRay)*(.55+.45*length(wx_sun_color))
               +wx_sun_color*vec3(1.,.85,.65)*pow(mu,6.)*.35;
  // brume du desert : poussiere chaude et lumineuse au ras du sable (air sec et chaud) ; tres loin, elle rejoint
  // le blanc-bleute du bas du ciel (meme couleur : pas de bande a l'horizon) ; eclat autour du soleil
  vec3 dustHaze=vec3(1.,.87,.72)*(.62+.34*min(length(wx_sun_color),1.2));
  vec3 farHaze=mix(wx_fog_color*1.1,vec3(.78,.87,.96),dayF);
  vec3 desertCol=mix(dustHaze,farHaze,smoothstep(400.,2600.,dist)*(1.-.8*mu*mu))
                +wx_sun_color*vec3(1.,.86,.62)*(pow(mu,6.)*.40+pow(mu,32.)*.35);
  vec3 col=(fogCol*tauFog+sandCol*tauSand+smokeCol*tauArena+desertCol*tauDesert)/tau;
  col+=vec3(.55,.6,.75)*wx_flash*.18;
  // sortie premultipliee ; desert (air chaud, ciel) : l'image retouchee remplace le pixel sous le voile
  color=replace?vec4(col*f+scene*(1.-f),1.):vec4(col*f,f);
}
