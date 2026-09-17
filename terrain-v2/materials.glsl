// PALACE_MATERIAL_BEGIN
uniform int palace_material;
uniform vec3 palace_eye;
in vec3 palace_smooth_normal;

float palaceHash(vec3 p) {
  p=fract(p*.1031); p+=dot(p,p.yzx+33.33);
  return fract((p.x+p.y)*p.z);
}
// Value and analytic gradient: stable world-space relief without UV seams.
vec4 palaceNoiseGradient(vec3 p) {
  vec3 i=floor(p),f=fract(p),u=f*f*f*(f*(f*6.0-15.0)+10.0);
  vec3 du=30.0*f*f*(f*(f-2.0)+1.0);
  float a=palaceHash(i),b=palaceHash(i+vec3(1,0,0));
  float c=palaceHash(i+vec3(0,1,0)),d=palaceHash(i+vec3(1,1,0));
  float e=palaceHash(i+vec3(0,0,1)),f0=palaceHash(i+vec3(1,0,1));
  float g=palaceHash(i+vec3(0,1,1)),h=palaceHash(i+vec3(1));
  float k1=b-a,k2=c-a,k3=e-a,k4=a-b-c+d;
  float k5=a-c-e+g,k6=a-b-e+f0,k7=-a+b+c-d+e-f0-g+h;
  return vec4(a+k1*u.x+k2*u.y+k3*u.z+k4*u.x*u.y+k5*u.y*u.z+k6*u.x*u.z+k7*u.x*u.y*u.z,
    du*vec3(k1+k4*u.y+k6*u.z+k7*u.y*u.z,
            k2+k5*u.z+k4*u.x+k7*u.z*u.x,
            k3+k6*u.x+k5*u.y+k7*u.x*u.y));
}
vec3 palaceSpecular(vec3 n,vec3 v,vec3 l,float roughness,vec3 f0) {
  float nv=max(dot(n,v),.005),nl=max(dot(n,l),.005);
  vec3 h=normalize(v+l);
  float nh=max(dot(n,h),0.0),vh=max(dot(v,h),0.0);
  float a=roughness*roughness,a2=a*a;
  float denominator=nh*nh*(a2-1.0)+1.0;
  float distribution=a2/(3.14159265*denominator*denominator);
  float k=(roughness+1.0)*(roughness+1.0)*.125;
  float geometry=(nv/(nv*(1.0-k)+k))*(nl/(nl*(1.0-k)+k));
  vec3 fresnel=f0+(1.0-f0)*pow(1.0-vh,5.0);
  return distribution*geometry*fresnel/max(4.0*nv,.02);
}
vec3 shadePalaceMaterial(vec3 existing,vec3 albedo,vec3 p) {
  if (palace_material==0) return existing;
  vec3 dx=dFdx(p),dy=dFdy(p),crossed=cross(dx,dy);
  if (dot(crossed,crossed)<1e-16) return existing;
  vec3 v=normalize(palace_eye-p),geometric=normalize(crossed);
  if (dot(geometric,v)<0.0) geometric=-geometric;
  if(palace_material!=4 && dot(palace_smooth_normal,palace_smooth_normal)>.1) {
    vec3 smoothNormal=normalize(palace_smooth_normal);
    if(dot(smoothNormal,geometric)<0.0)smoothNormal=-smoothNormal;
    geometric=normalize(mix(geometric,smoothNormal,palace_material==7?.82:.98));
  }
  bool wood=palace_material==2,metal=palace_material==3;
  bool glass=palace_material==4,leaf=palace_material==5;
  bool cloth=palace_material==6,rock=palace_material==7;
  vec3 q=p-vec3(2000,240,-440);
  float footprint=max(length(dx),length(dy));
  vec4 broad=palaceNoiseGradient(q*(rock?2.3:4.0));
  vec4 fine=palaceNoiseGradient(q*31.0);
  float fineVisibility=1.0-smoothstep(.012,.055,footprint);
  // Rock erosion is centimetre-scale; glass, metal and leaves are much smoother.
  float strength=rock?.32:(wood?.13:(metal?.035:(glass?.015:(leaf?.035:.17))));
  vec3 detail=broad.yzw*strength+fine.yzw*.10*fineVisibility;
  if (wood) detail*=vec3(1.0,.15,1.0);
  if (leaf) detail*=.35;
  // Albedo includes pigment and tiny pores, not measured height. Differentiating
  // its full-resolution luminance produced conspicuous 2x2-pixel normal blocks.
  // Keep relief continuous in world space; use authored normals for silhouettes.
  vec3 gradient=detail-geometric*dot(detail,geometric);
  vec3 n=normalize(geometric-gradient);
  vec3 l=normalize(vec3(-.38,.82,-.43));
  vec3 fill=normalize(vec3(.60,.35,.72));
  float nv=max(dot(n,v),0.0),nl=max(dot(n,l),0.0);
  float legacyLight=dot(existing,vec3(.2126,.7152,.0722))/
                    max(dot(albedo,vec3(.2126,.7152,.0722)),.025);
  float visibility=mix(.28,1.0,smoothstep(.08,1.15,legacyLight));
  float sky=clamp(n.y*.5+.5,0.0,1.0);
  vec3 ambient=mix(vec3(.22,.19,.14),vec3(.42,.51,.61),sky);
  vec3 irradiance=ambient+vec3(1.0,.87,.65)*nl*1.23
      +vec3(.20,.25,.30)*max(dot(n,fill),0.0);
  // The new directional response changes luminance, not the original art's hue.
  // Replacing the baked RGB light by cool skylight turned ochre stones grey.
  float oldLuma=max(dot(existing,vec3(.2126,.7152,.0722)),.015);
  float newLuma=dot(albedo*irradiance*visibility,vec3(.2126,.7152,.0722));
  vec3 result=existing*mix(1.0,clamp(newLuma/oldLuma,.70,1.65),.82);
  if (rock || (!metal && !glass && !leaf && !cloth))
    result*=.96+.08*broad.x+.09*(fine.x-.5)*fineVisibility;
  float roughness=metal?.34:(glass?.13:(leaf?.43:(cloth?.88:(wood?.66:.79))));
  roughness=clamp(roughness+(broad.x-.5)*.11,.10,.98);
  vec3 f0=metal?mix(vec3(.18),albedo,.42):vec3(.04);
  vec3 spec=palaceSpecular(n,v,l,roughness,f0);
  result+=min(spec,vec3(.8))*vec3(1.0,.89,.70)*visibility*1.25;
  // Broad environment sheen gives metal a view-dependent material response.
  vec3 reflected=reflect(-v,n);
  vec3 environment=mix(vec3(.13,.095,.055),vec3(.42,.51,.63),smoothstep(-.4,.75,reflected.y));
  float fresnel=.04+.96*pow(1.0-nv,5.0);
  if (metal) result+=environment*(.07+.23*pow(1.0-nv,3.0))*visibility;
  if (glass) {
    // Real scenery remains visible through the native alpha-blended windows.
    // Do not paint an opaque sky or a fictitious exterior over their surface.
    result=existing*.84+min(spec,vec3(.38))*visibility;
  }
  if (leaf) {
    float transmitted=pow(max(dot(v,-l),0.0),2.0)*.45+.16*max(dot(-n,l),0.0);
    result+=albedo*vec3(.80,1.05,.42)*(transmitted+.12)*max(visibility,.62);
  }
  return max(result,vec3(0));
}
// PALACE_MATERIAL_END
