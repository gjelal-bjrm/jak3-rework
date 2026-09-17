#version 410 core
in vec2 uv;
out vec4 color;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
uniform sampler2D tex_T27;
uniform mat4 lava_camera;
uniform vec3 lava_position;
uniform int bloom_pass;
uniform float fluid_time;

void main() {
  if (bloom_pass==0) {
    float depth=texture(tex_T26,uv).r;
    vec4 h=vec4(uv*2.0-1.0,depth*2.0-1.0,1.0);
    h.y/=(512.0/416.0)*0.5;
    vec4 world=inverse(-lava_camera)*h;
    vec3 p=(world.xyz/world.w+lava_position)/4096.0;
    float mask=(1.0-smoothstep(0.16,0.25,abs(p.y-9.999542)))
               *step(2186.13,p.x)*step(p.x,2466.15)*step(-644.11,p.z)*step(p.z,-364.08);
    vec3 source=texture(tex_T25,uv).rgb;
    mask*=smoothstep(0.35,0.88,source.r)*smoothstep(0.06,0.28,source.g);
    color=vec4(source*vec3(1.0,0.7,0.35)*mask,mask);
  } else if (bloom_pass==1 || bloom_pass==2) {
    vec2 axis=(bloom_pass==1?vec2(1,0):vec2(0,1))/vec2(textureSize(tex_T27,0));
    color=texture(tex_T27,uv)*0.227027;
    color+=(texture(tex_T27,uv+axis*1.384615)+texture(tex_T27,uv-axis*1.384615))*0.316216;
    color+=(texture(tex_T27,uv+axis*3.230769)+texture(tex_T27,uv-axis*3.230769))*0.070270;
  } else {
    vec4 glow=texture(tex_T27,uv);
    vec2 shimmer=vec2(sin(uv.y*150.0-fluid_time*2.0),sin(uv.x*130.0+fluid_time*1.6));
    // Distortion remains subpixel and local to visible hot lava.
    shimmer*=glow.a*0.00024;
    color=vec4(texture(tex_T25,uv+shimmer).rgb+glow.rgb*0.26,1.0);
  }
}
