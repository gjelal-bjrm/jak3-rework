"""Tables de la cote de Spargus pour les vagues de bord et les eclaboussures sur rochers.

Lit models-v2/shore/waterline.json (ligne d'eau du sable, tracee a y = 9 m dans le WCB natif par
l'analyse de beach-native.json) et les emetteurs natifs group-part-water-rocks-splash du niveau,
puis ecrit :
- shore_tables.glsl : polyligne de la plage (metres, plan xz) pour ocean_swell.glsl ;
- CoastSplashSites.h : sites d'eclaboussure (position, axe le long du rocher, direction vers le large).
Aucune donnee du jeu n'est copiee : seulement des coordonnees.
"""
from pathlib import Path
import json, math
H = Path(__file__).resolve().parent; R = H.parents[1]
ACTORS = R / 'city-remaster/staging/market-block-001/project/decompiler_out/jak3/entities/wascityb-actors.json'


def simplify(pts, tol):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dmax = 0; idx = 0
    for i in range(1, len(pts) - 1):
        p = pts[i]; ab = (b[0] - a[0], b[1] - a[1]); ap = (p[0] - a[0], p[1] - a[1]); L = math.hypot(*ab) or 1e-9
        d = abs(ab[0] * ap[1] - ab[1] * ap[0]) / L
        if d > dmax: dmax = d; idx = i
    if dmax > tol: return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [a, b]


def main():
    water = json.loads((H / 'waterline.json').read_text())
    chains = [c for c in water['chains'] if len(c) >= 3]
    # Plage : les deux troncons (ouest en diagonale, est le long de z ~ -425) forment une seule ligne
    chains.sort(key=lambda c: min(p[0] for p in c))
    pts = []
    for c in chains[:2]:
        c = c if c[0][0] <= c[-1][0] else c[::-1]
        pts.extend(simplify(c, 1.2))
    pts = [pts[0]] + [p for i, p in enumerate(pts[1:], 1) if math.dist(p, pts[i - 1]) > .5]
    # Ligne retenue (releve ci-dessus garde dans waterline.json) : la petite crique derriere les rochers de
    # (1494..1519, -434..-422) est ignoree, le trait suit le sable d'ouest en est. Terre = cote gauche
    # (produit vectoriel positif) pour un trait parcouru dans cet ordre.
    pts = [(1458.3, -513.0), (1473.1, -502.3), (1491.3, -495.1), (1501.8, -484.5), (1523.4, -426.8),
           (1532.0, -425.0), (1545.0, -429.0), (1556.0, -431.0), (1575.0, -425.5), (1582.0, -419.2)]
    segs = json.loads((H / 'waterline-segments.json').read_text())
    rocks = [s for s in segs if 'rocks' in s['material']]
    sites = []
    for a in json.loads(ACTORS.read_text()):
        if a.get('etype') != 'part-spawner' or a['lump'].get('art-name') != 'group-part-water-rocks-splash': continue
        x, y, z = a['trans'][:3]
        best = None
        for s in rocks:
            (ax, az), (bx, bz) = s['a'], s['b']
            ux, uz = bx - ax, bz - az; L2 = ux * ux + uz * uz or 1e-9
            t = max(0., min(1., ((x - ax) * ux + (z - az) * uz) / L2)); px, pz = ax + t * ux, az + t * uz
            d = math.hypot(x - px, z - pz)
            if best is None or d < best[0]: best = (d, px, pz, ux / math.sqrt(L2), uz / math.sqrt(L2))
        if best is None or best[0] > 25: continue
        d, px, pz, tx, tz = best
        sx, sz = x - px, z - pz            # du rocher vers le site : cote eau
        if math.hypot(sx, sz) < .4: sx, sz = 1560 - x, -470 - z
        L = math.hypot(sx, sz); sx, sz = sx / L, sz / L
        if sx * (-tz) + sz * tx < 0: tx, tz = -tx, -tz   # tangente orientee : (tangente x normale) coherent
        sites.append({'name': a['lump']['name'], 'x': round(x, 2), 'y': round(y, 2), 'z': round(z, 2),
                      'rock_distance': round(d, 2), 'tangent': [round(tx, 4), round(tz, 4)], 'seaward': [round(sx, 4), round(sz, 4)]})
    sites.sort(key=lambda s: s['name'])
    glsl = '// Genere par models-v2/shore/build_shore_tables.py : ligne d eau du sable de la plage de Spargus (y = 9 m).\n'
    glsl += f'const int shorePointCount={len(pts)};\n'
    glsl += 'const vec2 shorePoints[' + str(len(pts)) + ']=vec2[' + str(len(pts)) + '](' + ','.join(f'vec2({p[0]:.1f},{p[1]:.1f})' for p in pts) + ');\n'
    (H / 'shore_tables.glsl').write_text(glsl)
    header = '#pragma once\n// Genere par models-v2/shore/build_shore_tables.py : sites natifs d eclaboussure sur les rochers de Spargus.\n'
    header += '// x, y, z (m) ; tangente du rocher (xz) ; direction vers le large (xz).\n'
    header += 'struct CoastSplashSite { float x, y, z, tx, tz, sx, sz; };\n'
    header += f'inline constexpr int COAST_SPLASH_SITE_COUNT = {len(sites)};\n'
    header += 'inline constexpr CoastSplashSite COAST_SPLASH_SITES[' + str(len(sites)) + '] = {\n'
    header += ''.join(f"  {{{s['x']:.2f}f, {s['y']:.2f}f, {s['z']:.2f}f, {s['tangent'][0]:.4f}f, {s['tangent'][1]:.4f}f, {s['seaward'][0]:.4f}f, {s['seaward'][1]:.4f}f}},  // {s['name']}\n" for s in sites)
    header += '};\n'
    (H / 'CoastSplashSites.h').write_text(header)
    (R / 'engine-src/game/graphics/opengl_renderer/ocean/CoastSplashSites.h').write_text(header)
    (H / 'shore-tables.json').write_text(json.dumps({'beach_waterline': pts, 'splash_sites': sites}, indent=2))
    print(f'plage : {len(pts)} points ; sites : {len(sites)}')
    for p in pts: print('  ', round(p[0], 1), round(p[1], 1))
    for s in sites: print('  ', s['name'], s['x'], s['z'], 'rocher a', s['rock_distance'], 'm')


if __name__ == '__main__': main()
