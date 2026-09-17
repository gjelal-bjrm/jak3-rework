// MARKET_GRASS_CONTACT_BEGIN
layout (location = 4) in vec4 grass_root_in; // actual blade root metres + height
uniform int grass_contact_count;
uniform float grass_contact_time;
uniform vec4 grass_contacts[16]; // real Jak ground metres + monotonic sample time
vec3 marketGrassContact(vec3 position, vec2 rawUV) {
  if (grass_contact_count == 0 || grass_root_in.w <= 0.0) return vec3(0.0);
  float height = clamp(1.0 - rawUV.y / 4096.0, 0.0, 1.0);
  if (height == 0.0) return vec3(0.0); // roots remain bit-identical
  float bend = height * height * (3.0 - 2.0 * height);
  vec2 p = position.xz / 4096.0;
  float reach = clamp(0.94 + grass_root_in.w * 0.10, 1.0, 1.3);
  float strongest = 0.0;
  vec2 directions = vec2(0.0);
  float totalWeight = 0.0;
  for (int i = 0; i < 16; ++i) {
    if (i >= grass_contact_count) break;
    vec4 samplePoint = grass_contacts[i];
    float age = max(0.0, grass_contact_time - samplePoint.w);
    vec2 away = grass_root_in.xz - samplePoint.xz;
    float distanceToRoot = length(away);
    float radial = 1.0 - smoothstep(0.12, reach, distanceToRoot);
    // Compare two ground positions, never a tall tip against Jak's feet.
    float floor = 1.0 - smoothstep(0.35, 0.9, abs(grass_root_in.y - samplePoint.y));
    float recovery = 1.0 - smoothstep(0.08, 1.0, age);
    float strength = radial * floor * recovery;
    vec2 outward = distanceToRoot > 0.025 ? away / distanceToRoot : p - samplePoint.xz;
    float outwardLength = length(outward);
    outward = outwardLength > 0.005 ? outward / outwardLength : vec2(0.83205, 0.55470);
    float weight = strength * strength * strength * strength;
    directions += outward * weight;
    totalWeight += weight;
    strongest = max(strongest, strength); // repeated idle contacts cannot amplify
  }
  if (totalWeight <= 0.000001) return vec3(0.0);
  vec2 direction = directions / totalWeight;
  float amplitude = clamp(0.26 + grass_root_in.w * 0.17, 0.34, 0.74);
  float drop = min(0.20, amplitude * amplitude / max(0.5, grass_root_in.w) * 0.5);
  return vec3(direction.x * amplitude, -drop, direction.y * amplitude)
       * strongest * bend * 4096.0;
}
// MARKET_GRASS_CONTACT_END
