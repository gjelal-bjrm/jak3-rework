// Houle de Spargus v14 : trains de vagues directionnels qui roulent vers la cote (profil de Gerstner
// simplifie, cretes pointues, creux plats) + houle irreguliere bruitee. Hauteur et derivees analytiques,
// partagees par le vertex shader (relief) et le fragment (normale).
float swellHash(vec2 p) {return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
vec3 swellNoise(vec2 p) {
  vec2 i=floor(p),f=fract(p);
  vec2 u=f*f*f*(f*(f*6.-15.)+10.);
  vec2 du=30.*f*f*(f*(f-2.)+1.);
  float a=swellHash(i),b=swellHash(i+vec2(1,0)),c=swellHash(i+vec2(0,1)),d=swellHash(i+vec2(1));
  float k=a-b-c+d;
  return vec3(a+(b-a)*u.x+(c-a)*u.y+k*u.x*u.y,
              du.x*(b-a+k*u.y),du.y*(c-a+k*u.x));
}
#ifndef OCEAN_LEVEL_DECLARED
#define OCEAN_LEVEL_DECLARED
uniform float ocean_level;
#endif
uniform float ocean_swell_scale;
// SHORE_WAVES_INSERT
// Direction dominante des grandes vagues : du large (sud-ouest) vers la baie et la plage.
const vec2 swellDirection=vec2(.55,.835);
vec2 swellRotate(vec2 d,float a){float c=cos(a),s=sin(a);return vec2(c*d.x-s*d.y,s*d.x+c*d.y);}
// Un train de vagues : x hauteur, yz gradient. Profil asymetrique : cretes plus pointues, creux plus plats.
vec3 swellTrain(vec2 p,vec2 d,float wavelength,float amplitude,float offset,float footprint) {
  float k=6.2831853/wavelength,w=sqrt(9.81*k);
  // Les cretes ne sont pas des droites : un bruit lent deforme la phase le long du front (± ~1,3 rad).
  vec3 warp=swellNoise(p*k*.11+vec2(offset*3.1,ocean_time*.02));
  float phase=dot(p,d)*k-ocean_time*w+offset+2.6*(warp.x-.5);
  vec2 gradient=k*d+2.6*warp.yz*k*.11;
  float resolved=1.-smoothstep(.65,2.8,footprint*k);
  float h=sin(phase)-.18*cos(2.*phase);
  float dh=cos(phase)+.36*sin(2.*phase);
  return amplitude*resolved*vec3(h,dh*gradient);
}
vec3 oceanSwellFiltered(vec2 p,float footprint) {
  vec2 cameraDelta=p-ocean_eye.xz;
  vec2 world=p;
  p-=vec2(1700.,-350.);vec3 result=vec3(0);
  // 1. Grandes vagues vers la cote (44, 27, 15 et 8,5 m). Elles s'effacent sur la plage, ou les
  //    vagues de bord prennent le relais ; elles frappent les cotes rocheuses de plein fouet.
  vec2 unused;float coast=smoothstep(-6.,30.,shoreSigned(world,unused))*ocean_swell_scale;   // amplitude des grandes vagues par region (bassin portuaire calme)
  vec2 d=normalize(swellDirection);
  result+=swellTrain(p,d,44.,.42,0.,footprint)*coast;
  result+=swellTrain(p,swellRotate(d,.21),27.,.26,2.1,footprint)*coast;
  result+=swellTrain(p,swellRotate(d,-.26),15.,.12,4.3,footprint)*coast;
  result+=swellTrain(p,swellRotate(d,.44),8.5,.05,1.2,footprint)*coast;
  // 2. Houle irreguliere : paquets de vagues deformes par du bruit, sans trains rectilignes visibles.
  const float ks[8]=float[8](.155,.241,.363,.526,.737,1.05,1.48,2.14);
  const float amps[8]=float[8](.18,.09,.05,.03,.018,.010,.006,.003);
  for(int i=0;i<8;i++) {
    float fi=float(i),angle=.48+.23*sin(fi*2.39);
    vec2 dd=vec2(cos(angle),sin(angle));float k=ks[i];
    vec3 warp=swellNoise(p*k*.17+vec2(fi*17.1,ocean_time*.047));
    float phase=dot(p,dd)*k-ocean_time*sqrt(9.81*k)+3.8*warp.x+fi*2.14;
    vec2 gradient=k*dd+3.8*warp.yz*k*.17;
    float resolved=1.-smoothstep(.65,2.8,footprint*k);
    result.x+=amps[i]*resolved*(sin(phase)+.08*sin(phase*2.));
    result.yz+=amps[i]*resolved*(cos(phase)+.16*cos(phase*2.))*gradient;
  }
  // 3. Au loin, les composantes fines deviennent sous-pixel : une houle longue prend le relais pour
  //    que la mer ne devienne pas une bande plate.
  float distance=max(length(cameraDelta),.001);
  if(distance<=120.)return result;
  vec3 distant=vec3(0);
  const float longKs[3]=float[3](.05236,.02327,.01102);
  const float longAmps[3]=float[3](.22,.18,.12);
  for(int i=0;i<3;i++) {
    float fi=float(i),angle=.31+fi*.19,k=longKs[i];
    vec2 dd=vec2(cos(angle),sin(angle));
    vec3 warp=swellNoise(p*k*.27+vec2(fi*31.7,ocean_time*.012));
    float phase=dot(p,dd)*k-ocean_time*sqrt(9.81*k)+3.1*warp.x+fi*4.37;
    vec2 gradient=k*dd+3.1*warp.yz*k*.27;
    float resolved=1.-smoothstep(.65,2.8,footprint*k);
    distant+=longAmps[i]*resolved*vec3(sin(phase),cos(phase)*gradient);
  }
  float blend=smoothstep(120.,640.,distance);
  float u=clamp((distance-120.)/520.,0.,1.);
  vec2 blendGradient=cameraDelta/distance*(6.*u*(1.-u)/520.);
  result+=distant*blend;
  result.yz+=distant.x*blendGradient;
  return result;
}
vec3 oceanSwell(vec2 p){return oceanSwellFiltered(p,0.);}
// Phase de la grande vague dominante (0..1, 1 = crete) : sert aux moutons de crete du fragment.
float oceanCrestPhase(vec2 p) {
  p-=vec2(1700.,-350.);
  float k=6.2831853/44.,w=sqrt(9.81*k);
  return .5+.5*sin(dot(p,normalize(swellDirection))*k-ocean_time*w);
}
uniform vec4 fluid_contacts[32];
uniform float fluid_strength[32];
vec3 oceanContacts(vec2 p) {
  vec3 result=vec3(0);
  for(int i=0;i<32;i++) {
    float age=ocean_time-fluid_contacts[i].w;
    if(fluid_strength[i]<=0. || age<0. || age>4. || abs(fluid_contacts[i].y-ocean_level)>1.)continue;
    vec2 delta=p-fluid_contacts[i].xz;float d=max(length(delta),.001);
    if(d>7.)continue;
    float q=d-(.10+age*1.4),width=.24+age*.13;
    float e=exp(-q*q/(width*width)-age*1.10)*fluid_strength[i]*.65;
    result.x+=e*cos(q*10.);
    result.yz+=delta/d*e*(-10.*sin(q*10.)-2.*q/(width*width)*cos(q*10.));
  }
  return result;
}
