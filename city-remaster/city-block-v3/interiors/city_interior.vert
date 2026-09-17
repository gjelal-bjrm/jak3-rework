#version 410 core
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec2 uv;
layout(location=3) in vec4 color;
layout(location=4) in vec3 next_position;
layout(location=5) in vec3 next_normal;
uniform mat4 room_camera;
uniform mat3 room_basis;
uniform vec3 room_origin, room_eye, object_offset, object_scale;
uniform float object_yaw, pose_blend;
out vec3 local_pos, world_pos, world_normal;
out vec2 tex_uv;
out vec4 vertex_color;
void main(){
 float c=cos(object_yaw),s=sin(object_yaw);
 mat3 yaw=mat3(c,0,-s,0,1,0,s,0,c);
 local_pos=yaw*(mix(position,next_position,pose_blend)*object_scale)+object_offset;
 world_pos=room_origin+room_basis*local_pos;
 world_normal=normalize(room_basis*yaw*(mix(normal,next_normal,pose_blend)/object_scale));
 tex_uv=uv;vertex_color=color;
 gl_Position=-room_camera*vec4((world_pos-room_eye)*4096.,1.);
 gl_Position.y*=(512./416.)*.5;
}
