#version 410 core
// Gouttes : trainee fine aux bouts effiles ; flocons : disque doux ; sable : trainee courte ocre.
in vec2 local;
in float fade;
out vec4 color;
uniform int wx_kind;
uniform vec3 wx_light;              // couleur des gouttes / flocons / grains a cette heure
uniform float wx_alpha;             // opacite de base
void main(){
  float a;
  if(wx_kind==1){
    float d=length(local);
    a=smoothstep(1.,.25,d);
  }else{
    float across=1.-local.x*local.x;
    float along=smoothstep(0.,.3,local.y)*smoothstep(1.,.55,local.y);
    a=across*along;
  }
  a*=wx_alpha*fade;
  if(a<.002)discard;
  color=vec4(wx_light*a,a);
}
