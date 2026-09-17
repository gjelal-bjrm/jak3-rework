#version 410 core
in vec2 drift_uv;
in float drift_alpha;
in float drift_seed;
in float drift_layer;
in vec3 drift_world;
uniform float drift_time;
uniform vec3 drift_eye;
uniform vec3 drift_fog;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T26;
out vec4 color;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){
  vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);
}
void main(){
  vec2 uv=drift_uv;float t=drift_time,s=drift_seed;
  // Stries qui filent dans le sens du vent (u), fines en travers (v), plus un grain de sable.
  float streak=noise(vec2(uv.x*4.-t*3.1+s,uv.y*14.+s*3.));
  float ripple=noise(vec2(uv.x*9.-t*4.6+s*2.,uv.y*6.));
  float grain=noise(vec2(uv.x*27.-t*6.5,uv.y*45.+s));
  float density=smoothstep(.40,.88,streak*.55+ripple*.25+grain*.20);
  float mask;
  if(drift_layer<.5){
    vec2 d=(uv-.5)*vec2(2.,2.6);mask=1.-smoothstep(.30,1.,length(d));           // nappe elliptique
  } else {
    mask=(1.-smoothstep(.2,1.,abs(uv.x-.5)*2.))*(1.-smoothstep(.15,1.,uv.y))*smoothstep(0.,.12,uv.y);  // voile qui s efface en hauteur
  }
  float alpha=density*mask*drift_alpha*(drift_layer<.5?.62:.40);
  // Particule douce : fondu au contact du sol et des murs, pas d intersection dure.
  vec2 screen=(gl_FragCoord.xy-fluid_viewport.xy)/fluid_viewport.zw;
  float sceneDepth=texture(tex_T26,screen).r;
  alpha*=clamp((gl_FragCoord.z-sceneDepth)/max(fwidth(gl_FragCoord.z)*3.,0.00000004),0.,1.);
  alpha*=1.-smoothstep(90.,150.,length(drift_world-drift_eye));
  if(alpha<.006)discard;
  vec3 sand=vec3(.76,.66,.51);
  color=vec4(mix(sand,drift_fog,.22),alpha);
}
