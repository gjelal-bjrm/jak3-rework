#version 410 core
// Feu du remaster : etincelles (12 par foyer) qui montent en tournoyant, clignotent et s'eteignent.
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform float fire_time;
uniform vec4 fire_pos[48];
uniform vec4 fire_info[48];
uniform float viewport_height;
out float heat;
void main() {
  int id = gl_VertexID / 12, k = gl_VertexID % 12;
  float seed = fire_info[id].y * 13.7 + float(k) * 2.731;
  float r = fire_pos[id].w, H = fire_info[id].x, strength = fire_info[id].z;
  float life = 1.4 + .6 * fract(sin(seed) * 43758.5);
  float age = mod(fire_time * (.8 + .3 * fract(seed)) + seed, life);
  vec3 p = fire_pos[id].xyz + vec3(sin(seed * 1.3) * r * .45, H * .25, cos(seed * 1.7) * r * .45);
  float rise = age * (1.1 + H * .35);
  p += vec3(sin(age * 3.1 + seed) * age * .28, rise, cos(age * 2.6 + seed) * age * .24);
  gl_Position = -pc_camera * vec4(p * 4096. - cam_trans.xyz, 1.);
  gl_Position.y *= (512. / 416.) * .5;
  float d = length(p - cam_trans.xyz / 4096.);
  gl_PointSize = clamp(viewport_height * .03 / max(d, 1.), 1.5, 6.);
  float twinkle = .6 + .4 * sin(fire_time * 23. + seed * 5.);
  heat = smoothstep(0., .1, age) * (1. - smoothstep(life * .35, life, age)) * twinkle * strength;
}
