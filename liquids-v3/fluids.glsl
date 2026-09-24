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

// Couverture floue de la texture d'origine (posee par tfrag3 avant shadeModernWater ; -1 ailleurs).
float fluidCoverHint = -1.0;
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

// Lac de lave de l'arene : plaques de croute basaltique sombre separees par des fissures
// incandescentes, chenaux ou la croute a fondu, derive lente. Tout est attache a la surface.
// Cellules de plaques (Voronoi) : x = distance au bord (0 = fissure), y = variation de la plaque.
vec2 lavaCells(vec2 q, float scale) {
  vec2 cell = floor(q*scale), f = fract(q*scale);
  float d1 = 8.0, d2 = 8.0; vec2 plate = cell;
  for (int j=-1; j<=1; j++) for (int i=-1; i<=1; i++) {
    vec2 g = vec2(float(i),float(j));
    vec2 o = vec2(fluidHash(cell+g+scale), fluidHash(cell+g+17.3+scale));
    vec2 r = g + o - f; float d = dot(r,r);
    if (d < d1) { d2 = d1; d1 = d; plate = cell+g; } else if (d < d2) d2 = d;
  }
  return vec2(sqrt(d2)-sqrt(d1), fluidHash(plate+3.1+scale));
}
// x : relief, y : incandescence 0..1, z : distance au bord de plaque (0 = fissure), w : variation de plaque.
vec4 lavaField(vec2 p) {
  float t = fluid_time;
  p += vec2(t*0.045, -t*0.028);                                  // derive lente de la croute
  vec2 warp = vec2(fluidFbm(p*0.13+vec2(0.0,t*0.010)), fluidFbm(p*0.13+vec2(9.3,-t*0.012)))-0.5;
  vec2 q = p + warp*4.2;                                          // plaques irregulieres, pas un pavage
  vec2 large = lavaCells(q, 0.27);                                // grandes plaques (~3,7 m), fissures principales
  vec2 small = lavaCells(q + vec2(3.7,-1.9), 0.62);               // fractures secondaires (~1,6 m)
  float heat = fluidFbm(q*0.35 + vec2(t*0.02, 0.0));              // zones plus ou moins chaudes
  float cooled = smoothstep(0.32, 0.62, fluidFbm(q*0.9 + vec2(5.1, 2.3)));   // part du reseau fin refroidie
  float crackA = smoothstep(0.20, 0.03, large.x);
  float crackB = smoothstep(0.11, 0.015, small.x)*cooled;
  float crack = max(crackA, crackB*0.75);
  float molten = smoothstep(0.58, 0.74, heat);                    // chenaux en fusion
  float pulse = 0.72 + 0.28*sin(t*0.7 + large.y*6.2832);          // respiration lente des fissures
  float glow = max(crack*pulse*smoothstep(0.12, 0.55, heat+0.15), molten);
  float fine = fluidNoise(q*9.0);
  float height = (1.0-crackA)*0.5 - crackB*0.15 + fine*0.05 - molten*0.25;
  return vec4(height, glow, min(large.x, small.x*1.5), large.y);
}

