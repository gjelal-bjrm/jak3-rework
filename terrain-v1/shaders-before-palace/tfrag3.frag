#version 410 core

out vec4 color;

in vec4 fragment_color;
in vec3 tex_coord;
in float fogginess;
in vec3 arena_world;
uniform sampler2D tex_T0;

uniform float alpha_min;
uniform float alpha_max;
uniform vec4 fog_color;

uniform int gfx_hack_no_tex;


// Spargus arena prototype, morning lighting. World positions are GOAL units / 4096.
// Uses geometric derivatives and existing baked shading as an occlusion proxy.
// No shadow map, screen-space AO, ray tracing, or extra texture fetches.
float arenaWeight(vec3 p) {
  vec2 centre = vec2(9520000.0, -1830000.0) / 4096.0;
  float radial = 1.0 - smoothstep(70.0, 100.0, length(p.xz - centre));
  float vertical = smoothstep(-18.0, -4.0, p.y) * (1.0 - smoothstep(100.0, 125.0, p.y));
  return radial * vertical;
}

vec3 arenaRelight(vec3 baked, vec3 p) {
  // Derivatives must be evaluated before any discard or divergent branch.
  vec3 rawNormal = cross(dFdx(p), dFdy(p));
  vec3 n = rawNormal * inversesqrt(max(dot(rawNormal, rawNormal), 1e-12));
  float weight = arenaWeight(p);
  vec3 sunDirection = normalize(vec3(0.50, 0.814, 0.296));
  float sun = max(dot(n, sunDirection), 0.0);
  float sky = clamp(n.y * 0.5 + 0.5, 0.0, 1.0);
  vec3 skylight = mix(vec3(0.39, 0.43, 0.49), vec3(0.57, 0.66, 0.79), sky);
  vec3 sunlight = vec3(0.88, 0.74, 0.53) * sun;
  vec3 bounce = vec3(0.15, 0.093, 0.045) * (1.0 - sky);
  float bakedLuma = dot(max(baked, vec3(0.0)), vec3(0.2126, 0.7152, 0.0722));
  float visibility = mix(0.32, 1.0, smoothstep(0.08, 0.90, bakedLuma));
  vec3 rebuilt = (skylight + sunlight + bounce) * visibility;
  // Retain part of the original artwork's shading to avoid erasing baked shadows.
  vec3 heatBounce = vec3(0.70,0.17,0.022)
      * exp(-max(p.y-10.0,0.0)/7.0) * weight * visibility
      * (0.45+0.55*max(-n.y,0.0));
  return mix(baked, rebuilt, 0.62 * weight)+heatBounce;
}

// Distances in metres to solid bank cross sections, at each real basin height.
uniform sampler2DArray shore_field;
const float shore_levels[4]=float[4](240.629257,241.491302,242.372253,243.497742);
int shoreLayer(float y) {
  int layer=0;
  for(int i=1;i<4;i++)if(abs(y-shore_levels[i])<abs(y-shore_levels[layer]))layer=i;
  return layer;
}
vec3 shoreUV(vec3 P) { return vec3((P.xz-vec2(1944.0,-524.0))/128.0,float(shoreLayer(P.y))); }
float shoreDistance(vec3 P) {
  vec3 uv=shoreUV(P);
  if(any(lessThan(uv.xy,vec2(0)))||any(greaterThan(uv.xy,vec2(1))) ||
     abs(P.y-shore_levels[int(uv.z)])>0.5)return 1.5;
  return texture(shore_field,uv).r;
}
vec2 shoreDirection(vec3 P) {
  vec3 uv=shoreUV(P);float e=1.0/1024.0;
  vec2 gradient=vec2(texture(shore_field,uv+vec3(e,0,0)).r-texture(shore_field,uv-vec3(e,0,0)).r,
                     texture(shore_field,uv+vec3(0,e,0)).r-texture(shore_field,uv-vec3(0,e,0)).r);
  return gradient/max(length(gradient),0.001);
}
const int water_impact_count=14;
const vec3 water_impacts[14]=vec3[14](vec3(2007.471069,241.491302,-442.773376),vec3(2005.300903,241.491302,-453.336182),vec3(1990.604980,241.491302,-439.565002),vec3(1989.294556,241.491302,-450.188232),vec3(2044.023071,241.502426,-426.044189),vec3(2035.389526,241.500977,-431.432495),vec3(2019.906860,241.498322,-437.437775),vec3(2006.281006,241.498520,-437.680817),vec3(1989.839478,241.494888,-437.778015),vec3(1972.778809,241.496780,-437.859619),vec3(2026.199219,240.629852,-485.041504),vec3(2046.130737,240.631531,-486.035919),vec3(2029.992188,240.628723,-484.546326),vec3(1997.981567,240.649796,-484.783356));
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

