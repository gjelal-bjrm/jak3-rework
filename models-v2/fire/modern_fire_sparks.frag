#version 410 core
// Feu du remaster : etincelle ronde, coeur jaune, bord orange.
in float heat;
out vec4 color;
void main() {
  vec2 c = gl_PointCoord * 2. - 1.;
  float r = dot(c, c);
  if (r > 1. || heat < .01) discard;
  float core = exp(-r * 3.);
  color = vec4(mix(vec3(1.6, .45, .06), vec3(2., 1.5, .7), core) * core * heat, 0.);
}
