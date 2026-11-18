"""Lampes des lieux fermes -> vraies sources de lumiere pour le moteur (InteriorLightsData.h).

  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" materials-v2/lights/build_lights.py

Pour chaque lieu (CONFIG) : les faces des textures lumineuses sont exportees du niveau avec leurs 8 couleurs de
l'heure du jour (palace_mesh_bridge --export-selected, option with_palettes), groupees par objet (exemplaire TIE),
et chaque groupe devient une source en forme de tube (axe principal du groupe) : extremites, epaisseur, portee,
couleur, et intensite dans chacune des 8 palettes du jeu (le moteur les melange comme le jeu : les sources suivent
les pulsations et le chenillard d'origine).
Sortie : engine-src/game/graphics/opengl_renderer/InteriorLightsData.h (genere, compile dans le moteur).
"""
from pathlib import Path
import json, hashlib, subprocess, sys
from collections import defaultdict
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'engine-build/bin/Release/palace_mesh_bridge.exe'
OUT = ROOT / 'engine-src/game/graphics/opengl_renderer/InteriorLightsData.h'
WORK = Path(__file__).resolve().parent
# textures lumineuses : couleur de la lumiere emise (rvb, 0..1) et gain ; niveaux : ceux des familles de matieres v2
LAMPS = {'comb-temp-glass': ((.16, .42, 1.0), 1.0), 'comb-yell-light': ((1.0, .66, .16), 1.0)}
LEVEL_PREFIXES = ('comb', 'rail')


def config():
    inventory = json.loads((ROOT / 'remaster-build/textures-by-level.json').read_text())
    out = {}
    for level, textures in sorted(inventory.items()):
        names = {t[0] for t in textures} & set(LAMPS)
        if names and level.startswith(LEVEL_PREFIXES): out[level] = {n: LAMPS[n] for n in names}
    return out


def export(level, materials):
    src = ROOT / 'remaster-build/bases' / f'{level}.fr3'
    if not src.exists(): src = ROOT / 'data/out/jak3/fr3' / f'{level}.fr3'
    sel = WORK / f'sel-{level}.json'; out = WORK / f'{level}-lamps.json'
    sel.write_text(json.dumps({'level': level, 'source_fr3': {'path': str(src), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
                               'bytes': src.stat().st_size}, 'materials': sorted(materials), 'with_palettes': True}, indent=1))
    subprocess.run([str(BRIDGE), '--export-selected', str(src), str(sel), str(out)], check=True, capture_output=True)
    return json.loads(out.read_text())['faces']


def lights_of(level, spec):
    faces = [f for f in export(level, spec) if f['geom'] == 0 and f['tree_type'] in ('tie', 'tfrag')]
    groups = defaultdict(list)
    for f in faces: groups[(f['material'], f['tree_type'], f['tree'], f['instance'])].append(f)
    lights = []
    for (material, *_), fs in sorted(groups.items()):
        P = np.array([[v['p'] for v in f['vertices']] for f in fs])                    # faces x 3 x 3
        area = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1) / 2
        if area.sum() < .02: continue
        pal = np.array([[v.get('pal', [128] * 24) for v in f['vertices']] for f in fs], float).reshape(len(fs), 3, 8, 3)
        pal = (pal.mean(1) * area[:, None, None]).sum(0) / area.sum()               # 8 x 3
        pts = P.reshape(-1, 3); w = np.repeat(area / 3, 3)
        c = (pts * w[:, None]).sum(0) / w.sum()
        cov = ((pts - c) * w[:, None]).T @ (pts - c) / w.sum()
        val, vec = np.linalg.eigh(cov)
        axis = vec[:, 2]; t = (pts - c) @ axis
        half = (t.max() - t.min()) / 2; mid = c + axis * (t.max() + t.min()) / 2
        side = float(np.sqrt(max(val[1], 1e-6)) * 1.7)                                   # demi-largeur de l'emetteur
        tube = max(half - side, 0.)                                                      # demi-longueur du tube
        colour, gain = spec[material]
        power = float(area.sum()) * gain                                                 # ~ aire emettrice (une face visible)
        radius = float(np.clip(4.5 * np.sqrt(power) + 3., 4., 16.))
        lights.append({'a': mid - axis * tube, 'b': mid + axis * tube, 'size': max(side, .08), 'radius': radius,
                       'power': power, 'colour': colour, 'pal': pal.mean(1), 'material': material})
    return lights


def main():
    lines = ['// GENERE par materials-v2/lights/build_lights.py : ne pas modifier a la main.',
             '// Sources de lumiere des lieux fermes : tubes (a, b), demi-epaisseur, portee, puissance, couleur, et',
             "// intensite du sommet dans chacune des 8 palettes de l'heure du jour (0..255).",
             '#pragma once', '',
             'struct InteriorLightData { float a[3], b[3], size, radius, power, colour[3]; unsigned char pal[8]; };', '']
    table = []
    for level, spec in config().items():
        lights = lights_of(level, spec)
        if not lights: continue
        lines.append(f'inline const InteriorLightData kInteriorLights_{level}[] = {{')
        for l in lights:
            f3 = lambda v: '{' + ', '.join(f'{x:.2f}f' for x in v) + '}'
            lines.append(f"  {{{f3(l['a'])}, {f3(l['b'])}, {l['size']:.2f}f, {l['radius']:.1f}f, {l['power']:.3f}f, {f3(l['colour'])}, "
                         f"{{{', '.join(str(int(round(min(x, 255)))) for x in l['pal'])}}}}},")
        lines.append('};')
        table.append((level, len(lights)))
        by = defaultdict(int)
        for l in lights: by[l['material']] += 1
        print(level, len(lights), 'sources', dict(by))
    lines += ['', 'struct InteriorLightSet { const char* level; const InteriorLightData* lights; int count; };',
              'inline const InteriorLightSet kInteriorLightSets[] = {']
    lines += [f'  {{"{level}", kInteriorLights_{level}, {n}}},' for level, n in table]
    lines += ['};', '']
    OUT.write_text('\n'.join(lines), encoding='utf-8')
    print('ecrit :', OUT)


if __name__ == '__main__': main()
