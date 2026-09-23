// Mer de Spargus v14 : eau verte, limpide et brillante. Reecriture complete de l'optique.
// Modele : fond vu a travers une eau claire (absorption par canal), diffusion verte croissant avec
// la profondeur, reflet du ciel/de la scene selon Fresnel, eclat solaire net + scintillement,
// ecume douce le long des cotes, sur les cretes en eau peu profonde et sur la plage.
uniform int modern_ocean;
uniform int ocean_far_plane;
uniform int ocean_horizon_pass;
uniform float ocean_time;
uniform mat4 ocean_camera;
uniform vec3 ocean_eye;
uniform vec3 ocean_body_color;
uniform vec3 ocean_reflection_tint;
// Region (Spargus, Haven...) : niveau de la mer et palette fournis par le moteur (ModernOcean.h)
#define OCEAN_LEVEL_DECLARED
uniform float ocean_level;
uniform vec3 ocean_shallow;
uniform vec3 ocean_deep;
uniform vec3 ocean_far;
uniform vec3 ocean_absorb;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
uniform sampler2D ocean_geometry_depth;
uniform sampler2D ocean_coast_mask;
uniform vec4 ocean_coast_map;
#ifdef OCEAN_SURFACE_GEOMETRY
in vec3 ocean_world;
#endif
// OCEAN_SWELL_INSERT
bool oceanContainsPoint(vec2 xz) {
  vec2 cell=floor((xz-ocean_coast_map.xy)/ocean_coast_map.z);
  // Au-dela de la carte native finie (4608 m), la mer lointaine native continue. A l'interieur,
  // on respecte les cellules d'exclusion de 3 m (sous les routes et les batiments).
  if(any(lessThan(cell,vec2(0.))) || any(greaterThanEqual(cell,vec2(ocean_coast_map.w))))return true;
  return texelFetch(ocean_coast_mask,ivec2(cell),0).r>.5;
}
vec3 oceanUnproject(vec2 uv,float depth) {
  vec4 h=vec4((uv*vec2(textureSize(tex_T25,0))-fluid_viewport.xy)/fluid_viewport.zw*2.-1.,depth*2.-1.,1.);
  h.y/=(512./416.)*.5;
  vec4 p=inverse(-ocean_camera)*h;
  return p.xyz/p.w/4096.+ocean_eye;
}
vec3 oceanProject(vec3 p) {
  vec4 h=-ocean_camera*vec4((p-ocean_eye)*4096.,1.);
  h.y*=(512./416.)*.5;
  vec3 n=h.xyz/h.w;
  return vec3((fluid_viewport.xy+(n.xy*.5+.5)*fluid_viewport.zw)/vec2(textureSize(tex_T25,0)),n.z*.5+.5);
}
bool oceanSkyDepth(float depth) {
  // Le ciel de Jak 3 (sky-work::draw-fog) ecrit un Z24 constant de 400 : c'est un fond
  // atmospherique, pas un decor qui masquerait la mer lointaine.
  const float step24=1./16777215.;
  return depth<=1.5*step24 || abs(depth-400.*step24)<=1.5*step24;
}
float oceanVisibleDepth(float surfaceDepth) {
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T26,0));
  float background=texture(tex_T26,uv).r;
  if(oceanSkyDepth(background) && background>2./16777215.)
    return max(surfaceDepth,background+2./16777215.);
  return surfaceDepth;
}
float oceanNoise(vec2 p){return swellNoise(p).x;}
// Vaguelettes de surface (v15b) : ondulations de bruit de valeur lisse a trois echelles (~2 m, ~0,8 m,
// ~0,35 m), gradient analytique, tournees et advectees dans des directions differentes. Aucune sinusoide :
// des trains periodiques faisaient des moires (anneaux, rayures). Un grain fin est reserve a l'eclat.
vec2 oceanRipples(vec2 xz,float footprint,out vec2 glitterSlope) {
  mat2 rot=mat2(.819,.574,-.574,.819),rot2=mat2(.6,.8,-.8,.6);
  vec2 q=rot*(xz-vec2(1700,-350)),q2=rot2*(xz-vec2(1700,-350));
  vec2 slope=vec2(0);
  vec3 r1=swellNoise(q*vec2(.5,.36)-ocean_time*vec2(.42,.17));
  slope+=transpose(rot)*(r1.yz*vec2(.5,.36))*.067*(1.-smoothstep(.5,1.8,footprint*.5));
  vec3 r2=swellNoise(q2*vec2(1.3,.95)+ocean_time*vec2(.28,-.41));
  slope+=transpose(rot2)*(r2.yz*vec2(1.3,.95))*.018*(1.-smoothstep(.5,1.8,footprint*1.3));
  vec3 r3=swellNoise(q*2.9-ocean_time*vec2(.6,.35));
  slope+=transpose(rot)*(r3.yz*2.9)*.0035*(1.-smoothstep(.4,1.5,footprint*2.9));
  vec3 g=swellNoise(q*7.-ocean_time*vec2(.9,.6));
  glitterSlope=transpose(rot)*(g.yz*7.)*.0019*(1.-smoothstep(.3,1.2,footprint*7.));
  return slope;
}
vec3 oceanSkySample(vec3 ray,float minimumElevation,out float confidence) {
  vec3 lookup=normalize(vec3(ray.x,max(ray.y,minimumElevation),ray.z));
  vec2 dimensions=vec2(textureSize(tex_T25,0));
  vec2 uv=oceanProject(ocean_eye+lookup*3500.).xy;
  vec2 low=(fluid_viewport.xy+vec2(1.5))/dimensions;
  vec2 high=(fluid_viewport.xy+fluid_viewport.zw-vec2(1.5))/dimensions;
  vec3 total=vec3(0);float weight=0.;
  const float offsets[5]=float[5](0.,4.,12.,32.,80.);
  for(int i=0;i<5;i++) {
    vec2 tap=clamp(uv+vec2(0,offsets[i])/dimensions,low,high);
    float valid=oceanSkyDepth(texture(tex_T26,tap).r) ? 1. : 0.;
    float w=valid*exp(-float(i)*.8);
    total+=texture(tex_T25,tap).rgb*w;weight+=w;
  }
  confidence=smoothstep(.015,.12,weight);
  return total/max(weight,.00001);
}
// Ciel : le vrai ciel de la scene (capture avant la mer) domine ; un degrade clair sert de secours.
vec3 oceanSkyFallback(vec3 ray) {
  return mix(vec3(.66,.70,.72),vec3(.44,.56,.70),smoothstep(0.,.6,ray.y));
}
const vec3 oceanSunDirection=normalize(vec3(-.32,.66,-.68));
const vec3 oceanSunColor=vec3(1.,.93,.78);
// Soleil dans le reflet : disque net et lueur large (le ciel natif n'a pas de soleil marque).
vec3 oceanSunReflection(vec3 ray) {
  float c=max(dot(ray,oceanSunDirection),0.);
  return oceanSunColor*(pow(c,1400.)*6.+pow(c,90.)*.45+pow(c,8.)*.06);
}
vec3 oceanSky(vec3 ray) {
  vec3 sky=oceanSkyFallback(ray);
  float confidence;
  vec3 sampled=oceanSkySample(ray,.012,confidence);
  sky=mix(sky,sampled,.88*smoothstep(-.025,.015,ray.y)*confidence);
  return sky*ocean_reflection_tint+oceanSunReflection(ray);
}
vec3 oceanHorizonSky(vec3 away) {
  float confidence;
  vec3 sampled=oceanSkySample(away,.018,confidence);
  return mix(oceanSkyFallback(away)*ocean_reflection_tint,sampled,confidence);
}
// Reflet adouci (3x3, pas de 3 px) : les bords des rochers refletes ne font pas d'escaliers.
vec3 blurredScene(vec2 uv) {
  vec2 px=vec2(3.)/vec2(textureSize(tex_T25,0));
  vec3 sum=texture(tex_T25,uv).rgb*.25;
  sum+=(texture(tex_T25,uv+vec2(px.x,0)).rgb+texture(tex_T25,uv-vec2(px.x,0)).rgb+
        texture(tex_T25,uv+vec2(0,px.y)).rgb+texture(tex_T25,uv-vec2(0,px.y)).rgb)*.125;
  sum+=(texture(tex_T25,uv+px).rgb+texture(tex_T25,uv-px).rgb+
        texture(tex_T25,uv+vec2(px.x,-px.y)).rgb+texture(tex_T25,uv+vec2(-px.x,px.y)).rgb)*.0625;
  return sum;
}
// Reflet : ciel par defaut, scene proche par lancer de rayon ecran (rochers, batiments, Jak).
vec3 oceanReflection(vec3 p,vec3 n,vec3 v) {
  vec3 r=reflect(-v,n),sky=oceanSky(r);
  if(length(p-ocean_eye)>220.)return sky;
  float lo=.12;
  for(int i=0;i<32;i++) {
    float hi=lo+.15+float(i)*.075;
    vec3 ray=p+n*.065+r*hi,uv=oceanProject(ray);
    if(any(lessThan(uv.xy,vec2(.006))) || any(greaterThan(uv.xy,vec2(.994))))break;
    float z=texture(tex_T26,uv.xy).r;
    if(z>uv.z && !oceanSkyDepth(z)) {
      float a=lo,b=hi;
      for(int j=0;j<8;j++) {
        float m=(a+b)*.5;vec3 probe=oceanProject(p+n*.065+r*m);
        if(texture(tex_T26,probe.xy).r>probe.z)b=m;else a=m;
      }
      ray=p+n*.065+r*((a+b)*.5);uv=oceanProject(ray);
      vec3 hit=oceanUnproject(uv.xy,texture(tex_T26,uv.xy).r);
      float error=length(hit-ray);
      float confidence=(1.-smoothstep(.12,.65,error))*smoothstep(p.y+.03,p.y+.4,hit.y);
      confidence*=smoothstep(.006,.075,min(min(uv.x,uv.y),min(1.-uv.x,1.-uv.y)));
      if(confidence>.001)return mix(sky,blurredScene(uv.xy),confidence*.72);
    }
    lo=hi;
  }
  return sky;
}
vec3 shadeModernOcean() {
  vec2 screen=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec3 p=ocean_world;
  float range=length(p-ocean_eye);
  vec3 v=normalize(ocean_eye-p);
  float footprint=max(length(dFdx(p.xz)),length(dFdy(p.xz)));
  // ---- Surface : houle (relief), contacts de Jak, vagues de bord, vaguelettes lisses, grain d'eclat
  vec3 swell=oceanSwellFiltered(p.xz,footprint);
  vec2 slopeBase=swell.yz+oceanContacts(p.xz).yz;
  vec2 shoreDir;vec4 shore=shoreWave(p.xz,ocean_time,shoreDir);
  if(any(notEqual(shore,vec4(0)))) {
    vec2 unused;float ahead=shoreWave(p.xz+shoreDir*.2,ocean_time,unused).x;
    slopeBase+=shoreDir*((ahead-shore.x)/.2);
  }
  vec2 glitterSlope;vec2 slopeRipple=oceanRipples(p.xz,footprint,glitterSlope);
  vec2 slope=slopeBase+slopeRipple;
  vec3 n=normalize(vec3(-slope.x,1.,-slope.y));                       // reflets, refraction, Fresnel
  vec3 nGlitter=normalize(vec3(-(slope.x+glitterSlope.x),1.,-(slope.y+glitterSlope.y)));   // eclat solaire
  // ---- Sous l'eau : fenetre de Snell
  if(ocean_eye.y < p.y) {
    n=-n;
    float facing=max(dot(n,v),0.);
    float window=smoothstep(.61,.72,facing);
    vec2 uv=clamp(screen+n.xz*.006,vec2(.001),vec2(.999));
    return mix(ocean_deep*1.5,texture(tex_T25,uv).rgb,window*.90);
  }
  // ---- Fond et epaisseur d'eau traversee
  float depth=texture(tex_T26,screen).r,thickness=60.;
  bool hasBed=false;vec3 bedScene=vec3(0);vec3 bed=p;
  if(!oceanSkyDepth(depth) && depth<gl_FragCoord.z) {
    bed=oceanUnproject(screen,depth);thickness=clamp(length(bed-p),0.,60.);
    vec2 uv=clamp(screen+n.xz*.035*min(thickness,2.)/max(range*.03,1.),vec2(.001),vec2(.999));
    if(texture(tex_T26,uv).r>gl_FragCoord.z)uv=screen;
    bedScene=texture(tex_T25,uv).rgb;hasBed=true;
  }
  // ---- Corps de l'eau : fond vu a travers une eau claire, caustiques, diffusion selon la profondeur
  vec3 transmission=exp(-ocean_absorb*thickness);
  float caustic=0.;
  if(hasBed) {
    vec2 q=bed.xz*1.7;
    float c1=swellNoise(q+ocean_time*vec2(.31,.17)).x,c2=swellNoise(q*1.9-ocean_time*vec2(.23,.29)).x;
    caustic=pow(max(1.-abs(c1-c2)*2.6,0.),3.)*exp(-thickness*.55)*max(dot(n,oceanSunDirection),0.);
  }
  vec3 scatter=mix(ocean_deep,ocean_shallow,exp(-thickness*.20));
  vec3 body=hasBed ? bedScene*(1.+caustic*1.1)*transmission+scatter*(1.-transmission) : ocean_deep;
  float crest=smoothstep(0.,.55,swell.x);
  body+=ocean_shallow*.18*crest;
  float far=smoothstep(80.,700.,range);
  body=mix(body,ocean_far,far*.7);
  // Ombrage des ondulations : la face des vaguelettes tournee vers le soleil s'eclaire, l'autre s'assombrit.
  // Sans cela, vue du dessus, l'eau devient un plan uni ou les vagues n'existent plus.
  float shade=dot(n,oceanSunDirection)*.5+.5;
  body*=mix(.72,1.30,shade);
  // ---- Reflet : le ciel (avec soleil) et le decor proche ; Fresnel releve pour une surface bien miroir
  float facing=max(dot(n,v),0.);
  float fresnel=.09+.91*pow(1.-facing,4.);
  vec3 reflection=oceanReflection(p,n,v);
  vec3 result=mix(body,reflection,fresnel);
  // ---- Trainee de soleil : scintillement serre sur le grain, lobe doux sur les vaguelettes
  vec3 h=normalize(oceanSunDirection+v);
  float sunVis=max(dot(n,oceanSunDirection),0.);
  float glitter=pow(max(dot(nGlitter,h),0.),900.);
  float sheen=pow(max(dot(n,h),0.),70.);
  result+=oceanSunColor*(glitter*2.2+sheen*.14)*sunVis*mix(1.,.6,far);
  // ---- Ecume : sillage de Jak, lisere des cotes, moutons en eau peu profonde, plage
  float foamNoise=.45*smoothstep(.35,.85,oceanNoise(p.xz*2.3+ocean_time*vec2(.3,-.15)))
                 +.55*smoothstep(.45,.9,oceanNoise(p.xz*8.5-ocean_time*vec2(.7,.3)));
  float wake=0.;
  for(int i=0;i<32;i++) {
    float age=ocean_time-fluid_contacts[i].w;
    if(fluid_strength[i]<=0. || age<0. || age>2. || abs(fluid_contacts[i].y-ocean_level)>1.)continue;
    float d=length(p.xz-fluid_contacts[i].xz);
    wake+=exp(-d*d/1.6-age*2.0)*smoothstep(.03,.10,fluid_strength[i])*.26;
  }
  float shoreFoam=(1.-smoothstep(.10,.8,thickness))*(.35+.65*foamNoise)*.65;
  float crestFoam=smoothstep(.45,.9,crest)*smoothstep(5.,1.2,thickness)*foamNoise*.7;
  float beachFoam=shore.y*(.25+.95*foamNoise)+shore.z*(.12+.6*foamNoise)+shore.w*.95;
  float foam=clamp(max(max(wake*foamNoise*1.2,shoreFoam),max(crestFoam,beachFoam)),0.,.92);
  result=mix(result,vec3(.88,.91,.90),foam);
  // ---- Brume vers le vrai ciel de l'horizon, puis extinction au tres loin
  vec3 horizonSky=oceanHorizonSky(-v);
  float haze=1.-exp(-range*.0007);
  result=mix(result,horizonSky,haze*.5);
  if(range<=750.)return result;
  float extinction=1.-exp(-max(range-750.,0.)*.0006);
  return mix(result,horizonSky,extinction);
}
vec4 shadeOceanHorizon() {
  vec2 screen=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec3 ray=normalize(ocean_world);
  float pixelAngle=max(fwidth(ray.y),.00001);
  float band=abs(ray.y)/pixelAngle;
  if(band>8.)discard;
  if(!oceanSkyDepth(texture(ocean_geometry_depth,screen).r))discard;
  float confidence;
  vec3 sky=oceanSkySample(ray,max(.008,pixelAngle*10.),confidence);
  float coverage=(1.-smoothstep(5.,8.,band))*confidence;
  vec3 current=texture(tex_T25,screen).rgb;
  return vec4(mix(current,sky,coverage),1.);
}
