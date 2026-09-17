#version 410 core
in vec2 uv;
out vec4 color;
uniform sampler2D native_clouds;
uniform float cloud_time;

// Periodic noise: every octave and both domain-warp fields join across the
// repeated cloud dome. Quintic interpolation has continuous second derivatives.
float cloudHash(vec2 cell) {
  vec3 p=fract(vec3(cell.xyx)*vec3(.1031,.1030,.0973));
  p+=dot(p,p.yzx+33.33);
  return fract((p.x+p.y)*p.z);
}
float cloudNoise(vec2 p,float cells,vec2 drift) {
  p=p*cells+drift;
  vec2 i=floor(p),f=fract(p);
  vec2 w=f*f*f*(f*(f*6.0-15.0)+10.0);
  float a=cloudHash(mod(i,cells));
  float b=cloudHash(mod(i+vec2(1,0),cells));
  float c=cloudHash(mod(i+vec2(0,1),cells));
  float d=cloudHash(mod(i+vec2(1,1),cells));
  return mix(mix(a,b,w.x),mix(c,d,w.x),w.y);
}
float cloudBody(vec2 p) {
  float t=cloud_time;
  vec2 warp=vec2(cloudNoise(p,5.0,vec2(.006,-.004)*t),
                 cloudNoise(p,7.0,vec2(-.005,.007)*t+17.3))-.5;
  p+=warp*.07;
  float banks=cloudNoise(p,7.0,vec2(.005,.003)*t+3.7);
  float lobes=cloudNoise(p,17.0,vec2(-.008,.005)*t+11.2);
  float curls=cloudNoise(p,37.0,vec2(.009,-.011)*t+21.4);
  float wisps=cloudNoise(p,83.0,vec2(-.015,-.006)*t+7.9);
  return .51*banks+.29*lobes+.145*curls+.055*wisps;
}
float cloudHash3(vec3 p) {
  p=fract(p*.1031);p+=dot(p,p.yzx+33.33);
  return fract((p.x+p.y)*p.z);
}
float cloudNoise3(vec3 p,float cells,vec3 drift) {
  p=p*cells+drift;
  vec3 i=floor(p),f=fract(p);
  vec3 w=f*f*f*(f*(f*6.0-15.0)+10.0);
  float a=mix(cloudHash3(mod(i,cells)),cloudHash3(mod(i+vec3(1,0,0),cells)),w.x);
  float b=mix(cloudHash3(mod(i+vec3(0,1,0),cells)),cloudHash3(mod(i+vec3(1,1,0),cells)),w.x);
  float c=mix(cloudHash3(mod(i+vec3(0,0,1),cells)),cloudHash3(mod(i+vec3(1,0,1),cells)),w.x);
  float d=mix(cloudHash3(mod(i+vec3(0,1,1),cells)),cloudHash3(mod(i+vec3(1,1,1),cells)),w.x);
  return mix(mix(a,b,w.y),mix(c,d,w.y),w.z);
}
float cloudVolume(vec3 p) {
  return .56*cloudNoise3(p,13.0,vec3(.004,-.003,.004)*cloud_time+11.1)
        +.29*cloudNoise3(p,29.0,vec3(-.007,.005,-.003)*cloud_time+27.4)
        +.15*cloudNoise3(p,61.0,vec3(.012,.007,.006)*cloud_time+41.3);
}
float cloudDensity(vec3 p,float coverage,float billow) {
  // Coverage places the banks; it must not overwhelm and saturate their volume.
  // Erosion remains visible inside a fully white native bank as well as its edge.
  float z=p.z/.17;
  float shape=.48*coverage+.38*(billow-.5)+1.48*(cloudVolume(p)-.5)-.10-.50*z*z;
  return max(0.0,shape)*2.9;
}
void main() {
  // Native GOAL min/max, weather, day/night and cloud scrolling still define
  // coverage. This private texture is sampled by both original lighting layers.
  float original=clamp(textureLod(native_clouds,uv,0.0).a*2.0,0.0,1.0);
  float broad=clamp(textureLod(native_clouds,uv,3.0).a*2.0,0.0,1.0);
  float envelope=smoothstep(.018,.18,broad);
  float billow=cloudBody(uv);
  // Integrate through a shallow volume. Rounded density lobes change their
  // visible front depth, giving soft, coherent internal form rather than a
  // uniformly coloured opaque cutout or unrelated noise on top of a mask.
  float transmittance=1.0,scattering=0.0;
  for(int sampleIndex=0;sampleIndex<10;sampleIndex++) {
    float z=1.0-(float(sampleIndex)+.5)*.2;
    vec3 p=vec3(uv,z*.17);
    float density=cloudDensity(p,broad,billow)*envelope;
    float stepOpacity=1.0-exp(-density*.40);
    // Light must traverse neighbouring lobes: front-depth tint alone made the
    // dense native banks uniformly cream. Neutral self-shadow retains the GOAL
    // sun/moon palette while describing coherent interiors and rounded edges.
    float blocker1=cloudDensity(p+vec3(-.018,.012,.052),broad,billow);
    float blocker2=cloudDensity(p+vec3(-.037,.025,.109),broad,billow);
    float illumination=exp(-1.5*(blocker1+blocker2));
    float ambient=.38+.69*illumination;
    scattering+=transmittance*stepOpacity*ambient;
    transmittance*=1.0-stepOpacity;
  }
  float opacity=1.0-transmittance;
  float bodyShade=scattering/max(.001,opacity);
  // Retain faint native filaments and complete clear-sky weather transitions.
  opacity=max(opacity,.09*original*envelope);
  bodyShade=mix(1.0,clamp(bodyShade,.38,1.07),smoothstep(.001,.04,opacity));
  // Neutral modulation preserves the two native sun/moon lighting colours.
  // PS2 cloud texture convention is RGB=.5, alpha=[0,.5], not alpha=[0,1].
  color=vec4(vec3(.5*bodyShade),.5*clamp(opacity,0.0,1.0));
}
