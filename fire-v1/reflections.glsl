// FIRE_POSITIONS
// Approximate finite fire-source highlights, bent by the actual water normals.
vec3 palaceFireReflection(vec3 P,vec3 N,vec3 V) {
  vec3 reflected=reflect(-V,N),sum=vec3(0);
  for(int i=0;i<fire_count;i++) {
    vec3 delta=fire_sources[i].xyz+vec3(0,fire_heights[i]*.30,0)-P;
    float d=length(delta);
    if(d>38.0)continue;
    float angularRadius=clamp(fire_sources[i].w/max(d,1.0),.012,.25);
    float exponent=clamp(1.0/(angularRadius*angularRadius),48.0,1800.0);
    float glint=pow(max(dot(reflected,delta/max(d,.01)),0.0),exponent);
    float seed=float(i)*17.83;
    float pulse=.83+.12*sin(fluid_time*3.13+seed)+.06*sin(fluid_time*7.71+seed*1.7);
    sum+=vec3(1.0,.32,.045)*glint*pulse*(1.0-smoothstep(20.0,38.0,d));
  }
  return sum*.18;
}
