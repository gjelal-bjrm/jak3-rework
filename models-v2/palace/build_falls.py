"""Positions des chutes du palais (donnees des acteurs d'origine) -> models-v2/palace/palace_falls.glsl.

- 11 petites chutes (group-waspala-waterfall-top) : levre = emetteur + 0,5 m, direction = rotation de
  l'emetteur (avant local +z), largeur 1 m, chute de 2,4 m (vitesse et gravite des particules d'origine) ;
- impacts : 4 grandes chutes du plafond (fountain_positions), 11 pieds de petites chutes, 10 pieds
  d'origine (group-waspala-waterfall-base).
"""
from pathlib import Path
import json, math
H = Path(__file__).resolve().parent; R = H.parents[1]
actors = json.loads((R / 'data/decompiler_out/jak3/entities/waspala-actors.json').read_text())
tops = [a for a in actors if a['lump'].get('art-name') == 'group-waspala-waterfall-top']
bases = [a for a in actors if a['lump'].get('art-name') == 'group-waspala-waterfall-base']
DROP, SPEED, GRAVITY = 2.4, 0.45, 4.8
fall_time = math.sqrt(2 * DROP / GRAVITY)
starts, dirs, landings = [], [], []
for a in tops:
    x, y, z = a['trans'][:3]; q = a['quat']
    ang = 2 * math.atan2(q[1], q[3])
    d = (math.sin(ang), math.cos(ang))
    starts.append((x, y + 0.5, z)); dirs.append(d)
    landings.append((x + d[0] * SPEED * fall_time, y + 0.5 - DROP, z + d[1] * SPEED * fall_time))
big = []
text = (R / 'liquids-v3/fountain_positions.glsl').read_text()
import re
ends = re.search(r'fountain_end\[4\]=vec3\[4\]\((.*)\);', text).group(1)
big = [tuple(float(v) for v in m.split(',')) for m in re.findall(r'vec3\(([^)]*)\)', ends)]
small = [tuple(b['trans'][:3]) for b in bases]   # pieds des petites cascades (acteurs d'origine)
def v3(p): return 'vec3(' + ','.join(f'{c:.3f}' for c in p) + ')'
def v2(p): return 'vec2(' + ','.join(f'{c:.4f}' for c in p) + ')'
out = f'''// Genere par models-v2/palace/build_falls.py (acteurs d'origine du palais).
const int cascade_count={len(starts)};
const vec3 cascade_start[{len(starts)}]=vec3[{len(starts)}]({','.join(map(v3, starts))});
const vec2 cascade_dir[{len(dirs)}]=vec2[{len(dirs)}]({','.join(map(v2, dirs))});
const float cascade_drop={DROP:.2f},cascade_speed={SPEED:.2f},cascade_gravity={GRAVITY:.2f};
const vec3 impact_big[4]=vec3[4]({','.join(map(v3, big))});
const vec3 impact_small[{len(small)}]=vec3[{len(small)}]({','.join(map(v3, small))});
'''
(H / 'palace_falls.glsl').write_text(out)
print(f'{len(starts)} petites chutes, {len(big)} grands impacts, {len(small)} petits impacts')

# ---- Fonction d'impact du bassin (inseree dans liquids-v3/fluids.glsl entre marqueurs)
impacts = [(p, 1.1) for p in big] + [(p, 0.45) for p in small]
consts = ','.join(f'vec4({p[0]:.3f},{p[1]:.3f},{p[2]:.3f},{r:.2f})' for p, r in impacts)
function = f'''// PALACE_IMPACT_BEGIN (genere par models-v2/palace/build_falls.py)
// Pieds des chutes : eau blanche qui bouillonne, anneaux de vagues qui s'eloignent, ecume qui derive vers
// l'exterieur. Renvoie la pente de la surface (xy) et l'ecume (z).
vec3 palaceImpact(vec3 P) {{
  const vec4 impacts[{len(impacts)}]=vec4[{len(impacts)}]({consts});
  vec2 slope=vec2(0.0);float foam=0.0;
  for(int i=0;i<{len(impacts)};i++) {{
    vec4 im=impacts[i];
    if(abs(P.y-im.y)>0.8)continue;
    vec2 dp=P.xz-im.xz;float d=length(dp);float R=im.w;
    if(d>R*5.0)continue;
    vec2 dir=dp/max(d,1e-3);
    float t=fluid_time+float(i)*3.7;
    // coeur : eau aeree qui bouillonne
    float core=exp(-d*d/(R*R)*1.4);
    float churn=fluidNoise(dp*10.0/R+vec2(t*2.3,-t*1.7))*0.50+fluidNoise(dp*21.0/R-vec2(t*3.1,t*2.4))*0.32
               +fluidNoise(dp*43.0/R+vec2(t*4.0,t*3.3))*0.18;
    float bubbles=smoothstep(0.30,0.70,churn);
    foam+=core*(0.35+0.65*bubbles);
    // couronne d'ecume qui s'ouvre autour du point d'impact
    float crown=exp(-pow((d-R*0.9)/(R*0.35),2.0))*smoothstep(0.45,0.7,churn);
    foam+=crown*0.55;
    // ecume qui derive vers l'exterieur par plaques
    float ang=atan(dp.y,dp.x);
    float drift=fluidNoise(vec2(ang*2.2+float(i),d*2.4/R-t*1.1))*0.65+fluidNoise(vec2(ang*5.0,d*5.0/R-t*1.6)+4.0)*0.35;
    foam+=smoothstep(0.62,0.92,drift)*exp(-d/(R*1.3))*(1.0-core)*0.35;
    // anneaux de vagues qui s'eloignent et s'amortissent
    float k=6.5/R,w=7.0;
    float amp=0.10*exp(-d/(R*2.2))*smoothstep(0.0,R*0.5,d);
    slope+=dir*amp*cos(d*k-t*w);
    // surface agitee au coeur
    vec2 e=vec2(0.05,0.0);
    float c0=fluidNoise(dp*4.0/R+t*2.0);
    slope+=vec2(fluidNoise((dp+e.xy)*4.0/R+t*2.0)-c0,fluidNoise((dp+e.yx)*4.0/R+t*2.0)-c0)/0.05*0.02*core;
  }}
  return vec3(slope,clamp(foam,0.0,1.0));
}}
// PALACE_IMPACT_END
'''
fl = R / 'liquids-v3/fluids.glsl'
raw = fl.read_bytes(); crlf = b'\r\n' in raw
s = raw.decode('utf-8').replace('\r\n', '\n')
if '// PALACE_IMPACT_BEGIN' in s:
    a = s.index('// PALACE_IMPACT_BEGIN'); b = s.index('// PALACE_IMPACT_END') + len('// PALACE_IMPACT_END\n')
    s = s[:a] + function + s[b:]
else:
    at = s.index('vec3 shadeModernWater(')
    s = s[:at] + function + '\n' + s[at:]
if crlf: s = s.replace('\n', '\r\n')
fl.write_bytes(s.encode('utf-8'))
# ---- Gerbes (water_spray.vert) : grands impacts + pieds des petites chutes + pieds d'origine
spray = [p for p in big] + small
(H / 'spray_impacts.glsl').write_text(
    f'const int water_impact_count={len(spray)};\n'
    f'const vec3 water_impacts[{len(spray)}]=vec3[{len(spray)}]({",".join(map(v3, spray))});\n')
print(f'fonction palaceImpact ({len(impacts)} impacts) et {len(spray)} sources de gerbes')
