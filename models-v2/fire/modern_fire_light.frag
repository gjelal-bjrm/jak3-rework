#version 410 core
// Feu du remaster : lumiere des flammes sur le decor proche (vacille, cachee par les obstacles) et air chaud
// qui ondule au-dessus. Remplace l'image a partir de sa copie (tex_T25 couleur, tex_T26 profondeur).
out vec4 color;
uniform mat4 pc_camera;
uniform vec4 cam_trans;
uniform float fire_time;
uniform int fire_count;
uniform vec4 fire_pos[128];
uniform vec4 fire_info[128];
uniform vec4 fluid_viewport;
uniform sampler2D tex_T25;
uniform sampler2D tex_T26;
uniform mat4 fire_inv_camera;

mat4 inv_camera;
vec3 project(vec3 P) {
  vec4 h = -pc_camera * vec4(P * 4096. - cam_trans.xyz, 1.);
  h.y *= (512. / 416.) * .5;
  vec3 n = h.xyz / h.w;
  return vec3((fluid_viewport.xy + (n.xy * .5 + .5) * fluid_viewport.zw) / vec2(textureSize(tex_T25, 0)), n.z * .5 + .5);
}
vec3 unproject(vec2 uv, float depth) {
  vec4 h = vec4((uv * vec2(textureSize(tex_T25, 0)) - fluid_viewport.xy) / fluid_viewport.zw * 2. - 1., depth * 2. - 1., 1.);
  h.y /= (512. / 416.) * .5;
  vec4 w = inv_camera * h;
  return w.xyz / w.w / 4096. + cam_trans.xyz / 4096.;
}
float flicker(float seed) {
  return .80 + .12 * sin(fire_time * 3.1 + seed) + .07 * sin(fire_time * 7.7 + seed * 1.7) + .05 * sin(fire_time * 13.3 + seed * .3);
}
void main() {
  inv_camera = fire_inv_camera;
  vec2 uv = gl_FragCoord.xy / vec2(textureSize(tex_T25, 0));
  float depth = texture(tex_T26, uv).r;
  vec3 scene = texture(tex_T25, uv).rgb;
  if (depth < .00001) { color = vec4(scene, 1); return; }
  vec3 P = unproject(uv, depth), eye = cam_trans.xyz / 4096.;
  vec3 N = normalize(cross(dFdx(P), dFdy(P)));
  if (dot(N, eye - P) < 0.) N = -N;
  vec3 ray = normalize(P - eye);
  vec3 light = vec3(0); vec2 haze = vec2(0);
  for (int i = 0; i < fire_count; i++) {
    float r = fire_pos[i].w, H = fire_info[i].x, seed = fire_info[i].y, strength = fire_info[i].z;
    vec3 source = fire_pos[i].xyz + vec3(0, H * .35, 0);
    float reach = 3.5 + H * 1.6;
    vec3 delta = source - P; float d = length(delta);
    if (d < reach) {
      float visible = 1.;
      for (int k = 1; k <= 4; k++) {
        vec3 probe = mix(P + N * .08, source, float(k) / 5.);
        vec3 s = project(probe);
        if (any(lessThan(s.xy, vec2(.001))) || any(greaterThan(s.xy, vec2(.999)))) continue;
        float z = texture(tex_T26, s.xy).r;
        if (z > s.z && length(unproject(s.xy, z) - probe) > .3) { visible = .08; break; }
      }
      float att = (1. - smoothstep(reach * .45, reach, d)) / (1. + d * d * .45);
      // la vasque (ou le sol) arrete la lumiere : rien n'est eclaire sous le niveau des braises
      att *= smoothstep(fire_pos[i].y - .6, fire_pos[i].y + .3, P.y);
      light += vec3(1.0, .42, .10) * max(dot(N, delta / max(d, .01)), 0.) * att * flicker(seed) * visible * strength * (.35 + .1 * H);
    }
    // air chaud au-dessus de la pointe
    vec3 hot = fire_pos[i].xyz + vec3(0, H * 1.05, 0);
    float along = dot(hot - eye, ray);
    if (along > 0. && along < length(P - eye)) {
      vec3 q = eye + along * ray - hot;
      float plume = exp(-dot(q.xz, q.xz) / (r * r * .9) - q.y * q.y / (H * H * .45)) * strength;
      haze += vec2(sin(q.y * 10. - fire_time * 6.3 + seed), cos(q.y * 7.5 - fire_time * 4.9 + seed)) * plume * .9;
    }
  }
  vec2 shifted = clamp(uv + haze / vec2(textureSize(tex_T25, 0)), vec2(.001), vec2(.999));
  if (abs(length(unproject(shifted, texture(tex_T26, shifted).r) - eye) - length(P - eye)) < 1.)
    scene = texture(tex_T25, shifted).rgb;
  color = vec4(scene + scene * light, 1.);
}
