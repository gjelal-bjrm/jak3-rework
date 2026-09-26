#version 410 core
// Eclairage moderne, etape 1 : occlusion ambiante (les coins, creux, dessous et contacts s'assombrissent,
// comme dans un jeu actuel). Calculee sur l'image a partir de la profondeur du decor opaque, en metres :
//   mode 0 : occlusion (12 echantillons dans l'hemisphere de la normale, deux echelles, rotation aleatoire) ;
//   mode 1 : flou qui respecte les bords (sens ao_dir) ;
//   mode 2 : application (multiplie l'image : melange GL_ZERO, GL_SRC_COLOR).
in vec2 screen_uv;
out vec4 color;
uniform sampler2D ao_depth;     // profondeur du decor (resolue, sans MSAA)
uniform sampler2D ao_input;     // occlusion (r) + distance (g) pour le flou / l'application
uniform mat4 pc_camera;
uniform vec4 ao_viewport;       // zone de dessin dans l'image (x, y, largeur, hauteur)
uniform int ao_mode;
uniform vec2 ao_dir;
uniform float ao_strength;

bool skyDepth(float d) { const float s = 1. / 16777215.; return d <= 1.5 * s || abs(d - 400. * s) <= 1.5 * s; }

mat4 inv_camera;
vec3 relPos(vec2 px, float d) {                  // position relative a la camera, en metres
  vec4 h = vec4((px - ao_viewport.xy) / ao_viewport.zw * 2. - 1., d * 2. - 1., 1.);
  h.y /= (512. / 416.) * .5;
  vec4 w = inv_camera * h;
  return w.xyz / w.w / 4096.;
}
vec3 project(vec3 rel) {                        // -> pixel (xy) et profondeur de camera (z)
  vec4 c = -pc_camera * vec4(rel * 4096., 1.);
  c.y *= (512. / 416.) * .5;
  vec3 n = c.xyz / c.w;
  return vec3((n.xy * .5 + .5) * ao_viewport.zw + ao_viewport.xy, c.w);
}
float depthAt(vec2 px) { return texelFetch(ao_depth, ivec2(px), 0).r; }

const vec3 kernel[12] = vec3[12](
  vec3(.53, .12, .34), vec3(-.41, .31, .22), vec3(.08, -.57, .41), vec3(-.19, -.25, .12),
  vec3(.71, -.22, .52), vec3(-.62, .48, .31), vec3(.23, .69, .45), vec3(-.35, -.71, .38),
  vec3(.88, .31, .22), vec3(-.84, -.12, .41), vec3(.12, .91, .21), vec3(-.29, -.82, .62));

void main() {
  vec2 px = gl_FragCoord.xy;
  if (ao_mode == 0) {
    inv_camera = inverse(-pc_camera);
    float d = depthAt(px);
    if (skyDepth(d)) { color = vec4(1., 1e4, 0., 1.); return; }
    vec3 P = relPos(px, d);
    float dist = length(P);
    // normale reconstruite : voisin le plus proche sur chaque axe (pas de halo aux silhouettes)
    vec3 px1 = relPos(px + vec2(1, 0), depthAt(px + vec2(1, 0))), px0 = relPos(px - vec2(1, 0), depthAt(px - vec2(1, 0)));
    vec3 py1 = relPos(px + vec2(0, 1), depthAt(px + vec2(0, 1))), py0 = relPos(px - vec2(0, 1), depthAt(px - vec2(0, 1)));
    vec3 dx = length(px1 - P) < length(P - px0) ? px1 - P : P - px0;
    vec3 dy = length(py1 - P) < length(P - py0) ? py1 - P : P - py0;
    vec3 N = normalize(cross(dx, dy));
    if (dot(N, -P) < 0.) N = -N;
    // rotation aleatoire par pixel (bruit a gradient entrelace)
    float a = 6.2831853 * fract(52.9829189 * fract(dot(px, vec2(.06711056, .00583715))));
    vec3 r = vec3(cos(a), sin(a), 0.);
    vec3 T = normalize(r - N * dot(r, N)); if (any(isnan(T))) T = normalize(cross(N, vec3(0, 1, 0)));
    vec3 B = cross(N, T);
    float occlusion = 0.;
    for (int scale = 0; scale < 2; scale++) {
      float R = scale == 0 ? clamp(.6 + dist * .006, .6, 1.6) : clamp(2.2 + dist * .02, 2.2, 7.);
      for (int i = 0; i < 12; i++) {
        vec3 k = kernel[i] * mix(.35, 1., float(i) / 11.);
        vec3 S = P + (T * k.x + B * k.y + N * k.z) * R;
        vec3 s = project(S);
        if (s.x < ao_viewport.x || s.y < ao_viewport.y || s.x >= ao_viewport.x + ao_viewport.z ||
            s.y >= ao_viewport.y + ao_viewport.w) continue;
        float ds = depthAt(s.xy);
        if (skyDepth(ds)) continue;
        vec3 Q = relPos(s.xy, ds);
        float behind = length(S) - length(Q);
        float range = smoothstep(0., 1., R / max(length(Q - P), 1e-3));
        // petite echelle allegee : les aretes ou deux plaques de roche se croisent faisaient des traits noirs
        occlusion += (behind > .03 * R ? 1. : 0.) * range * (scale == 0 ? .35 : .45);
      }
    }
    float ao = clamp(1. - 1.35 * occlusion / 12., 0., 1.);
    color = vec4(ao, dist, 0., 1.);
  } else if (ao_mode == 1) {
    vec2 c = texelFetch(ao_input, ivec2(px), 0).rg;
    if (c.g > 9e3) { color = vec4(1., c.g, 0., 1.); return; }
    const float w[5] = float[5](.227, .195, .122, .054, .016);
    float sum = c.r * w[0], total = w[0];
    for (int i = 1; i < 5; i++) {
      for (int sgn = -1; sgn <= 1; sgn += 2) {
        vec2 q = texelFetch(ao_input, ivec2(px + ao_dir * float(i * sgn) * 1.5), 0).rg;
        float wd = w[i] * exp(-abs(q.g - c.g) / (.04 * c.g + .15));
        sum += q.r * wd; total += wd;
      }
    }
    color = vec4(sum / total, c.g, 0., 1.);
  } else {
    vec2 c = texelFetch(ao_input, ivec2(px), 0).rg;
    // plafond : au plus -40 % (les plaques de roche qui se croisent donnaient des traits noirs « en epines »,
    // et les lieux encaisses, deja sombres dans l'eclairage du jeu, devenaient noirs)
    float ao = max(pow(c.r, 1.6), .6);
    float fade = 1. - smoothstep(180., 400., c.g);          // tres loin : la brume prend le relais
    color = vec4(vec3(mix(1., ao, ao_strength * fade)), 1.);
  }
}
