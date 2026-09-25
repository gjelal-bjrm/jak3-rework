#version 410 core
// Ombres du soleil : profondeur du decor vue depuis le soleil (positions en unites du jeu).
layout (location = 0) in vec3 position_in;
uniform mat4 light_matrix;
void main() {
  gl_Position = light_matrix * vec4(position_in / 4096.0, 1.0);
}
