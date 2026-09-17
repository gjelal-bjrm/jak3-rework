// Per-pixel prototype materials. No animated low-resolution albedo is used for lava.
uniform int fluid_kind;
uniform float fluid_time;
uniform vec4 cam_trans;
uniform mat4 pc_camera;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T25; // resolved scene before this liquid bucket
uniform sampler2D tex_T26; // matching reversed-Z scene depth
uniform vec4 fluid_contacts[32]; // world position in metres, birth time
uniform float fluid_strength[32];

float fluidHash(vec2 p) {
  vec3 q = fract(vec3(p.xyx) * 0.1031);
  q += dot(q, q.yzx + 33.33);
  return fract((q.x + q.y) * q.z);
}
float fluidNoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f*f*(3.0-2.0*f);
  return mix(mix(fluidHash(i), fluidHash(i+vec2(1,0)), f.x),
             mix(fluidHash(i+vec2(0,1)), fluidHash(i+vec2(1,1)), f.x), f.y);
}
float fluidFbm(vec2 p) {
  float v = 0.0, a = 0.5;
  mat2 r = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i=0; i<4; i++) {
    v += a*fluidNoise(p);
    p = r*p*2.03+vec2(7.1, 3.7);
    a *= 0.5;
  }
  return v;
}

// Slow advection and two scales of curling folds, all attached to the surface.
// x: crust height, y: incandescent channels, z: finer ropy striations.
vec3 lavaField(vec2 p) {
  float t = fluid_time;
  p += vec2(t*0.18, -t*0.11);
  vec2 curl = vec2(fluidFbm(p*0.28+vec2(0,t*0.026)),
                   fluidFbm(p*0.28+vec2(11.7,-t*0.032)))-0.47;
  vec2 q = p + curl*3.6;
  float folds = fluidFbm(q*0.80);
  float streaks = sin(q.x*4.5 + q.y*2.1 + folds*13.0);
  float fissures = abs(sin(q.y*1.9 - q.x*0.85 + folds*11.5));
  float hot = pow(1.0-fissures, 3.0);
  float flow = smoothstep(0.42, 0.71, folds);
  float fine = fluidNoise(q*10.0);
  vec2 cell = floor(p*0.21);
  vec2 centre = (cell+vec2(0.2)+vec2(fluidHash(cell+7.0),fluidHash(cell+31.0))*0.6)/0.21;
  float phase = fract(t*0.16+fluidHash(cell+19.0));
  float radius = mix(0.08,0.90,smoothstep(0.0,0.72,phase));
  float active = smoothstep(0.02,0.22,phase)*(1.0-smoothstep(0.72,1.0,phase));
  active *= smoothstep(0.35,0.65,fluidHash(cell+29.0));
  float bubble = exp(-dot(p-centre,p-centre)/(radius*radius))*active;
  float height = folds*0.65 + streaks*0.024 + fine*0.015 - hot*0.075 + bubble*0.18;
  hot = max(hot,bubble*0.82);
  return vec3(height, max(hot, flow*0.72), streaks*0.5+0.5);
}

vec3 shadeModernLava(vec3 P) {
  vec3 V = normalize(cam_trans.xyz/4096.0-P);
  vec2 p = (P.xz-vec2(2320.0,-505.0))*0.72;
  vec2 parallax = clamp(V.xz/max(V.y,0.28), vec2(-2.5), vec2(2.5))*0.16;
  vec3 field = lavaField(p);
  p -= parallax*(field.x-0.30);
  field = lavaField(p);
  float e = 0.027;
  vec2 grad = vec2(lavaField(p+vec2(e,0)).x-field.x,
                   lavaField(p+vec2(0,e)).x-field.x)/e;
  vec3 N = normalize(vec3(-grad.x*0.64,1.0,-grad.y*0.64));
  float hot = field.y;
  // The warm red cooling skin stays part of the flow, never a floating black decal.
  vec3 cooling = mix(vec3(0.13,0.025,0.011),vec3(0.48,0.085,0.016),
                     smoothstep(0.20,0.55,field.x));
  vec3 incandescent = mix(vec3(1.10,0.105,0.008),vec3(1.40,0.78,0.15),
                          smoothstep(0.15,0.95,hot));
  float emission = smoothstep(0.02,0.68,hot);
  vec3 result = mix(cooling,incandescent,emission);
  result *= 0.88 + 0.12*field.z;
  vec3 L = normalize(vec3(0.5,0.81,0.3));
  vec3 H = normalize(L+V);
  float spec = pow(max(dot(N,H),0.0),32.0);
  float fresnel = 0.04 + 0.28*pow(1.0-max(dot(N,V),0.0),5.0);
  result += vec3(1.0,0.49,0.16)*spec*0.32;
  result += vec3(0.17,0.08,0.025)*fresnel;
  // Smoothly compress hot cores without turning all molten areas flat yellow.
  return result/(vec3(1.0)+max(result-0.85,vec3(0.0))*0.4);
}

