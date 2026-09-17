#version 410 core
in vec3 fruit_normal;
in vec3 fruit_local;
in vec3 fruit_world;
flat in vec4 fruit_tint;
flat in float fruit_type;
flat in int fruit_stalk;
uniform vec3 market_eye;
uniform vec3 market_fog;
out vec4 color;
float hash(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
void main(){
  // Native opacity controls pixel coverage. The fixed screen-space threshold
  // is shared by front/back faces, so a fading fruit cannot fill its own holes.
  float alpha=clamp(fruit_tint.a*2.,0.,1.);
  float coverage=fract(52.9829189*fract(dot(floor(gl_FragCoord.xy),vec2(.06711056,.00583715))));
  vec3 base=fruit_type>1.5?vec3(.27,.51,.065):(fruit_type>.5?vec3(.85,.65,.13):vec3(.95,.40,.065));
  float variation=clamp(fruit_tint.r-fruit_tint.g,-.2,.3);
  if(fruit_type<.5)base=mix(base,vec3(.81,.22,.035),variation*.9);
  float marbling=noise(fruit_local*5.+17.);
  base*=.97+.06*marbling;
  float pores=noise(fruit_local*85.);
  float detail=1.-smoothstep(.018,.07,length(fwidth(fruit_local)));
  vec3 n=normalize(fruit_normal+detail*.035*vec3(noise(fruit_local*85.+7.)-.5,pores-.5,noise(fruit_local*85.+19.)-.5));
  vec3 light=normalize(vec3(-.45,.80,-.30)),view=normalize(market_eye-fruit_world);
  float diffuse=max(dot(n,light),0.);
  float softSpec=pow(max(dot(n,normalize(light+view)),0.),28.)*.20;
  if(fruit_stalk==1){base=vec3(.17,.13,.055);softSpec*=.12;}
  vec3 shaded=base*(.58+.42*diffuse)+softSpec*vec3(1.,.91,.70);
  shaded*=1.-detail*.065*(1.-pores);
  float fog=smoothstep(65.,220.,length(market_eye-fruit_world));
  // Evaluate fwidth before the per-pixel discard, with intact derivative quads.
  if(alpha<=coverage)discard;
  // Survivors are opaque; discarded fragments never occlude later particles.
  color=vec4(mix(shaded,market_fog,fog),1.);
}