vec3 shadeModernLava(vec3 P) {
  vec3 V = normalize(cam_trans.xyz/4096.0-P);
  vec2 p = P.xz-vec2(2320.0,-505.0);
  vec4 field = lavaField(p);
  float e = 0.05;
  vec2 grad = vec2(lavaField(p+vec2(e,0)).x-field.x, lavaField(p+vec2(0,e)).x-field.x)/e;
  vec3 N = normalize(vec3(-grad.x*0.35, 1.0, -grad.y*0.35));
  float glow = field.y;
  // Croute : basalte sombre brun-gris, grain fin, variation par plaque.
  vec3 crust = mix(vec3(0.050,0.036,0.030), vec3(0.105,0.078,0.062), field.w*0.6 + fluidNoise(p*3.0)*0.4);
  // Incandescence : rouge sombre -> orange -> jaune-blanc au coeur des chenaux.
  vec3 ember = mix(vec3(0.55,0.06,0.010), vec3(1.25,0.38,0.05), smoothstep(0.10,0.60,glow));
  ember = mix(ember, vec3(1.55,1.05,0.45), smoothstep(0.75,1.0,glow));
  vec3 result = mix(crust, ember, smoothstep(0.03,0.5,glow));
  // Croute chauffee par conduction au bord des fissures : rougeoiement diffus.
  float halo = smoothstep(0.55,0.05,field.z)*(1.0-smoothstep(0.03,0.5,glow));
  result += vec3(0.26,0.045,0.006)*halo*0.7;
  // Reflet terne du ciel sur la croute rugueuse, plus vif sur la lave en fusion.
  vec3 L = normalize(vec3(0.5,0.81,0.3));
  vec3 H = normalize(L+V);
  float spec = pow(max(dot(N,H),0.0), mix(8.0,40.0,glow));
  result += mix(vec3(0.05,0.05,0.05), vec3(1.0,0.5,0.18), glow)*spec*mix(0.08,0.30,glow);
  // Compression douce des coeurs chauds (le bloom ecran fait le reste).
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
  // Deux ondulations longues et lentes, puis des rides organiques (gradient de bruit advecte)
  // a la place des trains sinusoidaux reguliers.
  slope += vec2(1.0,0.30)*cos(dot(p,vec2(1.0,0.30))*3.4-t*1.2)*0.070;
  slope += vec2(-0.4,1.0)*cos(dot(p,vec2(-0.4,1.0))*5.8+t*1.5)*0.055;
  {
    float e = 0.04;
    vec2 q = p*1.9 + vec2(t*0.21,-t*0.13);
    float c = fluidNoise(q), gx = fluidNoise(q+vec2(e,0.0)), gz = fluidNoise(q+vec2(0.0,e));
    slope += vec2(gx-c, gz-c)/e*0.060;
    q = p*4.7 - vec2(t*0.17, t*0.29);
    c = fluidNoise(q); gx = fluidNoise(q+vec2(e,0.0)); gz = fluidNoise(q+vec2(0.0,e));
    slope += vec2(gx-c, gz-c)/e*0.022;
  }
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
// PALACE_IMPACT_BEGIN (genere par models-v2/palace/build_falls.py)
// Pieds des chutes : eau blanche qui bouillonne, anneaux de vagues qui s'eloignent, ecume qui derive vers
// l'exterieur. Renvoie la pente de la surface (xy) et l'ecume (z).
vec3 palaceImpact(vec3 P) {
  const vec4 impacts[14]=vec4[14](vec4(1990.605,241.491,-439.565,1.10),vec4(2007.471,241.491,-442.773,1.10),vec4(2005.301,241.491,-453.336,1.10),vec4(1989.295,241.491,-450.188,1.10),vec4(2044.023,241.502,-426.044,0.45),vec4(2035.390,241.501,-431.432,0.45),vec4(2019.907,241.498,-437.438,0.45),vec4(2006.281,241.499,-437.681,0.45),vec4(1989.839,241.495,-437.778,0.45),vec4(1972.779,241.497,-437.860,0.45),vec4(2026.199,240.630,-485.042,0.45),vec4(2046.131,240.632,-486.036,0.45),vec4(2029.992,240.629,-484.546,0.45),vec4(1997.982,240.650,-484.783,0.45));
  vec2 slope=vec2(0.0);float foam=0.0;
  for(int i=0;i<14;i++) {
    vec4 im=impacts[i];
    if(abs(P.y-im.y)>0.8)continue;
    vec2 dp=P.xz-im.xz;float d=length(dp);float R=im.w;
    if(d>R*5.0)continue;
    vec2 dir=dp/max(d,1e-3);
    float t=fluid_time+float(i)*3.7;
    // coeur : eau aeree qui bouillonne
    float core=exp(-d*d/(R*R)*1.4);
    float churn=fluidNoise(dp*10.0/R+vec2(t*2.3,-t*1.7))*0.50+fluidNoise(dp*21.0/R-vec2(t*3.1,t*2.4))*0.32
               +fluidNoise(dp*43.0/R+vec2(t*4.0,t*3.3))*0.18;
    float bubbles=smoothstep(0.30,0.70,churn);
    foam+=core*(0.35+0.65*bubbles);
    // couronne d'ecume qui s'ouvre autour du point d'impact
    float crown=exp(-pow((d-R*0.9)/(R*0.35),2.0))*smoothstep(0.45,0.7,churn);
    foam+=crown*0.55;
    // ecume qui derive vers l'exterieur par plaques
    float ang=atan(dp.y,dp.x);
    float drift=fluidNoise(vec2(ang*2.2+float(i),d*2.4/R-t*1.1))*0.65+fluidNoise(vec2(ang*5.0,d*5.0/R-t*1.6)+4.0)*0.35;
    foam+=smoothstep(0.62,0.92,drift)*exp(-d/(R*1.3))*(1.0-core)*0.35;
    // anneaux de vagues qui s'eloignent et s'amortissent
    float k=6.5/R,w=7.0;
    float amp=0.10*exp(-d/(R*2.2))*smoothstep(0.0,R*0.5,d);
    slope+=dir*amp*cos(d*k-t*w);
    // surface agitee au coeur
    vec2 e=vec2(0.05,0.0);
    float c0=fluidNoise(dp*4.0/R+t*2.0);
    slope+=vec2(fluidNoise((dp+e.xy)*4.0/R+t*2.0)-c0,fluidNoise((dp+e.yx)*4.0/R+t*2.0)-c0)/0.05*0.02*core;
  }
  return vec3(slope,clamp(foam,0.0,1.0));
}
// PALACE_IMPACT_END

vec3 shadeModernWater(vec3 P, vec3 geometricNormal, vec4 legacyTexture) {
  vec2 screen = gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  vec3 originalScene = texture(tex_T25,screen).rgb;
  vec3 V = normalize(cam_trans.xyz/4096.0-P);
  float horizontal = smoothstep(0.45,0.85,abs(geometricNormal.y));
  vec2 local = P.xz-vec2(2000.0,-460.0);
  float wakeFoam;
  vec3 N = waterNormal(local,P,wakeFoam);
  if (horizontal<0.5) {
    // The palace's central jet cards overlap the new volume jets and mist. Retire those
    // cards while retaining the small cascades around the stepping stones.
    // Cartes centrales autour des quatre chutes : remplacees par le voile de brume en volume (fountain_mist).
    if(P.x>1987.0 && P.x<2011.0 && P.z> -456.0 && P.z< -438.8) discard;
    // Petite cascade (v3) : vraie nappe d'eau qui deborde de la pierre. La texture d'origine ne sert plus
    // qu'a savoir OU il y a de l'eau (couverture large, sans ses fines lignes) ; l'eau elle-meme est
    // dessinee : lisse et vitreuse en haut, filets qui accelerent et blanchissent vers le bas, on voit la
    // pierre a travers, deformee.
    float across=(P.x+P.z)*0.7071;
    float fall=P.y+fluid_time*3.2;
    float strands=fluidNoise(vec2(across*6.0,fall*1.1))*0.6+fluidNoise(vec2(across*13.0,fall*2.2)+7.3)*0.4;
    vec3 tangent = normalize(vec3(geometricNormal.z,0.0,-geometricNormal.x)+vec3(0.001));
    N = normalize(geometricNormal+tangent*(strands-0.5)*0.5);
    if (dot(N,V)<0.0) N = -N;
    vec2 offset=(fluidProject(P+tangent*(strands-0.5)*0.10).xy-fluidProject(P).xy);
    vec2 maxOffset=vec2(4.0)/vec2(textureSize(tex_T25,0));
    offset=clamp(offset,-maxOffset,maxOffset);
    vec2 uv=clamp(screen+offset,vec2(0.001),vec2(0.999));
    if(texture(tex_T26,uv).r>gl_FragCoord.z) uv=screen;
    vec3 transmitted=texture(tex_T25,uv).rgb;
    // couverture : la moindre trace d'eau de la texture d'origine suffit (plus de lignes separees)
    float cover=fluidCoverHint>=0.0 ? fluidCoverHint : legacyTexture.a;
    float mask=smoothstep(0.03,0.22,cover)*0.85+0.15*smoothstep(0.0,0.1,legacyTexture.a);
    // aeration : eau vive, blanche par endroits, avec des passages plus clairs
    float aer=0.12+0.88*smoothstep(0.42,0.86,strands);
    float fres=0.05+0.95*pow(1.0-max(dot(N,V),0.0),4.0);
    vec3 light=vec3(0.97,0.91,0.82);
    vec3 glass=mix(transmitted*vec3(0.84,0.93,0.95),vec3(0.46,0.52,0.52)*light,0.18+0.40*fres);
    vec3 film=mix(glass,vec3(0.93,0.94,0.92)*light,aer*0.85);
    film+=palaceFireReflection(P,N,V)*0.8;
    film+=vec3(1.0,0.84,0.60)*pow(max(dot(N,normalize(V+vec3(-0.3,0.8,-0.2))),0.0),56.0)*0.35;
    float nearFade=smoothstep(0.5,2.2,length(cam_trans.xyz/4096.0-P));
    return mix(originalScene,film,nearFade*mask);
  }
  // The basin is visible from both sides. Preserve the accepted upper face;
  // only its underside needs the normal oriented toward the submerged camera.
  bool belowSurface = cam_trans.y/4096.0 < P.y;
  // pieds des chutes : bouillonnement, anneaux de vagues, ecume
  vec3 impact = palaceImpact(P);
  N = normalize(N+vec3(-impact.x,0.0,-impact.y));
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
  // Eau de bassin laiteuse, turquoise gris comme l'original : absorption et diffusion bien visibles
  // (la version limpide faisait croire qu'il n'y avait pas d'eau entre les pierres).
  vec3 transmission = exp(-vec3(0.55,0.30,0.26)*thickness);
  float murk = 1.0-exp(-thickness*1.4);
  vec3 below = texture(tex_T25,refractUV).rgb*transmission*(1.0-0.45*murk);
  below = mix(below,vec3(0.24,0.33,0.34),clamp(murk*0.55+0.12,0.0,0.8));
  // Caustics follow the bed through refraction and disappear on deep water.
  vec3 bed = fluidUnproject(refractUV,z);
  float caustic = pow(max(0.0,1.0-abs(sin(bed.x*5.1+fluid_time*0.8+
                      sin(bed.z*4.2-fluid_time*0.6)*1.9))),8.0);
  below *= 1.0+caustic*0.22*exp(-thickness*0.85)*horizontal;
  float fresnel = 0.035+0.72*pow(1.0-max(dot(N,V),0.0),5.0);
  vec3 reflected = waterReflection(P,V,N).rgb;
  vec3 result = mix(below,reflected,fresnel);
  // Reflets des feux sur une normale lissee : des lueurs souples, pas des paillettes orange.
  result += palaceFireReflection(P,normalize(mix(vec3(0.0,1.0,0.0),N,0.45)),V)*1.35;
  vec3 L = normalize(vec3(-0.30,0.88,-0.37));
  float glint = pow(max(dot(N,normalize(V+L)),0.0),160.0);
  result += vec3(0.95,0.85,0.61)*glint*0.55;
  // Foam belongs to moving contacts and falling-water impacts, not a bank outline.
  float foam=wakeFoam*smoothstep(0.25,0.65,fluidNoise(local*19.0+fluid_time*vec2(1.9,0.7)));
  result = mix(result,vec3(0.68,0.76,0.73),clamp(foam,0.0,0.48));
  // ecume des chutes : blanche, eclairee par les braseros, avec un peu de relief
  float impactFoam = impact.z*(0.75+0.25*fluidNoise(P.xz*9.0+fluid_time*vec2(1.3,-0.8)));
  result = mix(result,vec3(0.86,0.87,0.83)*vec3(1.0,0.93,0.84),clamp(impactFoam,0.0,0.85));
  if (horizontal<0.5) {
    float strands = pow(fluidNoise(vec2((P.x+P.z)*14.0,P.y*1.4+fluid_time*4.2)),3.0);
    float film = clamp(legacyTexture.a*0.65+strands*0.42,0.05,0.65);
    result = mix(originalScene, result+vec3(0.34,0.41,0.42)*strands,film);
  }
  return result;
}