vec3 fluidProject(vec3 p) {
  vec4 h = -pc_camera*vec4(p*4096.0-cam_trans.xyz,1.0);
  h.y *= (512.0/416.0)*0.5;
  vec3 ndc = h.xyz/h.w;
  vec2 pixel = fluid_viewport.xy+(ndc.xy*0.5+0.5)*fluid_viewport.zw;
  return vec3(pixel/vec2(textureSize(tex_T25,0)),ndc.z*0.5+0.5);
}
vec3 fluidUnproject(vec2 uv, float depth) {
  vec2 pixel = uv*vec2(textureSize(tex_T25,0));
  vec4 h = vec4((pixel-fluid_viewport.xy)/fluid_viewport.zw*2.0-1.0,
                depth*2.0-1.0,1.0);
  h.y /= (512.0/416.0)*0.5;
  vec4 world = inverse(-pc_camera)*h;
  return world.xyz/world.w/4096.0+cam_trans.xyz/4096.0;
}

vec2 waterContactSlope(vec3 P, out float wakeFoam) {
  vec2 slope = vec2(0.0);
  wakeFoam = 0.0;
  for (int i=0; i<32; i++) {
    float age = fluid_time-fluid_contacts[i].w;
    if (fluid_strength[i]<=0.0 || age<0.0 || age>4.0 ||
        abs(P.y-fluid_contacts[i].y)>0.45) continue;
    vec2 delta = P.xz-fluid_contacts[i].xz;
    float d = max(length(delta),0.001);
    float radius = 0.10+age*1.40;
    float width = 0.19+age*0.12;
    float q = d-radius;
    float envelope = exp(-q*q/(width*width))*exp(-age*1.15);
    float amplitude = fluid_strength[i];
    float derivative = amplitude*envelope*
      (-13.0*sin(q*13.0)-2.0*q/(width*width)*cos(q*13.0));
    slope += delta/d*derivative;
    wakeFoam += envelope*smoothstep(0.025,0.08,amplitude)*0.24;
  }
  for (int i=0; i<water_impact_count; i++) {
    if (abs(P.y-water_impacts[i].y)>0.35) continue;
    vec2 delta=P.xz-water_impacts[i].xz;
    float d=max(length(delta),0.001);
    if (d>3.0) continue;
    vec2 outward=delta/d;
    float phase=d*8.5-fluid_time*7.0+float(i);
    float envelope=exp(-d*1.45);
    slope += outward*cos(phase)*envelope*0.16;
    // Foam fragments travel away from the falling water; no stationary white disc.
    vec2 advected=outward*(d-fluid_time*0.65);
    float bubbles=fluidNoise(advected*11.0+vec2(float(i)*13.7));
    bubbles=mix(bubbles,fluidNoise(advected*21.0+fluid_time*vec2(0.35,-0.23)),0.28);
    float patches=smoothstep(0.48,0.79,bubbles);
    float movingRing=pow(max(sin(phase+fluidNoise(delta*4.0)*1.2),0.0),5.0);
    wakeFoam += (patches*0.24+patches*movingRing*0.18)*envelope;
  }
  return slope;
}

