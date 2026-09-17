#version 410 core
in vec3 breaker_world;
in vec2 breaker_uv;
flat in vec4 breaker_episode;
flat in vec4 breaker_tint;
uniform vec3 ocean_eye;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
out vec4 color;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){
  vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);
}
void main(){
  if(breaker_world.y<8.75)discard;
  float u=breaker_uv.x,v=breaker_uv.y,age=breaker_episode.x,seed=breaker_episode.z;
  int kind=int(breaker_episode.y+.1);
  bool impact=kind==2;
  float edge=smoothstep(0.,.09,u)*(1.-smoothstep(.91,1.,u));
  float n=noise(vec2(u*16.+seed,v*8.-age*1.8));
  float detail=noise(vec2(u*43.-seed,v*26.-age*3.5));
  float top=.79+.15*noise(vec2(u*9.+seed,age*.55));
  float film=impact ? smoothstep(.06,.19,v)*(1.-smoothstep(top-.035,top+.035,v))
                    : exp(-pow((v-.57)/.29,2.));
  // Disconnected filaments and a narrow broken lip, without a filled white quad.
  float strands=smoothstep(.62,.88,n*.7+detail*.3);
  float lip=exp(-pow((v-(impact?top:.63))/(impact?.074:.048),2.))*smoothstep(.18,.55,n);
  float foam=clamp(strands*(impact?.78:.42)+lip*.95,0.,1.);
  if(kind==3) {
    film=smoothstep(.40,.75,n)*smoothstep(.25,.7,detail)*(1.-smoothstep(.20,.58,length(breaker_uv-.5)));
    foam=.7;
  }
  vec3 normal=normalize(cross(dFdx(breaker_world),dFdy(breaker_world)));
  vec3 view=normalize(ocean_eye-breaker_world);
  if(dot(normal,view)<0.)normal=-normal;
  float fresnel=pow(1.-abs(dot(normal,view)),4.);
  vec2 screen=(gl_FragCoord.xy-fluid_viewport.xy)/fluid_viewport.zw;
  vec2 bend=normal.xz*(.0018+.001*noise(vec2(u*11.,v*13.-age)));
  vec3 refracted=texture(tex_T25,clamp(screen+bend,vec2(.001),vec2(.999))).rgb;
  vec3 water=mix(refracted,vec3(.25,.34,.30),.22+.20*fresnel);
  float aeration=0.;
  float openings=1.;
  if(impact) {
    // Entrained air gives a breaking wave a visible body even when the water
    // behind it has the same colour. Density follows moving folds and pockets;
    // clear holes keep this from becoming a filled white sprite wall.
    float fold=noise(vec2(u*9.+sin(v*6.-age)*.65+seed,v*6.-age*1.3));
    aeration=smoothstep(.17,.82,n*.45+detail*.20+fold*.35);
    aeration*=.40+.60*smoothstep(.10,.60,v);
    float pore=noise(vec2(u*24.+seed+11.,v*12.+age*2.3));
    openings=1.-smoothstep(.72,.91,pore)*smoothstep(.22,.78,v)*.82;
    vec3 aeratedWater=mix(vec3(.38,.52,.44),vec3(.59,.71,.63),aeration);
    water=mix(water,aeratedWater,.55+.34*aeration);
  }
  vec3 light=mix(vec3(.82,.88,.84),breaker_tint.rgb,.20);
  vec3 rgb=mix(water,light,foam*.90);
  float bodyAlpha=impact ? .28+.18*aeration : .13;
  float alpha=(bodyAlpha+.10*fresnel+foam*(impact?.46:.44))*film*edge*breaker_episode.w*openings;
  if(kind==1)alpha*=.6;
  if(kind==3)alpha*=.45;
  float sceneDepth=texture(tex_T26,screen).r;
  float depthFade=clamp((gl_FragCoord.z-sceneDepth)/max(fwidth(gl_FragCoord.z)*1.7,0.000000025),0.,1.);
  alpha*=depthFade*(1.-smoothstep(130.,260.,length(ocean_eye-breaker_world)));
  if(alpha<.007)discard;
  color=vec4(rgb,alpha);
}
