#version 410 core
in vec3 local_pos,world_pos,world_normal;
in vec2 tex_uv;
in vec4 vertex_color;
uniform sampler2D material_tex;
uniform vec3 material_color,room_eye,room_fog;
uniform mat3 room_basis;
uniform float roughness,room_occupancy;
uniform int texture_mode,emissive;
out vec4 color;
void main(){
 vec4 albedo=vec4(material_color,1.)*vertex_color;
 vec4 t=texture(material_tex,tex_uv);
 if(texture_mode==3)albedo*=t;
 else if(texture_mode>0)albedo.rgb*=mix(.80,1.15,clamp(dot(t.rgb,vec3(.299,.587,.114))*1.5,0.,1.));
 if(albedo.a<.15)discard;
 vec3 n=normalize(world_normal);
 if(!gl_FrontFacing)n=-n;
 vec3 daylight=normalize(room_basis*vec3(-.2,.6,1.));
 vec3 lamp_local=vec3(0,2.94,-1.65)-local_pos;
 vec3 lamp_direction=normalize(room_basis*lamp_local);
 float lamp= max(dot(n,lamp_direction),0.)/(1.+dot(lamp_local,lamp_local)*.34);
 float daylight_depth=exp(min(local_pos.z,0.)*.18);
 vec3 illumination=vec3(.29,.28,.24)+vec3(.56,.55,.46)*max(dot(n,daylight),0.)*daylight_depth;
 illumination+=vec3(.72,.36,.12)*lamp*room_occupancy;
 vec3 view_direction=normalize(room_eye-world_pos);
 float spec=pow(max(dot(n,normalize(daylight+view_direction)),0.),mix(62.,9.,roughness))*(1.-roughness)*.16;
 vec3 result=albedo.rgb*illumination+vec3(spec);
 if(emissive!=0)result=albedo.rgb*(.75+.25*room_occupancy);
 float fog=clamp((distance(room_eye,world_pos)-70.)/200.,0.,.6);
 color=vec4(mix(result,room_fog,fog),1.);
}
