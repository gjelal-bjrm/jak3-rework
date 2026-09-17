// ---- Vagues de bord de la plage de Spargus (procedurales, remplacent les sprites natifs wave-foam) ----
// SHORE_TABLES_INSERT
const float shorePeriod=7.4;      // s entre deux lames
const float shoreWavelength=17.;  // m pres du bord (celerite ~2,3 m/s)
const float shoreSlope=.127;      // pente du sable mesuree dans le WCB natif (1:8)
const float shoreRunup=5.5;       // m : remontee maximale de la lame sur le sable
const vec2 shoreAlong=vec2(.8,.6);// direction generale de la plage (ouest -> est)
// Distance signee au trait de cote du sable : >0 vers la mer, <0 sur le sable. seaward : direction vers le large.
float shoreSigned(vec2 xz,out vec2 seaward){
  float best=1e12;vec2 bestVec=vec2(0,1);float side=1.;
  for(int i=0;i<shorePointCount-1;i++){
    vec2 a=shorePoints[i],ab=shorePoints[i+1]-a;
    float t=clamp(dot(xz-a,ab)/dot(ab,ab),0.,1.);
    vec2 r=xz-(a+ab*t);float d2=dot(r,r);
    if(d2<best){best=d2;bestVec=r;side=(ab.x*(xz.y-a.y)-ab.y*(xz.x-a.x))>0.?-1.:1.;}
  }
  float d=sqrt(best);
  seaward=d>1e-3?bestVec/d*side:vec2(0,1);
  return d*side;
}
// Phase des lames (entier = crete). Un leger bruit le long de la plage evite des cretes parfaitement paralleles.
float shorePhase(float d,vec2 xz,float time){
  float jitter=(swellNoise(vec2(dot(xz,shoreAlong)*.025,time*.03)).x-.5)*3.;
  return (max(d,0.)+jitter)/shoreWavelength+time/shorePeriod;
}
// Position du front de la lame sur le sable (m) selon la phase u (0 = lame arrivee au trait de cote).
float shoreSwashFront(float u){return shoreRunup*(smoothstep(0.,.34,u)-smoothstep(.34,.88,u));}
// x : hauteur au-dessus de 9 m ; y : ecume de deferlement ; z : nappe sur le sable (1 au bord, 0,4 au front) ; w : front de la lame.
vec4 shoreWave(vec2 xz,float time,out vec2 seaward){
  float d=shoreSigned(xz,seaward);
  if(d>70.||d<-(shoreRunup+3.))return vec4(0);
  float u=fract(shorePhase(d,xz,time));
  float uu=u+.12*sin(6.2831853*u);                  // face avant (vers le sable) plus raide
  float crest=pow(.5+.5*cos(6.2831853*uu),2.4);
  float shoaling=mix(.05,.34,smoothstep(45.,7.,d));  // la houle se cambre en arrivant sur le sable
  float breaking=smoothstep(13.,3.,d);               // puis la crete se brise
  float height=(crest-.22)*shoaling*(1.-.45*breaking);
  float trail=exp(-u*5.);                            // ecume laissee derriere la crete
  float foam=breaking*clamp(max(crest*1.3-.15,trail*.85),0.,1.)*smoothstep(-.5,2.,d);
  float l=-d,swash=0.,front=0.;
  if(d<2.){
    // Nappe mince qui monte le sable puis redescend ; entre deux lames l'eau se retire un peu sous 9 m.
    float lf=shoreSwashFront(u),active=smoothstep(0.,.6,lf);
    float film=(.04+.11*(1.-clamp(l/max(lf,.01),0.,1.)))*active-.05*(1.-active);
    // Au-dela du front, la nappe s'amincit en pente douce et passe sous le sable (pas de marche verticale).
    float sheet=l<lf?shoreSlope*max(l,0.)+film:shoreSlope*lf+film-(l-lf)*.45;
    height=mix(height,sheet,smoothstep(2.,-.3,d));
    if(l>-.6){
      swash=(l<lf?1.-.6*clamp(l/max(lf,.01),0.,1.):0.)*smoothstep(.15,.9,lf);
      front=smoothstep(.7,.05,abs(l-lf))*smoothstep(.2,1.,lf)*step(-.3,l);
    }
  }
  return vec4(height,foam,swash,front);
}
