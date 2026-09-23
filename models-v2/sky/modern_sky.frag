#version 410 core
// Ciel moderne de Jak 3 (remaster). Sur les pixels de ciel :
//  1. degrade d'ambiance natif du niveau (conserve : c'est lui qui porte l'identite de chaque zone) ;
//  2. eclaircissement vers le soleil (diffusion), soleil : disque net + lueur ;
//  3. nuages : couche principale (cumulus, ~1,6 km) eclairee par le soleil avec ombre propre et lisere
//     lumineux, plus une couche haute de cirrus etires par le vent ; les deux s'ecrasent dans la brume
//     d'horizon ;
//  4. etoile du jour (vaisseau des Dark Makers) : coeur blanc-violet, halo, anneau d'eco noir qui ondule,
//     quatre aigrettes, pulsation lente.
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
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){
  vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);
}
float fbm(vec2 p){
  float v=0.,a=.5;mat2 r=mat2(.8,.6,-.6,.8);
  for(int i=0;i<5;i++){v+=a*noise(p);p=r*p*2.03+vec2(7.1,3.7);a*=.5;}
  return v;
}
// Densite de la couche principale au point plan p (m). Grandes masses + detail, seuil par couverture.
float cloudDensity(vec2 p,float coverage){
  float shape=fbm(p*.00055+vec2(sky_time*.0011,0.));
  float detail=fbm(p*.0028-vec2(0.,sky_time*.0021));
  // fbm vaut ~0,3-0,65 : on etire son contraste avant le seuil de couverture.
  float d=(shape*.7+detail*.3-.47)*3.2+.5;
  float threshold=.92-coverage*.9;                      // couverture .36 -> .60 ; .54 -> .43
  return smoothstep(threshold,threshold+.42,d);
}
void main(){
  vec2 screen=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec3 native=texture(tex_T25,screen).rgb;
  if(!skyDepth(texture(tex_T26,screen).r)){color=vec4(native,1.);return;}
  vec3 ray=normalize(sky_ray);
  vec3 sun=normalize(sky_sun);
  float sunUp=clamp(sun.y*2.5,0.,1.);                  // 0 sous l'horizon, 1 des 24 deg d'elevation
  vec3 sunColor=mix(vec3(1.,.62,.32),vec3(1.,.96,.88),sunUp);
  // Couleur de brume a l'horizon dans la direction du pixel (echantillon natif juste au-dessus de l'horizon)
  vec3 horizonRay=normalize(vec3(ray.x,max(.03,ray.y*.15),ray.z));
  vec2 huv=clamp(project(horizonRay),vec2(.003),vec2(.997));
  vec3 haze=skyDepth(texture(tex_T26,huv).r)?texture(tex_T25,huv).rgb:native;
  vec3 result=native;
  // ---- Diffusion vers le soleil : le ciel s'eclaircit et se rechauffe autour de lui, surtout bas.
  float toSun=max(dot(ray,sun),0.);
  result+=sunColor*haze*pow(toSun,4.)*.22*(1.-.6*clamp(ray.y*3.,0.,1.));
  // ---- Nuages (au-dessus de l'horizon seulement)
  if(ray.y>.005){
    float y=max(ray.y,.02);
    // Couche principale : cumulus a 1,6 km, epaisseur simulee 500 m.
    vec2 p=ray.xz/y*1600.+vec2(sky_time*9.,sky_time*3.5);
    float far=exp(-length(ray.xz/y*1600.)*.000038);          // les nuages lointains fondent dans la brume
    float d=cloudDensity(p,sky_coverage);
    if(d>.001){
      // ombre propre : densite decalee vers le soleil (les bords tournes vers lui sont eclaires)
      vec2 toward=sun.xz/max(sun.y,.18)*420.;
      float dSun=cloudDensity(p+toward,sky_coverage);
      float lit=exp(-dSun*2.6)*.75+.25*(1.-d);
      float powder=1.-exp(-d*4.);                              // bords fins plus clairs, coeur plus dense
      vec3 ambient=mix(native,vec3(.62,.66,.74),.25)*1.15;
      vec3 shade=ambient*.62;
      vec3 bright=mix(ambient,sunColor,.55)*1.25;
      vec3 cloud=mix(shade,bright,lit*powder);
      // lisere lumineux : diffusion avant a travers les bords minces
      float rim=pow(toSun,14.)*(1.-d)*d*3.2;
      cloud+=sunColor*rim;
      float alpha=smoothstep(.0,.55,d)*(1.-exp(-d*2.2))*far*smoothstep(.0,.06,ray.y);
      result=mix(result,mix(cloud,haze,1.-far),alpha*.96);
    }
    // Cirrus : haute couche etiree dans le sens du vent, tres legere.
    if(ray.y>.04){
      vec2 q=ray.xz/y*7000.+vec2(sky_time*22.,sky_time*4.);
      mat2 stretch=mat2(.96,.28,-.28,.96);
      q=stretch*q;q.y*=3.6;
      float c=fbm(q*.00016)*.6+fbm(q*.0007+vec2(3.3,1.1))*.4;
      float cirrus=smoothstep(.58,.82,c)*smoothstep(.04,.2,ray.y)*exp(-length(ray.xz/y)*.09);
      vec3 cirrusColor=mix(vec3(.93,.94,.97),sunColor,.3*pow(toSun,3.));
      result=mix(result,cirrusColor,cirrus*.42);
    }
  }
  // ---- Soleil : disque net, couronne, lueur large (par-dessus les nuages, attenue par eux via la brume)
  {
    float c=dot(ray,sun);
    float disc=smoothstep(.99990,.99997,c);
    float corona=pow(max(c,0.),600.)*.7+pow(max(c,0.),2500.)*.6;
    float glow=pow(max(c,0.),40.)*.35+pow(max(c,0.),7.)*.06;
    result+=sunColor*(disc*1.5+corona)*step(0.,sun.y+.05)+sunColor*glow*(.6+.4*sunUp);
  }
  // ---- Etoile du jour : le vaisseau des Dark Makers, fixe dans le ciel.
  if(sky_day_star_on>.5){
    vec3 ds=normalize(sky_day_star);
    float c=dot(ray,ds);
    if(c>.985){
      float angle=acos(clamp(c,-1.,1.));                       // rad depuis le centre
      vec3 right=normalize(cross(ds,vec3(0.,1.,0.)));vec3 up=cross(right,ds);
      vec2 local=vec2(dot(ray,right),dot(ray,up));
      float pulse=.88+.12*sin(sky_time*1.7)+.05*sin(sky_time*4.3);
      vec3 core=vec3(.92,.86,1.);
      vec3 violet=vec3(.62,.38,1.);
      vec3 dark=vec3(.30,.06,.48);
      float coreDisc=smoothstep(.0075,.0025,angle);
      float halo=exp(-angle*angle/(2.*.006*.006))*.9+exp(-angle*angle/(2.*.02*.02))*.35;
      // anneau d'eco noir : rayon ~1,6 deg, epaisseur variable, tourne lentement
      float theta=atan(local.y,local.x);
      float wobble=.0022*sin(theta*5.+sky_time*.9)+.0012*sin(theta*9.-sky_time*1.7);
      float ring=exp(-pow((angle-.040-wobble)*420.,2.))*(.45+.55*noise(vec2(theta*3.+sky_time*.4,sky_time*.2)));
      // quatre aigrettes fines
      float spikes=(exp(-abs(local.x)*900.)*exp(-abs(local.y)*40.)+exp(-abs(local.y)*900.)*exp(-abs(local.x)*40.))*smoothstep(.06,.0,angle);
      vec3 star=core*coreDisc*2.4*pulse+violet*halo*pulse+violet*spikes*.9;
      result=mix(result,dark,ring*.40*smoothstep(.0,.008,angle));
      result+=star;
      result+=violet*ring*.12;
    }
  }
  color=vec4(result,1.);
}
