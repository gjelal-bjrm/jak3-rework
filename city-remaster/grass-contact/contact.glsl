// MARKET_GRASS_CONTACT_BEGIN
uniform int grass_contact_count;
uniform float grass_contact_time;
uniform vec4 grass_contacts[16]; // world metres + monotonic sample time
vec3 marketGrassContact(vec3 position, vec2 rawUV) {
  vec3 p = position / 4096.0;
  float height = clamp(1.0 - rawUV.y / 4096.0, 0.0, 1.0);
  float bend = height * height * (3.0 - 2.0 * height);
  vec2 direction = vec2(0.0);
  float strongest = 0.0;
  for (int i = 0; i < 16; ++i) {
    if (i >= grass_contact_count) break;
    vec4 samplePoint = grass_contacts[i];
    float age = max(0.0, grass_contact_time - samplePoint.w);
    vec2 away = p.xz - samplePoint.xz;
    float distanceToBody = length(away);
    float radial = 1.0 - smoothstep(0.12, 0.78, distanceToBody);
    // Discard another floor and distant tips; contact is at the real ground Y.
    float aboveGround = p.y - samplePoint.y;
    float vertical = smoothstep(-0.20, -0.03, aboveGround)
                   * (1.0 - smoothstep(1.25, 1.85, aboveGround));
    float recovery = 1.0 - smoothstep(0.08, 1.0, age);
    float strength = radial * vertical * recovery;
    // Max, not sum: repeated idle samples cannot accumulate extra bending.
    if (strength > strongest) {
      strongest = strength;
      direction = distanceToBody > 0.005 ? away / distanceToBody : vec2(0.83205, 0.55470);
    }
  }
  return vec3(direction.x * 0.28, -0.08, direction.y * 0.28)
       * strongest * bend * 4096.0;
}
// MARKET_GRASS_CONTACT_END
