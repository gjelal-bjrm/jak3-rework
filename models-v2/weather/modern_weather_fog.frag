#version 410 core
// Atmosphere meteo (apres le decor, les particules et la mer ; avant l'interface) :
//  - voile de pluie / neige : densite uniforme, les lointains se fondent dans le gris du ciel couvert ;
//  - brouillard matinal : brouillard de hauteur exponentiel (epais au ras de l'eau, ciel visible au-dessus),
//    integre analytiquement le long du rayon ;
//  - tempete de sable : nuee ocre animee par rafales qui defilent dans le sens du vent, plus dense au sol.
// Le soleil eclaire le brouillard vers l'avant (halo). Sortie premultipliee (ONE, ONE_MINUS_SRC_ALPHA).
in vec3 view_ray;
out vec4 color;
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
void main(){
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T26,0));
  float depth=texture(tex_T26,uv).r;
  vec3 rd=normalize(view_ray);
  float dist=3000.;
  if(!skyDepth(depth)) dist=min(length(unproject(uv,depth)),3000.);
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
  float tau=tauFog+tauSand;
  if(tau<1e-4){color=vec4(0.);return;}
  float f=1.-exp(-tau);
  vec3 L=normalize(wx_sun);
  float mu=max(dot(rd,L),0.);
  vec3 fogCol=wx_fog_color+wx_sun_color*(pow(mu,8.)*.55+pow(mu,48.)*.6);
  vec3 sandCol=wx_sand_color+wx_sun_color*vec3(1.,.8,.55)*(pow(mu,5.)*.45);
  vec3 col=(fogCol*tauFog+sandCol*tauSand)/tau;
  col+=vec3(.55,.6,.75)*wx_flash*.18;
  color=vec4(col*f,f);
}
