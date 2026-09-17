#version 410 core
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
uniform vec4 fluid_viewport;
uniform mat4 ocean_camera;
uniform vec3 ocean_eye;
uniform float ocean_level;
out vec4 color;
void main(){
  vec2 uv=gl_FragCoord.xy/vec2(textureSize(tex_T25,0));
  float z=max(texture(tex_T26,uv).r,.0000001);
  vec4 h=vec4((gl_FragCoord.xy-fluid_viewport.xy)/fluid_viewport.zw*2.-1.,z*2.-1.,1.);
  h.y/=(512./416.)*.5;
  vec4 world=inverse(-ocean_camera)*h;
  vec3 delta=world.xyz/world.w/4096.;
  float distanceInWater=length(delta);
  if(delta.y>0.)distanceInWater=min(distanceInWater,(ocean_level-ocean_eye.y)*length(delta)/delta.y);
  vec3 scene=texture(tex_T25,uv).rgb;
  vec3 trans=exp(-vec3(.125,.062,.075)*max(distanceInWater,0.));
  color=vec4(scene*trans+vec3(.046,.095,.081)*(1.-trans),1.);
}