vec3 waterNormal(vec2 p, vec3 P, out float wakeFoam) {
  float t = fluid_time;
  vec2 slope = vec2(0.0);
  slope += vec2(1.0,0.30)*cos(dot(p,vec2(1.0,0.30))*3.4-t*1.2)*0.090;
  slope += vec2(-0.4,1.0)*cos(dot(p,vec2(-0.4,1.0))*5.8+t*1.5)*0.074;
  slope += vec2(0.71,0.71)*cos(dot(p,vec2(0.71))*11.2-t*2.2)*0.036;
  slope += vec2(0.93,-0.36)*cos(dot(p,vec2(0.93,-0.36))*19.0+t*2.8)*0.023;
  slope += waterContactSlope(P,wakeFoam);
  float bankDistance=shoreDistance(P);
  if(bankDistance<1.2) {
    float irregular=fluidNoise(P.xz*2.1+fluid_time*vec2(0.19,-0.12))-0.5;
    irregular+=0.4*(fluidNoise(P.xz*4.7-fluid_time*vec2(0.12,0.15))-0.5);
    slope+=shoreDirection(P)*irregular*0.065*exp(-bankDistance*3.0);
  }
  return normalize(vec3(-slope.x,1.0,-slope.y));
}

vec4 waterReflection(vec3 P, vec3 V, vec3 N) {
  vec3 R = reflect(-V,N);
  vec3 env = mix(vec3(0.115,0.15,0.16),vec3(0.32,0.36,0.34),
                 smoothstep(0.0,0.8,R.y));
  float distanceAlong = 0.25;
  for (int i=0; i<28; i++) {
    distanceAlong += 0.22+float(i)*0.045;
    vec3 ray = P+N*0.055+R*distanceAlong;
    vec3 screen = fluidProject(ray);
    if (any(lessThan(screen.xy,vec2(0.005))) ||
        any(greaterThan(screen.xy,vec2(0.995))) || screen.z<0.0) break;
    float z = texture(tex_T26,screen.xy).r;
    if (z>screen.z && z>0.00001) {
      vec3 hit = fluidUnproject(screen.xy,z);
      float error = length(hit-ray);
      if (error < 0.6+distanceAlong*0.06 && hit.y>P.y-0.08) {
        vec2 edge = min(screen.xy,1.0-screen.xy);
        float confidence = smoothstep(0.005,0.08,min(edge.x,edge.y));
        confidence *= 1.0-smoothstep(0.4,1.2,error);
        return vec4(mix(env,texture(tex_T25,screen.xy).rgb,confidence),confidence);
      }
    }
  }
  return vec4(env,0.0);
}

