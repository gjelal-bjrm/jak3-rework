#version 410 core
layout(location=0)in vec4 source_position;
layout(location=1)in vec4 source_shape;
layout(location=2)in vec4 source_color;
uniform mat4 market_camera;
uniform vec3 market_eye;
out vec3 fruit_normal;
out vec3 fruit_local;
out vec3 fruit_world;
flat out vec4 fruit_tint;
flat out float fruit_type;
flat out int fruit_stalk;
const float PI=3.14159265359;
void main(){
  const ivec2 c[6]=ivec2[6](ivec2(0,0),ivec2(1,0),ivec2(1,1),ivec2(0,0),ivec2(1,1),ivec2(0,1));
  float sx=abs(source_position.w),sy=abs(source_shape.w);
  float green=1.-smoothstep(.08,.35,source_color.r);
  fruit_type=green>.5?2.:(sx>.57?1.:0.);
  fruit_stalk=gl_VertexID>=16*12*6?1:0;
  vec3 radii=vec3(sx,sy,sx)*.49;
  vec3 n,p;
  if(fruit_stalk==0){
    int cell=gl_VertexID/6;vec2 uv=(vec2(cell%16,cell/16)+vec2(c[gl_VertexID%6]))/vec2(16,12);
    float theta=uv.x*2.*PI,phi=uv.y*PI;
    n=vec3(cos(theta)*sin(phi),cos(phi),sin(theta)*sin(phi));
    float lobes=1.+.026*cos(theta*5.+.7)*pow(sin(phi),2.);
    float dimple=1.-.085*pow(abs(n.y),10.);
    p=n*radii*vec3(lobes,dimple,lobes);
    n=normalize(n/radii);
  }else{
    int vertex=gl_VertexID-16*12*6,cell=vertex/6;
    vec2 uv=(vec2(cell,0)+vec2(c[vertex%6]))/vec2(8,1);
    float theta=uv.x*2.*PI,r=min(sx*.035,.018)*(1.-uv.y*.45);
    p=vec3(cos(theta)*r,radii.y*.91+uv.y*sy*.09,sin(theta)*r);
    p.x+=uv.y*sy*.04;
    n=vec3(cos(theta),0,sin(theta));
  }
  // Skin detail stays attached to the fruit, including non-spherical fruit.
  fruit_local=p/radii;
  // Native Z rotation also rotates the solid fruit when it is knocked loose.
  float a=source_shape.z*(2.*PI/65536.);mat2 spin=mat2(cos(a),sin(a),-sin(a),cos(a));
  p.xy=spin*p.xy;n.xy=spin*n.xy;
  fruit_normal=n;fruit_world=source_position.xyz+p;
  fruit_tint=source_color;
  gl_Position=-market_camera*vec4((fruit_world-market_eye)*4096.,1.);
  gl_Position.y*=(512./416.)*.5;
}
