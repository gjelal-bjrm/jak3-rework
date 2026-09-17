// Spargus sea optics. Palette is supplied per region by the renderer.
uniform int modern_ocean;
uniform int ocean_far_plane;
uniform int ocean_horizon_pass;
uniform float ocean_time;
uniform mat4 ocean_camera;
uniform vec3 ocean_eye;
uniform vec3 ocean_body_color;
uniform vec3 ocean_reflection_tint;
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
  // Retain the native far ocean beyond its finite 4608m map. Inside it,
  // use the exact authored 3m exclusion cells rather than the camera region.
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
  // Jak 3's sky-work::draw-fog writes packed XYZF2 Z=6400. DirectRenderer
  // shifts that by four bits, then divides by 0xffffff: a flat Z24 value 400.
  // This is atmospheric background, not scenery occluding the distant sea.
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
vec3 oceanSurface(vec3 p,out float wake) {
  float footprint=max(length(dFdx(p.xz)),length(dFdy(p.xz)));
  vec3 swell=oceanSwellFiltered(p.xz,footprint);
  vec2 slope=swell.yz;
  // Advected, rotated noise has no straight, intersecting wave trains.
  mat2 rotation=mat2(.819,.574,-.574,.819);
  vec2 q=rotation*(p.xz-vec2(1700,-350));
  for(int i=0;i<3;i++) {
    float fi=float(i),k=1.7*pow(2.13,fi);
    vec2 scale=vec2(k,k*.72);
    vec3 rip=swellNoise(q*scale-ocean_time*vec2(.67,.19)+fi*vec2(19.7,32.1));
    slope+=transpose(rotation)*(rip.yz*scale)*(.029*pow(.35,fi))*(1.-smoothstep(.55,1.8,k*footprint));
  }
  vec3 contact=oceanContacts(p.xz);
  slope+=contact.yz;
  wake=0.;
  for(int i=0;i<32;i++) {
    float age=ocean_time-fluid_contacts[i].w;
    if(fluid_strength[i]<=0. || age<0. || age>2. || abs(fluid_contacts[i].y-9.)>1.)continue;
    float d=length(p.xz-fluid_contacts[i].xz);
    wake+=exp(-d*d/1.3-age*2.4)*smoothstep(.03,.10,fluid_strength[i])*.16;
  }
  return normalize(vec3(-slope.x,1.,-slope.y));
}
vec3 oceanSkySample(vec3 ray,float minimumElevation,out float confidence) {
  vec3 lookup=normalize(vec3(ray.x,max(ray.y,minimumElevation),ray.z));
  vec2 dimensions=vec2(textureSize(tex_T25,0));
  vec2 uv=oceanProject(ocean_eye+lookup*3500.).xy;
  vec2 low=(fluid_viewport.xy+vec2(1.5))/dimensions;
  vec2 high=(fluid_viewport.xy+fluid_viewport.zw-vec2(1.5))/dimensions;
  vec3 total=vec3(0);float weight=0.;
  // Clamp at the viewport edge instead of switching the entire last 1% of
  // the image to a solid fallback. Higher taps look past distant palm leaves.
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
  return mix(vec3(.62,.66,.70),vec3(.42,.53,.68),smoothstep(0.,.6,ray.y));
}
vec3 oceanSky(vec3 ray) {
  vec3 sky=oceanSkyFallback(ray);
  float confidence;
  vec3 sampled=oceanSkySample(ray,.012,confidence);
  sky=mix(sky,sampled,.88*smoothstep(-.025,.015,ray.y)*confidence);
  return sky*ocean_reflection_tint;
}
vec3 oceanHorizonSky(vec3 away) {
  float confidence;
  vec3 sampled=oceanSkySample(away,.018,confidence);
  return mix(oceanSkyFallback(away)*ocean_reflection_tint,sampled,confidence);
}
vec3 blurredScene(vec2 uv) {
  vec2 px=vec2(2.)/vec2(textureSize(tex_T25,0));
  return texture(tex_T25,uv).rgb*.4+
    (texture(tex_T25,uv+vec2(px.x,0)).rgb+texture(tex_T25,uv-vec2(px.x,0)).rgb+
     texture(tex_T25,uv+vec2(0,px.y)).rgb+texture(tex_T25,uv-vec2(0,px.y)).rgb)*.15;
}
vec3 oceanReflection(vec3 p,vec3 n,vec3 v) {
  vec3 r=reflect(-v,n),sky=oceanSky(r);
  if(length(p-ocean_eye)>140.)return sky;
  float lo=.12;
  for(int i=0;i<32;i++) {
    float hi=lo+.15+float(i)*.075;
    vec3 ray=p+n*.065+r*hi,uv=oceanProject(ray);
    if(any(lessThan(uv.xy,vec2(.006))) || any(greaterThan(uv.xy,vec2(.994))))break;
    float z=texture(tex_T26,uv.xy).r;
    if(z>uv.z && !oceanSkyDepth(z)) {
      // Refine the crossing rather than selecting a discrete march step.
      // This removes the horizontal bands made by coarse hit/miss thresholds.
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
  float range=length(p-ocean_eye),wake;
  vec3 n=oceanSurface(p,wake),v=normalize(ocean_eye-p);
  if(ocean_eye.y < p.y) {
    n=-n;
    float facing=max(dot(n,v),0.);
    // Snell's window: surface is reflective outside the escape cone.
    float window=smoothstep(.61,.72,facing);
    vec2 uv=clamp(screen+n.xz*.006,vec2(.001),vec2(.999));
    return mix(vec3(.10,.16,.14),texture(tex_T25,uv).rgb,window*.90);
  }
  vec3 deep=ocean_body_color,body=deep;
  float depth=texture(tex_T26,screen).r,thickness=40.;
  if(!oceanSkyDepth(depth) && depth<gl_FragCoord.z) {
    vec3 bed=oceanUnproject(screen,depth);thickness=clamp(length(bed-p),0.,40.);
    vec2 uv=clamp(screen+n.xz*.012*min(thickness,1.),vec2(.001),vec2(.999));
    if(texture(tex_T26,uv).r>gl_FragCoord.z)uv=screen;
    vec3 transmission=exp(-vec3(.65,.38,.45)*thickness);
    body=texture(tex_T25,uv).rgb*transmission+deep*(1.-transmission);
  }
  float facing=max(dot(n,v),0.);
  float fresnel=.035+.90*pow(1.-facing,5.);
  // Corps : avec la distance, l'eau s'eclaircit vers un vert grise (diffusion), jamais bleu.
  float far=smoothstep(60.,600.,range);
  body=mix(body,vec3(.16,.23,.20),far*.85);
  // Diffusion sous la surface sur les cretes : vert d'eau plus clair.
  float height=oceanSwell(p.xz).x;
  float crest=smoothstep(.05,.32,height);
  body+=vec3(.06,.13,.10)*crest*(1.-far*.6);
  vec3 result=mix(body,oceanReflection(p,n,v),fresnel);
  // A soft sky lobe makes small wave curvature readable from above.
  float skyLobe=pow(max(dot(n,normalize(v+vec3(-.3,.78,-.43))),0.),36.);
  result+=vec3(.16,.18,.17)*skyLobe*.20;
  // Soleil : reflet etroit de pres, scintillement large au loin (rugosite croissante).
  vec3 light=normalize(vec3(-.32,.66,-.68));
  float a2=mix(.0225,.075,far);
  float nh=max(dot(n,normalize(light+v)),0.);
  float spec=a2/(3.14159*pow(max(.006,nh*nh*(a2-1.)+1.),2.));
  result+=vec3(1.,.88,.62)*min(spec*mix(.007,.014,far),.6)*max(dot(n,light),0.);
  // Ecume : contacts de Jak, berges, et moutons epars sur les cretes a moyenne distance.
  float noise=oceanNoise(p.xz*7.-ocean_time*vec2(.65,.31));
  float bubbles=smoothstep(.68,.88,noise);
  float coast=(1.-smoothstep(.15,1.1,thickness))*smoothstep(.03,.25,height);
  // (moutons de crete retires : le bruit grossier faisait des taches rectangulaires de pres)
  float foam=clamp(wake*bubbles+coast*bubbles*.16,0.,.22);
  result=mix(result,vec3(.72,.78,.75),foam);
  // Brume : vers le vrai ciel de l'horizon, pas vers un gris fixe.
  vec3 horizonSky=oceanHorizonSky(-v);
  float haze=1.-exp(-range*.0007);
  result=mix(result,horizonSky,haze*.55);
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
  // The second snapshot contains the new sea. The first snapshot's depth
  // masks every island, building and character before any sea was drawn.
  if(!oceanSkyDepth(texture(ocean_geometry_depth,screen).r))discard;
  float confidence;
  vec3 sky=oceanSkySample(ray,max(.008,pixelAngle*10.),confidence);
  // The legacy sky uses a +/-1 GS-pixel offset (about 2.6 pixels at 1080p).
  // Fully cover that seam, then feather the outer three pixels of the band.
  float coverage=(1.-smoothstep(5.,8.,band))*confidence;
  vec3 current=texture(tex_T25,screen).rgb;
  return vec4(mix(current,sky,coverage),1.);
}
