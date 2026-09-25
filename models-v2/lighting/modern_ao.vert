#version 410 core
// Triangle plein ecran (eclairage moderne : occlusion ambiante).
out vec2 screen_uv;
void main() {
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  screen_uv = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
