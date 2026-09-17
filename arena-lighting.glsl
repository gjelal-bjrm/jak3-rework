// Spargus arena prototype, morning lighting. World positions are GOAL units / 4096.
// Uses geometric derivatives and existing baked shading as an occlusion proxy.
// No shadow map, screen-space AO, ray tracing, or extra texture fetches.
float arenaWeight(vec3 p) {
  vec2 centre = vec2(9520000.0, -1830000.0) / 4096.0;
  float radial = 1.0 - smoothstep(70.0, 100.0, length(p.xz - centre));
  float vertical = smoothstep(-18.0, -4.0, p.y) * (1.0 - smoothstep(100.0, 125.0, p.y));
  return radial * vertical;
}

vec3 arenaRelight(vec3 baked, vec3 p) {
  // Derivatives must be evaluated before any discard or divergent branch.
  vec3 rawNormal = cross(dFdx(p), dFdy(p));
  vec3 n = rawNormal * inversesqrt(max(dot(rawNormal, rawNormal), 1e-12));
  float weight = arenaWeight(p);
  vec3 sunDirection = normalize(vec3(0.50, 0.814, 0.296));
  float sun = max(dot(n, sunDirection), 0.0);
  float sky = clamp(n.y * 0.5 + 0.5, 0.0, 1.0);
  vec3 skylight = mix(vec3(0.39, 0.43, 0.49), vec3(0.57, 0.66, 0.79), sky);
  vec3 sunlight = vec3(0.88, 0.74, 0.53) * sun;
  vec3 bounce = vec3(0.15, 0.093, 0.045) * (1.0 - sky);
  float bakedLuma = dot(max(baked, vec3(0.0)), vec3(0.2126, 0.7152, 0.0722));
  float visibility = mix(0.32, 1.0, smoothstep(0.08, 0.90, bakedLuma));
  vec3 rebuilt = (skylight + sunlight + bounce) * visibility;
  // Retain part of the original artwork's shading to avoid erasing baked shadows.
  return mix(baked, rebuilt, 0.62 * weight);
}
