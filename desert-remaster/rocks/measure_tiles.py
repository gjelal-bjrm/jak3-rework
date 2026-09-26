"""Echelle native des textures de roche (pour le plaquage selon le monde, PalaceMaterials::world_tile).

Pour chaque materiau : gradient des UV natifs par rapport au monde sur les flancs raides, moyenne ponderee par
l'aire -> metres par repetition en u et en v, axe vertical (0 : u, 1 : v) et sens. Imprime aussi l'etirement
natif (rapport des deux echelles, cisaillement) pour savoir si le plaquage d'origine etait deja tordu.
  python measure_tiles.py export1.json [export2.json ...]
"""
import json, sys, collections
import numpy as np

acc = collections.defaultdict(list)
for path in sys.argv[1:]:
    d = json.load(open(path)); F = d['faces'] if isinstance(d, dict) else d
    for f in F:
        if f.get('geom', 0) != 0: continue
        P = np.array([v['p'] for v in f['vertices']]); U = np.array([v['uv'] for v in f['vertices']])
        e1, e2 = P[1] - P[0], P[2] - P[0]; n = np.cross(e1, e2); a = np.linalg.norm(n) / 2
        if a < 1e-4: continue
        n /= 2 * a
        if abs(n[1]) > .6: continue                       # flancs seulement
        # gradient g (3x2) tel que duv = dP . g, dans le plan du triangle
        E = np.stack([e1, e2]); D = np.stack([U[1] - U[0], U[2] - U[0]])
        G = np.linalg.pinv(E) @ D                         # (3,2)
        acc[f['material']].append((a, G))
for mat, items in sorted(acc.items(), key=lambda kv: -sum(a for a, _ in kv[1])):
    A = np.array([a for a, _ in items]); G = np.array([g for _, g in items])
    gu, gv = G[:, :, 0], G[:, :, 1]
    vert_u = np.average(np.abs(gu[:, 1]), weights=A); vert_v = np.average(np.abs(gv[:, 1]), weights=A)
    axis = 0 if vert_u > vert_v else 1
    sign = np.sign(np.average((gu if axis == 0 else gv)[:, 1], weights=A)) or 1.0
    lu = np.linalg.norm(gu, axis=1); lv = np.linalg.norm(gv, axis=1)
    Tu = 1 / np.median(lu[lu > 1e-9]); Tv = 1 / np.median(lv[lv > 1e-9])
    ratio = np.median(np.maximum(lu, lv) / np.maximum(np.minimum(lu, lv), 1e-9))
    print(f'{mat:28s} aire {A.sum():10.0f} m2  u {Tu:6.1f} m  v {Tv:6.1f} m  axe vertical {"u" if axis == 0 else "v"}'
          f' sens {sign:+.0f}  etirement natif {ratio:4.2f}')
