#version 410 core
const int max_city_fires=64;
uniform int fire_count;
uniform vec4 fire_sources[max_city_fires];
uniform float fire_heights[max_city_fires];
uniform float fire_footprints[max_city_fires];
uniform float fire_seeds[max_city_fires];
uniform int fire_light_count;
uniform int fire_light_indices[8];
float fireFuelSurface(int id,vec2 xz) { return 0.0; }
float fireFloor(int id) { return 0.0; }

uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform float fire_time;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
vec3 fireProject(vec3 P) {
  vec4 h=-pc_camera*vec4(P*4096.0-cam_trans.xyz,1.0);
  h.y*=(512.0/416.0)*0.5;
  vec3 n=h.xyz/h.w;
  return vec3((fluid_viewport.xy+(n.xy*.5+.5)*fluid_viewport.zw)/vec2(textureSize(tex_T25,0)),n.z*.5+.5);
}
vec3 fireUnproject(vec2 uv,float depth) {
  vec4 h=vec4((uv*vec2(textureSize(tex_T25,0))-fluid_viewport.xy)/fluid_viewport.zw*2.0-1.0,depth*2.0-1.0,1.0);
  h.y/=(512.0/416.0)*0.5;
  vec4 w=inverse(-pc_camera)*h;
  return w.xyz/w.w/4096.0+cam_trans.xyz/4096.0;
}
float fireHash(vec3 p) {
  p=fract(p*.1031);p+=dot(p,p.yzx+33.33);
  return fract((p.x+p.y)*p.z);
}
float fireNoise(vec3 p) {
  vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
  return mix(mix(mix(fireHash(i),fireHash(i+vec3(1,0,0)),f.x),
                 mix(fireHash(i+vec3(0,1,0)),fireHash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(fireHash(i+vec3(0,0,1)),fireHash(i+vec3(1,0,1)),f.x),
                 mix(fireHash(i+vec3(0,1,1)),fireHash(i+vec3(1)),f.x),f.y),f.z);
}
float firePulse(int id) {
  float s=fire_seeds[id]*17.83;
  return .83+.12*sin(fire_time*3.13+s)+.06*sin(fire_time*7.71+s*1.7)+.04*sin(fire_time*11.17+s*.3);
}

in vec3 proxy_world;
flat in int fire_id;
out vec4 color;
void main() {
  vec3 base=fire_sources[fire_id].xyz;
  float radius=fire_sources[fire_id].w,H=fire_heights[fire_id];
  vec3 eye=cam_trans.xyz/4096.0,ray=normalize(proxy_world-eye);
  vec3 lo=base+vec3(-radius*2.0,fireFloor(fire_id),-radius*2.0);
  vec3 hi=base+vec3(radius*2.0,H*1.8,radius*2.0);
  vec3 invRay=1.0/(mix(vec3(-1),vec3(1),greaterThanEqual(ray,vec3(0)))*max(abs(ray),vec3(.00001)));
  vec3 a=(lo-eye)*invRay,b=(hi-eye)*invRay;
  vec3 near3=min(a,b),far3=max(a,b);
  float nearT=max(max(near3.x,near3.y),max(near3.z,0.0));
  float farT=min(min(far3.x,far3.y),far3.z);
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  float depth=texture(tex_T26,uv).r;
  vec3 scene=fireUnproject(uv,depth);
  if(depth>0.00001)farT=min(farT,dot(scene-eye,ray));
  if(farT<=nearT)discard;
  int samples=length(base-eye)>90.0 ? 24 : 48;
  float stepSize=(farT-nearT)/float(samples);
  float t=nearT+stepSize*.5;
  vec3 radiance=vec3(0);float transmission=1.0;
  float seed=fire_seeds[fire_id]*7.913;
  float clock=fire_time*(1.35+.13*sin(seed));
  for(int i=0;i<48;i++,t+=stepSize) {
    if(i>=samples)break;
    vec3 p=eye+ray*t-base;
    float h=p.y/H;
    vec3 q=vec3(p.x/radius,p.y/H,p.z/radius);
    vec2 bend=vec2(sin(q.y*5.3-clock*2.0+seed),sin(q.y*4.1-clock*1.73+seed*1.7));
    q.xz-=bend*clamp(q.y,0.0,1.5)*.22;
    vec3 flow=vec3(q.x*4.3,q.y*5.0-clock*3.1,q.z*4.3)+seed;
    float n=fireNoise(flow)*.64+fireNoise(flow*2.03+9.2)*.25+fireNoise(flow*4.07)*.11;
    // Three unequal tongues split and reunite instead of a smooth conical candle.
    float fuel=-1.0;
    for(int tongue=0;tongue<3;tongue++) {
      float a=float(tongue)*2.0944+seed;
      float tip=.77+.16*sin(clock*1.7+a)+.12*sin(clock*2.81+a*1.31);
      float y=h/max(tip,.4);
      float width=max(.035,.51*(1.0-clamp(y,0.0,1.0)*.87));
      vec2 centre=vec2(cos(a),sin(a))*(.30+.11*h);
      centre+=vec2(sin(h*9.0-clock*2.9+a),cos(h*7.1-clock*2.37+a))*.13*h;
      float tongueFuel=1.0-length(q.xz-centre)/width+(n-.48)*2.1;
      tongueFuel-=smoothstep(.60,1.0,y)*.9;
      fuel=max(fuel,tongueFuel);
    }
    float density=smoothstep(-.10,.30,fuel)*(1.0-smoothstep(.75,1.16,h));
    density*=.42+.58*smoothstep(.32,.65,n);
    // The fuel is an eight-sided bowl, not a plane at the vessel's highest rim.
    // A small overlap removes the air gap while the actual surface and scene
    // depth still prevent fire from emerging through the underside.
    float fuelSurface=fireFuelSurface(fire_id,p.xz);
    density*=smoothstep(fuelSurface-.025,fuelSurface+.025,p.y);
    // Keep the fire inside the fuel opening until it clears the vessel rim.
    float foot=1.0-smoothstep(fire_footprints[fire_id]*.82,fire_footprints[fire_id],length(p.xz));
    density*=mix(foot,1.0,smoothstep(.10,.65,p.y));
    float absorption=1.0-exp(-density*stepSize*3.8/radius);
    float hot=clamp(fuel*.90+(1.0-h)*.23,0.0,1.0);
    vec3 flame=mix(vec3(1.12,.10,.006),vec3(1.65,.68,.08),smoothstep(.02,.48,hot));
    flame=mix(flame,vec3(1.8,1.40,.69),smoothstep(.48,.87,hot));
    radiance+=transmission*absorption*flame*(.95+.12*firePulse(fire_id));
    transmission*=1.0-absorption;
    // Thin soot above the tip; it never becomes a large opaque plume.
    float smoke=smoothstep(.62,1.05,h)*(1.0-smoothstep(1.1,1.75,h));
    smoke*=exp(-dot(q.xz,q.xz)*2.2)*smoothstep(.35,.73,n)*.065;
    float sa=1.0-exp(-smoke*stepSize/radius);
    radiance+=transmission*sa*vec3(.15,.12,.095);
    transmission*=1.0-sa;
    if(transmission<.035)break;
  }
  float opacity=1.0-transmission;
  if(opacity<.003)discard;
  // Premultiplied output retains orange filaments against both dark and bright walls.
  float fade=1.0-smoothstep(200.0,300.0,length(base-eye));
  color=vec4(radiance,opacity)*fade;
}