// PALACE_FIRE_REFLECTION_HELPER
vec3 shadeModernWater(vec3 P, vec3 geometricNormal, vec4 legacyTexture) {
  vec2 screen = gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec3 originalScene = texture(tex_T25,screen).rgb;
  vec3 V = normalize(cam_trans.xyz/4096.0-P);
  float horizontal = smoothstep(0.45,0.85,abs(geometricNormal.y));
  vec2 local = P.xz-vec2(2000.0,-460.0);
  float wakeFoam;
  vec3 N = waterNormal(local,P,wakeFoam);
  if (horizontal<0.5) {
    // The palace's central jet cards overlap the new volume jets. Retire those
    // cards while retaining the small cascades around the stepping stones.
    if(P.x>1987.0 && P.x<2011.0 && P.z> -456.0 && P.z< -438.8) discard;
    // An elongated flowing film, with small bright streaks instead of cloudy noise.
    vec2 q=vec2((P.x+P.z)*7.0,P.y*0.50+fluid_time*2.8);
    float flow=fluidNoise(q)+0.35*fluidNoise(q*vec2(2.8,1.9));
    vec3 tangent = normalize(vec3(geometricNormal.z,0.0,-geometricNormal.x)+vec3(0.001));
    N = normalize(geometricNormal+tangent*(flow-0.55)*0.40);
    if (dot(N,V)<0.0) N = -N;
    vec2 offset=(fluidProject(P+tangent*(flow-0.5)*0.09).xy-fluidProject(P).xy);
    vec2 maxOffset=vec2(3.0)/vec2(textureSize(tex_T25,0));
    offset=clamp(offset,-maxOffset,maxOffset);
    vec2 uv=clamp(screen+offset,vec2(0.001),vec2(0.999));
    if(texture(tex_T26,uv).r>gl_FragCoord.z) uv=screen;
    vec3 transmitted=texture(tex_T25,uv).rgb;
    float streak=smoothstep(0.67,1.02,flow);
    float facing=0.10+0.35*pow(1.0-max(dot(N,V),0.0),3.0);
    vec3 film=mix(transmitted,vec3(0.48,0.56,0.54),facing+streak*0.28);
    film+=vec3(0.20,0.23,0.22)*pow(max(dot(N,normalize(V+vec3(-0.3,0.8,-0.2))),0.0),48.0);
    float coverage=clamp(legacyTexture.a*legacyTexture.a*2.0,0.0,0.8)
      *(0.55+streak*0.45);
    coverage *= smoothstep(0.5,2.2,length(cam_trans.xyz/4096.0-P));
    return mix(originalScene,film,coverage);
  }
  // The basin is visible from both sides. Preserve the accepted upper face;
  // only its underside needs the normal oriented toward the submerged camera.
  bool belowSurface = cam_trans.y/4096.0 < P.y;
  if (belowSurface && dot(N,V)<0.0) N = -N;
  vec3 projectedOffset = fluidProject(P+vec3(N.x,0.0,N.z)*0.16);
  vec2 refractUV = clamp(screen+(projectedOffset.xy-fluidProject(P).xy),vec2(0.001),vec2(0.999));
  float z = texture(tex_T26,refractUV).r;
  // Do not pull foreground banks or stepping stones into the water.
  if (z>gl_FragCoord.z) {
    refractUV=screen;
    z=texture(tex_T26,screen).r;
  }
  float thickness = min(length(fluidUnproject(refractUV,z)-P),3.0);
  // From below, the submerged segment ends at the surface. The remaining ray
  // goes through air; a distant wall must not add metres of water absorption.
  if (belowSurface) thickness = min(length(cam_trans.xyz/4096.0-P),3.0);
  vec3 transmission = exp(-vec3(0.21,0.072,0.045)*thickness);
  vec3 below = texture(tex_T25,refractUV).rgb*transmission;
  below += vec3(0.018,0.078,0.083)*(1.0-transmission);
  // Caustics follow the bed through refraction and disappear on deep water.
  vec3 bed = fluidUnproject(refractUV,z);
  float caustic = pow(max(0.0,1.0-abs(sin(bed.x*5.1+fluid_time*0.8+
                      sin(bed.z*4.2-fluid_time*0.6)*1.9))),8.0);
  below *= 1.0+caustic*0.22*exp(-thickness*0.85)*horizontal;
  float fresnel = 0.035+0.72*pow(1.0-max(dot(N,V),0.0),5.0);
  vec3 reflected = waterReflection(P,V,N).rgb;
  vec3 result = mix(below,reflected,fresnel);
  result += palaceFireReflection(P,N,V);
  vec3 L = normalize(vec3(-0.30,0.88,-0.37));
  float glint = pow(max(dot(N,normalize(V+L)),0.0),160.0);
  result += vec3(0.95,0.85,0.61)*glint*0.55;
  // Foam belongs to moving contacts and falling-water impacts, not a bank outline.
  float foam=wakeFoam*smoothstep(0.25,0.65,fluidNoise(local*19.0+fluid_time*vec2(1.9,0.7)));
  result = mix(result,vec3(0.68,0.76,0.73),clamp(foam,0.0,0.48));
  if (horizontal<0.5) {
    float strands = pow(fluidNoise(vec2((P.x+P.z)*14.0,P.y*1.4+fluid_time*4.2)),3.0);
    float film = clamp(legacyTexture.a*0.65+strands*0.42,0.05,0.65);
    result = mix(originalScene, result+vec3(0.34,0.41,0.42)*strands,film);
  }
  return result;
}
