#version 410 core
// Feu du remaster : nappe de flamme peinte, style Genshin mais crédible.
//  - enveloppe en goutte (base large et ronde, pointe fine), hauteur qui respire ;
//  - langues de flamme : turbulence etiree verticalement qui monte vite, deformee (domaine tordu) ;
//  - bouts qui se detachent au-dessus de la pointe ;
//  - bords nets (aspect peint), coeur jaune-blanc, orange puis rouge sombre vers les bords et le haut,
//    racine legerement bleutee ; halo doux autour ;
//  - fondu au contact du decor (pas d'arete la ou la flamme touche les braises).
in vec2 local;
in vec3 world;
flat in int src;
flat in int layer;
out vec4 color;
uniform vec4 cam_trans;
uniform mat4 pc_camera;
uniform vec4 fire_pos[128];
uniform vec4 fire_info[128];
uniform float fire_time;
uniform vec4 fluid_viewport;
uniform sampler2D tex_T26;
uniform mat4 fire_inv_camera;   // inverse(-pc_camera), calculee sur le processeur

float hash(vec2 p) { vec3 q = fract(vec3(p.xyx) * .1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) {
  float v = 0., a = .5;
  for (int i = 0; i < 4; i++) { v += a * noise(p); p = mat2(1.6, 1.2, -1.2, 1.6) * p + 3.1; a *= .5; }
  return v;
}
bool skyDepth(float d) { const float s = 1. / 16777215.; return d <= 1.5 * s || abs(d - 400. * s) <= 1.5 * s; }
float sceneDistance() {
  vec2 uv = gl_FragCoord.xy / vec2(textureSize(tex_T26, 0));
  float d = texture(tex_T26, uv).r;
  if (skyDepth(d)) return 1e6;
  vec2 px = uv * vec2(textureSize(tex_T26, 0));
  vec4 h = vec4((px - fluid_viewport.xy) / fluid_viewport.zw * 2. - 1., d * 2. - 1., 1.);
  h.y /= (512. / 416.) * .5;
  vec4 w = fire_inv_camera * h;
  return length(w.xyz / w.w / 4096.);
}

void main() {
  float seed = fire_info[src].y + float(layer) * 3.71;
  float strength = fire_info[src].z;
  float x = local.x, y = local.y;
  float t = fire_time * (1.05 + .1 * sin(seed)) + seed * 7.;
  // turbulence qui monte (domaine tordu), plus forte en hauteur
  float w1 = fbm(vec2(x * 1.5 + seed, y * 1.8 - t * 1.7));
  float w2 = fbm(vec2(x * 3.4 - seed * 1.3, y * 3.9 - t * 2.9));
  float xw = x + (w1 - .5) * 1.1 * y + (w2 - .5) * .42 * y;
  float tip = .95 + .10 * sin(t * 2.1 + seed) + .06 * sin(t * 4.9 + seed * 2.1);   // la hauteur respire
  float yy = y / tip;
  // plusieurs langues : largeur modulee par un bruit horizontal qui monte
  float tongues = fbm(vec2(xw * 2.9 + seed * 5.1, yy - t * 1.55));
  float width = mix(.95, .02, pow(clamp(yy, 0., 1.), .55)) * (.18 + 1.45 * tongues);
  float body = width - abs(xw) * 1.05;
  // lechage fin des bords, bouts qui se detachent au-dessus
  float lick = fbm(vec2(xw * 6. + seed * 3., yy * 2.4 - t * 4.2));
  body += (lick - .5) * .42 * smoothstep(.08, .8, yy);
  body -= smoothstep(.55, 1.08, yy + (w2 - .5) * .7) * .6;
  float mask = smoothstep(0., .045, body) * smoothstep(-.07, .10, yy);     // bord net (peint), base adoucie
  float inner = smoothstep(.10, .42, body);
  float heat = clamp(inner * (1.05 - yy * .9) + (1. - yy) * .10, 0., 1.) * smoothstep(-.05, .12, yy);
  vec3 c = mix(vec3(.78, .10, .02), vec3(1.45, .46, .06), smoothstep(0., .40, heat));
  c = mix(c, vec3(1.65, 1.12, .40), smoothstep(.50, .95, heat));
  float glow = exp(-x * x * 1.2) * exp(-max(yy, 0.) * 1.6) * smoothstep(-.10, .05, yy) * .18;
  float pulse = .93 + .07 * sin(t * 7.7 + seed);
  vec3 rgb = (c * mask * (layer == 1 ? 1. : .72) + vec3(1.2, .38, .06) * glow) * .95 * pulse * strength;
  // fondu au contact du decor
  float soft = clamp((sceneDistance() - length(world - cam_trans.xyz / 4096.)) / .35, 0., 1.);
  rgb *= soft;
  if (max(rgb.r, max(rgb.g, rgb.b)) < .003) discard;
  color = vec4(rgb, 0.);
}
