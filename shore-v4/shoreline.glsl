// Distances in metres to solid bank cross sections, at each real basin height.
uniform sampler2DArray shore_field;
const float shore_levels[4]=float[4](240.629257,241.491302,242.372253,243.497742);
int shoreLayer(float y) {
  int layer=0;
  for(int i=1;i<4;i++)if(abs(y-shore_levels[i])<abs(y-shore_levels[layer]))layer=i;
  return layer;
}
vec3 shoreUV(vec3 P) { return vec3((P.xz-vec2(1944.0,-524.0))/128.0,float(shoreLayer(P.y))); }
float shoreDistance(vec3 P) {
  vec3 uv=shoreUV(P);
  if(any(lessThan(uv.xy,vec2(0)))||any(greaterThan(uv.xy,vec2(1))) ||
     abs(P.y-shore_levels[int(uv.z)])>0.5)return 1.5;
  return texture(shore_field,uv).r;
}
vec2 shoreDirection(vec3 P) {
  vec3 uv=shoreUV(P);float e=1.0/1024.0;
  vec2 gradient=vec2(texture(shore_field,uv+vec3(e,0,0)).r-texture(shore_field,uv-vec3(e,0,0)).r,
                     texture(shore_field,uv+vec3(0,e,0)).r-texture(shore_field,uv-vec3(0,e,0)).r);
  return gradient/max(length(gradient),0.001);
}
