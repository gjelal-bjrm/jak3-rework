// Arena lava material. It uses the original moving lava texture as a flow/height
// field, with apparent depth and view-dependent highlights, independent of baked
// sunlight. It deliberately leaves depth, collision and the PS2 alpha contract intact.
float lavaHeight(vec2 q) {
  vec3 t = texture(tex_T0, q).rgb;
  return dot(t, vec3(0.22, 0.75, 0.03));
}

vec3 shadeArenaLava(vec2 originalUV, vec3 viewVector) {
  vec3 V = normalize(viewVector + vec3(0.0, 0.001, 0.0));
  vec2 texel = 1.0 / vec2(textureSize(tex_T0, 0));
  vec2 q = originalUV;
  // Two bounded parallax steps avoid unstable offsets at grazing angles.
  vec2 parallax = clamp(V.xz / max(abs(V.y), 0.35), vec2(-2.0), vec2(2.0)) * 0.012;
  q -= parallax * (lavaHeight(q) - 0.48);
  q -= parallax * (lavaHeight(q) - 0.48) * 0.5;
  vec3 flowing = texture(tex_T0, q).rgb;
  float heat = lavaHeight(q);
  float hx = lavaHeight(q + vec2(texel.x, 0.0)) - lavaHeight(q - vec2(texel.x, 0.0));
  float hz = lavaHeight(q + vec2(0.0, texel.y)) - lavaHeight(q - vec2(0.0, texel.y));
  vec3 N = normalize(vec3(-hx * 12.0, 1.0, -hz * 12.0));
  vec3 L = normalize(vec3(0.50, 0.814, 0.296));
  vec3 H = normalize(V + L);
  float cooled = 1.0 - smoothstep(0.40, 0.55, heat);
  float hot = smoothstep(0.55, 0.78, heat);
  vec3 crust = vec3(0.20, 0.067, 0.024) * (0.65 + 0.35 * max(dot(N, L), 0.0));
  vec3 molten = flowing * vec3(1.04, 0.92, 0.85);
  vec3 emission = mix(molten, crust, cooled * 0.70);
  // A smooth hot core and broad wet highlights give the moving folds volume.
  emission += vec3(0.15, 0.067, 0.009) * hot;
  float specular = pow(max(dot(N, H), 0.0), 18.0);
  float fresnel = 0.045 + 0.20 * pow(1.0 - max(dot(N, V), 0.0), 5.0);
  vec3 reflectedLight = vec3(1.0, 0.75, 0.41) * specular * (0.25 + fresnel) * (1.0 - cooled * 0.65);
  reflectedLight += vec3(0.15, 0.18, 0.21) * fresnel * (1.0 - hot * 0.6);
  return emission + reflectedLight;
}
