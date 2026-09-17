"""Sable mouille de la plage de Spargus dans le shader de terrain (tfrag3.frag) installe.

Patch idempotent entre les marqueurs BEACH_WET_BEGIN / BEACH_WET_END, applique a data/ et engine-src/,
puis recopie dans variants/remaster (empreintes) par sync_variant.py. Partage la geometrie des vagues
de bord (shore_waves.glsl) : la bande humide et la pellicule brillante suivent la meme lame que la mer.
"""
from pathlib import Path
import re, subprocess, sys
H = Path(__file__).resolve().parent; R = H.parents[1]
REL = 'game/graphics/opengl_renderer/shaders/tfrag3.frag'
BEGIN, END = '// BEACH_WET_BEGIN', '// BEACH_WET_END'


def block():
    swell = (H.parent / 'ocean_swell.glsl').read_text()
    # swellHash + swellNoise (les deux premieres fonctions), necessaires a shorePhase
    noise = swell[swell.index('float swellHash'):swell.index('vec3 oceanSwellFiltered')]
    shore = (H / 'shore_waves.glsl').read_text().replace('// SHORE_TABLES_INSERT', (H / 'shore_tables.glsl').read_text())
    return BEGIN + '\n' + noise + shore + '''
// Sable humide : bande sombre permanente sous la limite des lames, pellicule brillante laissee par la lame qui recule.
vec3 beachWetSand(vec3 color,vec3 P){
  if(P.x<1440.||P.x>1600.||P.z<-530.||P.z>-405.||P.y<8.4||P.y>10.8)return color;
  vec2 seaward;float d=shoreSigned(P.xz,seaward);float l=-d;
  if(l<-1.5||l>shoreRunup+3.)return color;
  float low=smoothstep(10.6,9.5,P.y);
  float damp=max(smoothstep(shoreRunup+2.,1.5,l),smoothstep(1.2,-.5,l))*low;
  float u=fract(shorePhase(0.,P.xz,fluid_time));
  float lf=shoreSwashFront(u);
  // Sable decouvert depuis peu : entre le front actuel (qui recule) et la remontee maximale.
  float exposed=step(lf-.3,l)*smoothstep(shoreRunup+.4,shoreRunup-.6,l)*step(0.,l);
  float film=exposed*smoothstep(.30,.42,u)*(1.-smoothstep(.72,1.,u))*low;
  vec3 V=normalize(cam_trans.xyz/4096.-P);
  vec3 L=normalize(vec3(-.32,.66,-.68));
  float sheen=pow(max(dot(normalize(V+L),vec3(0.,1.,0.)),0.),90.);
  float grazing=pow(1.-max(V.y,0.),3.);
  vec3 wet=color*mix(1.,.6,damp);
  wet=mix(wet,vec3(.55,.62,.68),film*(.10+.25*grazing));
  wet+=vec3(1.,.9,.7)*sheen*(damp*.12+film*.45);
  return wet;
}
''' + END + '\n'


def patch(text):
    text = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n', '', text, flags=re.S)
    call = '    color.rgb=beachWetSand(color.rgb,arena_world);   // plage de Spargus\n'
    text = text.replace(call, '')
    anchor = '    if (palace_material==4) color.a *= mix(.48,1.0,smoothstep(.36,.49,T0.a));\n'
    assert text.count(anchor) == 1, 'ancre du shader de terrain introuvable'
    text = text.replace(anchor, anchor + call)
    marker = '\nvoid main() {'
    assert text.count(marker) == 1
    return text.replace(marker, '\n' + block() + marker)


def main():
    for root in (R / 'data', R / 'engine-src'):
        path = root / REL
        path.write_text(patch(path.read_text()))
        print('patche :', path.relative_to(R))
    subprocess.run([sys.executable, str(R / 'sync_variant.py'), REL], check=True)


if __name__ == '__main__': main()