const int fire_count=24;
const vec4 fire_sources[24]=vec4[24](vec4(2068.347656,245.195191,-439.520416,0.850),vec4(2044.332520,260.605389,-427.963776,1.750),vec4(2012.435425,256.637372,-416.933777,1.200),vec4(2017.756592,247.652466,-427.581390,0.850),vec4(2021.635132,247.511597,-414.157471,0.850),vec4(2030.881958,251.703870,-423.380585,1.200),vec4(2047.177368,251.070966,-440.113129,1.200),vec4(1996.695557,248.875825,-410.387360,0.850),vec4(2006.619873,248.875825,-410.387360,0.850),vec4(1980.074219,251.162625,-428.589844,1.200),vec4(1984.552734,247.492097,-427.279144,0.850),vec4(1982.396606,247.511597,-414.157471,0.850),vec4(1969.389648,260.605389,-433.689301,1.750),vec4(1991.966309,254.317990,-416.675903,1.200),vec4(1967.893677,250.980099,-446.651794,1.200),vec4(2027.325928,250.861111,-501.077118,1.200),vec4(2035.419434,247.474076,-519.398621,0.850),vec4(2041.876587,260.605389,-494.716095,1.750),vec4(2048.688232,251.067761,-479.644440,1.200),vec4(1998.561401,251.097028,-503.746338,1.200),vec4(2013.424316,260.605389,-507.685303,1.750),vec4(1949.805908,245.182191,-485.345551,0.850),vec4(1971.172852,251.053128,-483.306976,1.200),vec4(1981.258423,260.605389,-497.629883,1.750));
const float fire_heights[24]=float[24](3.500,7.000,5.000,3.500,3.500,5.000,5.000,3.500,3.500,5.000,3.500,3.500,7.000,5.000,5.000,5.000,3.500,7.000,5.000,5.000,7.000,3.500,5.000,7.000);
const float fire_footprints[24]=float[24](0.896473,1.500000,1.000000,0.906730,0.906680,1.000000,1.000000,0.896406,0.896406,1.000000,0.896423,0.906680,1.500000,1.000000,1.000000,1.000000,0.896406,1.500000,1.000000,1.000000,1.500000,0.913050,1.000000,1.500000);

// Approximate finite fire-source highlights, bent by the actual water normals.
vec3 palaceFireReflection(vec3 P,vec3 N,vec3 V) {
  vec3 reflected=reflect(-V,N),sum=vec3(0);
  for(int i=0;i<fire_count;i++) {
    vec3 delta=fire_sources[i].xyz+vec3(0,fire_heights[i]*.30,0)-P;
    float d=length(delta);
    if(d>38.0)continue;
    float angularRadius=clamp(fire_sources[i].w/max(d,1.0),.012,.25);
    float exponent=clamp(1.0/(angularRadius*angularRadius),48.0,1800.0);
    float glint=pow(max(dot(reflected,delta/max(d,.01)),0.0),exponent);
    float seed=float(i)*17.83;
    float pulse=.83+.12*sin(fluid_time*3.13+seed)+.06*sin(fluid_time*7.71+seed*1.7);
    sum+=vec3(1.0,.32,.045)*glint*pulse*(1.0-smoothstep(20.0,38.0,d));
  }
  return sum*.18;
}

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
  vec3 projectedOffset = fluidProject(P+vec3(N.x,0.0,N.z)*0.16);
  vec2 refractUV = clamp(screen+(projectedOffset.xy-fluidProject(P).xy),vec2(0.001),vec2(0.999));
  float z = texture(tex_T26,refractUV).r;
  // Do not pull foreground banks or stepping stones into the water.
  if (z>gl_FragCoord.z) {
    refractUV=screen;
    z=texture(tex_T26,screen).r;
  }
  float thickness = min(length(fluidUnproject(refractUV,z)-P),3.0);
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

void main() {
  vec3 arena_light = arenaRelight(fragment_color.rgb, arena_world);
  vec3 surface_normal = normalize(cross(dFdx(arena_world),dFdy(arena_world)));
  if (gfx_hack_no_tex == 0) {
    //vec4 T0 = texture(tex_T0, tex_coord);
    vec4 T0 = texture(tex_T0, tex_coord.xy);
    if (fluid_kind == 1) {
      color = vec4(shadeModernLava(arena_world),1.0);
    } else if (fluid_kind == 2) {
      color = vec4(shadeModernWater(arena_world,surface_normal,
        T0*vec4(1.0,1.0,1.0,fragment_color.a*2.0)),1.0);
    } else {
      color = vec4(arena_light, fragment_color.a) * T0;
    }
  } else {
    color = fragment_color/2;
  }

  if (color.a < alpha_min || color.a > alpha_max) {
    discard;
  }

  if (fluid_kind != 2)
    color.rgb = mix(color.rgb, fog_color.rgb, clamp(fogginess * fog_color.a, 0, 1));
}
