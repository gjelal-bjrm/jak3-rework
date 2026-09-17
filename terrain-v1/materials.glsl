// PALACE_MATERIAL_BEGIN
uniform int palace_material;
uniform vec3 palace_eye;

vec3 shadePalaceMaterial(vec3 existing,vec3 albedo,vec3 p) {
  if (palace_material==0) return existing;
  vec3 dx=dFdx(p),dy=dFdy(p);
  vec3 crossed=cross(dx,dy);
  if (dot(crossed,crossed)<1e-16) return existing;
  vec3 view=normalize(palace_eye-p);
  vec3 geometric=normalize(crossed);
  if (dot(geometric,view)<0.0) geometric=-geometric;
  bool metal=palace_material==3,glass=palace_material==4,leaf=palace_material==5;
  float roughness=metal?.48:(glass?.19:(leaf?.72:(palace_material==6?.95:.86)));
  // Subtle relief estimated from the filtered albedo, not a displacement or
  // an authored height map. World-space derivatives make its scale stable.
  float height=dot(albedo,vec3(.2126,.7152,.0722))*(glass?.004:(leaf?.003:.022));
  vec3 rx=cross(dy,geometric),ry=cross(geometric,dx);
  float determinant=dot(dx,rx);
  vec3 gradient=(rx*dFdx(height)+ry*dFdy(height))/
      (sign(determinant)*max(abs(determinant),1e-12));
  gradient*=min(1.0,.28/max(length(gradient),.00001));
  vec3 normal=normalize(geometric-gradient);
  vec3 light=normalize(vec3(-.38,.82,-.43));
  float visibility=clamp(dot(existing,vec3(.2126,.7152,.0722))/
      max(dot(albedo,vec3(.2126,.7152,.0722)),.08),.0,1.2);
  float relief=clamp(dot(normal,light)-dot(geometric,light),-.22,.22);
  vec3 result=existing*(1.0+relief*.55);
  float nv=max(dot(normal,view),.001),nl=max(dot(normal,light),.001);
  vec3 halfway=normalize(view+light);
  float nh=max(dot(normal,halfway),0.0),vh=max(dot(view,halfway),0.0);
  float a=roughness*roughness,a2=a*a;
  float denom=nh*nh*(a2-1.0)+1.0;
  float distribution=a2/(3.14159265*denom*denom);
  float k=(roughness+1.0)*(roughness+1.0)*.125;
  float geometry=(nv/(nv*(1.0-k)+k))*(nl/(nl*(1.0-k)+k));
  vec3 f0=metal?mix(vec3(.14),albedo,.42):vec3(.04);
  vec3 fresnel=f0+(1.0-f0)*pow(1.0-vh,5.0);
  vec3 specular=distribution*geometry*fresnel/max(4.0*nv*nl,.01);
  result+=min(specular*nl,vec3(.38))*vec3(1.0,.90,.72)*visibility*.42;
  if (glass) {
    vec3 reflected=reflect(-view,normal);
    vec3 sky=mix(vec3(.14,.12,.085),vec3(.32,.39,.48),smoothstep(-.25,.7,reflected.y));
    float grazing=.04+.96*pow(1.0-nv,5.0);
    result=mix(result,sky,grazing*.30*clamp(visibility,0.0,1.0));
  }
  if (leaf) {
    float transmitted=pow(max(dot(view,-light),0.0),3.0)*.10;
    result+=albedo*vec3(.65,.9,.38)*transmitted*visibility;
  }
  return result;
}
// PALACE_MATERIAL_END
