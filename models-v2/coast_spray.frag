#version 410 core
in vec2 droplet_uv;
in float opacity;
in float mist;
in vec3 droplet_world;
uniform sampler2D tex_T26;
uniform vec4 fluid_viewport;
out vec4 color;
void main(){
  float r=dot(droplet_uv,droplet_uv);
  float alpha=(1.-smoothstep(.12,1.,r))*opacity;
  vec2 screen=(gl_FragCoord.xy-fluid_viewport.xy)/fluid_viewport.zw;
  float depth=texture(tex_T26,screen).r;
  alpha*=clamp((gl_FragCoord.z-depth)/max(fwidth(gl_FragCoord.z)*2.,.00000004),0.,1.);
  if(alpha<.009)discard;
  float glint=pow(max(0.,1.-length(droplet_uv-vec2(-.24,.28))),4.);
  color=vec4(mix(vec3(.62,.72,.68),vec3(.92,.95,.93),glint*.85+mist*.12),alpha);   // gouttes claires, eclat solaire
}
