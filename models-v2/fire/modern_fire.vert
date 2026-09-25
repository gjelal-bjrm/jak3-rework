#version 410 core
// Feu du remaster : trois nappes par foyer, tournees vers la camera autour de l'axe vertical du foyer,
// decalees en largeur et en profondeur (impression de volume). fire_pos = base (m) + rayon ; fire_info = hauteur,
// graine, intensite.
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform vec4 fire_pos[128];
uniform vec4 fire_info[128];
out vec2 local;          // x : en rayons (-1,5..1,5) ; y : en hauteurs de flamme (-0,12..1,35)
out vec3 world;
flat out int src;
flat out int layer;
void main() {
  const vec2 c[6] = vec2[6](vec2(-1, 0), vec2(1, 0), vec2(1, 1), vec2(-1, 0), vec2(1, 1), vec2(-1, 1));
  src = gl_InstanceID / 3; layer = gl_InstanceID % 3;
  vec3 base = fire_pos[src].xyz; float r = fire_pos[src].w, H = fire_info[src].x;
  vec3 eye = cam_trans.xyz / 4096.;
  vec2 toEye = eye.xz - base.xz; float l = length(toEye);
  vec2 dir = l > 1e-3 ? toEye / l : vec2(0, 1);
  vec2 side = vec2(-dir.y, dir.x);
  vec2 k = c[gl_VertexID];
  float spread = layer == 1 ? 1.25 : 1.5;
  float lat = (float(layer) - 1.) * .16 * r, dep = (float(layer) - 1.) * .22 * r;
  vec3 p = base + vec3(side.x, 0., side.y) * (k.x * spread * r + lat) - vec3(dir.x, 0., dir.y) * dep;
  float y = -.12 + k.y * 1.47;
  p.y += y * H;
  local = vec2(k.x * spread, y);
  world = p;
  gl_Position = -pc_camera * vec4(p * 4096. - cam_trans.xyz, 1.);
  gl_Position.y *= (512. / 416.) * .5;
}
