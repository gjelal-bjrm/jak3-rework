"""Falaises de l'arene de Spargus : les blocs de gres (TIE, 20 prototypes, ~340 exemplaires) remodeles.

Lancement : blender.exe --background --python arena-remaster/rocks/remodel_rocks.py -- [apercu 3 4 ...]
  sans argument : tous les prototypes -> rocks-patch.json (+ rocks-report.json) ;
  apercu N ... : seulement ces prototypes, rendus avant/apres dans preview/ (pas de patch).

Chaque prototype est remodele une seule fois (sur son premier exemplaire), puis reporte sur tous ses
exemplaires par leur transformation exacte (affine, mesuree sommet a sommet). Niveau de detail 0 seulement :
OpenGOAL dessine toujours le niveau 0 des TIE (lod_tie = 0) ; les niveaux 1 a 3 restent d'origine.

  1. nouveau maillage regulier (Delaunay contraint, face d'origine par face d'origine, aretes partagees
     decoupees de la meme facon des deux cotes) : fin pres des aretes vives, plus large sur les grands plans ;
  2. aretes vives arrondies : chaque point descend vers le centre de gravite gaussien de la surface
     d'origine qui l'entoure (le long de la normale lissee). Les plans ne bougent pas, les aretes deviennent
     des conges d'erosion ; calcul qui ne depend que de la position -> aucune fissure entre morceaux ;
  3. relief irregulier doux (bruit fractal) qui casse les grands plans et les silhouettes rectilignes ;
  4. sur les dessus ou l'on marche (selon l'orientation de chaque exemplaire), relief reduit et jamais
     au-dessus de la collision d'origine (l'arrondi, lui, reste entier : le reduire creait un rebord).
UV et couleurs (palettes de l'heure du jour) : exactement celles d'origine, par coordonnees barycentriques
dans la face native d'ou vient chaque triangle. Normales lissees recalculees par exemplaire.
"""
import sys, json, math
from pathlib import Path
from collections import defaultdict
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'models-v1'))
from blender_common import *
from mathutils.geometry import delaunay_2d_cdt
from mathutils.kdtree import KDTree
OUT = Path(__file__).resolve().parent

MATS = ('wstd-rockwall-01', 'wstd-small-rockwall-01')
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = [int(a) for a in args[1:]] if args[:1] == ['apercu'] else None

native = json.loads((OUT / 'rocks-native.json').read_text())
groups = defaultdict(list)
for f in native:
    if f['tree_type'] == 'tie' and f['geom'] == 0 and f['material'] in MATS:
        groups[(f['proto'], f['instance'])].append(f)
protos = defaultdict(list)
for (p, i), fs in sorted(groups.items()):
    protos[p].append((i, fs))


# ---------------------------------------------------------------- outils
def _hash(i, j, k):
    h = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(p):
    i = np.floor(p).astype(np.int64); f = p - i; u = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) * (u[:, 2] if dz else 1 - u[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return out * 2 - 1


def fbm(p, octaves=3):
    total, amp, norm = 0, 1.0, 0
    for o in range(octaves):
        total = total + amp * vnoise(p * (2 ** o) + o * 17.3); norm += amp; amp *= .5
    return total / norm


def segment_distance(points, A, B):
    """Distance de chaque point (n,3) au plus proche des segments (A,B) (m,3)."""
    out = np.full(len(points), 1e9)
    if len(A) == 0: return out
    AB = B - A; ab2 = np.maximum((AB * AB).sum(1), 1e-12)
    for k in range(0, len(points), 1024):
        P = points[k:k + 1024, None, :]
        t = np.clip(((P - A) * AB).sum(2) / ab2, 0, 1)
        out[k:k + 1024] = np.linalg.norm(P - (A + t[..., None] * AB), axis=2).min(1)
    return out


def vertex_normals(P, T):
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    N = np.zeros_like(P)
    for c in range(3): np.add.at(N, T[:, c], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def barycentric(p, A):
    u, v, w = A[1] - A[0], A[2] - A[0], p - A[0]
    aa, ab, bb, wa, wb = u @ u, u @ v, v @ v, w @ u, w @ v
    den = aa * bb - ab * ab
    if abs(den) < 1e-12: return np.array([1., 0., 0.])
    b = (bb * wa - ab * wb) / den; c = (aa * wb - ab * wa) / den
    return np.array([1 - b - c, b, c])


def in_triangle_2d(c, tri2):
    v0, v1 = tri2[1] - tri2[0], tri2[2] - tri2[0]; den = v0[0] * v1[1] - v0[1] * v1[0]
    w = c - tri2[0]
    b = (w[:, 0] * v1[1] - w[:, 1] * v1[0]) / den; g = (v0[0] * w[:, 1] - v0[1] * w[:, 0]) / den
    return (b >= 0) & (g >= 0) & (b + g <= 1)


def orient(F, NV):
    """Les triangles natifs (issus de bandes) ne sont pas tous tournes dans le meme sens : on les rend
    coherents de proche en proche, puis chaque morceau est tourne vers l'exterieur."""
    by_edge = defaultdict(list)
    for k, (_, ids) in enumerate(F):
        for a, b in ((0, 1), (1, 2), (2, 0)): by_edge[frozenset((ids[a], ids[b]))].append(k)
    flip = [None] * len(F); comps = []
    for start in range(len(F)):
        if flip[start] is not None: continue
        flip[start] = False; stack = [start]; comp = [start]
        while stack:
            k = stack.pop(); ids = F[k][1]
            if flip[k]: ids = [ids[0], ids[2], ids[1]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                nb = by_edge[frozenset((ids[a], ids[b]))]
                if len(nb) != 2: continue
                other = nb[0] if nb[1] == k else nb[1]
                if flip[other] is not None: continue
                o = F[other][1]
                same = any((o[x], o[(x + 1) % 3]) == (ids[a], ids[b]) for x in range(3))
                flip[other] = same            # meme sens de parcours de l'arete : a retourner
                stack.append(other); comp.append(other)
        comps.append(comp)
    out = [(index, [ids[0], ids[2], ids[1]] if flip[k] else list(ids)) for k, (index, ids) in enumerate(F)]
    for comp in comps:
        centre = np.mean([NV[out[k][1]].mean(0) for k in comp], 0)
        outward = 0.0
        for k in comp:
            q = NV[out[k][1]]
            outward += np.cross(q[1] - q[0], q[2] - q[0]) @ (q.mean(0) - centre)
        if outward < 0:
            for k in comp: out[k] = (out[k][0], [out[k][1][0], out[k][1][2], out[k][1][1]])
    return out


# ---------------------------------------------------------------- remodelage d'un prototype
def remodel(ref):
    """ref : faces natives (monde) du premier exemplaire. Renvoie la geometrie de reference."""
    pts = np.array([v['p'] for f in ref for v in f['vertices']])
    size = float((pts.max(0) - pts.min(0)).max())
    sigma = min(max(size * .03, .2), .85)            # largeur de l'arrondi
    h_fine = .85 * sigma
    h_coarse = min(max(size / 14, 3 * h_fine), 2.5)

    # sommets natifs soudes (1 cm), faces, aretes, aretes vives
    weld, NV, F, seen = {}, [], [], set()
    for index, f in enumerate(ref):
        ids = []
        for v in f['vertices']:
            key = tuple(round(x * 100) for x in v['p'])
            if key not in weld: weld[key] = len(NV); NV.append(v['p'])
            ids.append(weld[key])
        if len(set(ids)) < 3 or tuple(sorted(ids)) in seen: continue
        seen.add(tuple(sorted(ids))); F.append((index, ids))
    NV = np.array(NV, float)
    F = orient(F, NV)
    fn = {}
    for index, ids in F:
        n = np.cross(NV[ids[1]] - NV[ids[0]], NV[ids[2]] - NV[ids[0]]); fn[index] = n / max(np.linalg.norm(n), 1e-12)
    edges = defaultdict(list)
    for index, ids in F:
        for a, b in ((0, 1), (1, 2), (2, 0)): edges[tuple(sorted((ids[a], ids[b])))].append(index)
    crease = [e for e, fl in edges.items() if len(fl) != 2 or fn[fl[0]] @ fn[fl[1]] < math.cos(math.radians(30))]
    CA = NV[[e[0] for e in crease]] if crease else np.zeros((0, 3))
    CB = NV[[e[1] for e in crease]] if crease else np.zeros((0, 3))

    def sizing(points):
        d = segment_distance(np.atleast_2d(points), CA, CB)
        return h_fine + (h_coarse - h_fine) * np.clip((d - .5 * sigma) / (2.5 * sigma), 0, 1)

    # sommets : natifs, points d'aretes (partages par les deux faces), points interieurs
    vn_native = np.zeros_like(NV)
    for index, ids in F:
        for i in ids: vn_native[i] += fn[index]
    vn_native /= np.maximum(np.linalg.norm(vn_native, axis=1, keepdims=True), 1e-12)
    V = [NV[i] for i in range(len(NV))]; VN = [vn_native[i] for i in range(len(NV))]
    edge_points = {}
    for e, fl in edges.items():
        a, b = NV[e[0]], NV[e[1]]; length = np.linalg.norm(b - a)
        ts = np.linspace(0, 1, 65); density = length / sizing(a + ts[:, None] * (b - a))
        cdf = np.concatenate([[0], np.cumsum((density[1:] + density[:-1]) / 2 / 64)])
        n = max(1, int(round(cdf[-1])))
        inner = np.interp(np.arange(1, n) * cdf[-1] / n, cdf, ts) if n > 1 else []
        nref = sum(fn[x] for x in fl); nref = nref / max(np.linalg.norm(nref), 1e-12)
        edge_points[e] = []
        for t in inner:
            edge_points[e].append(len(V)); V.append(a + t * (b - a)); VN.append(nref)
    T, S = [], []
    rng = np.random.default_rng(7)
    for index, ids in F:
        A, B, C = NV[ids[0]], NV[ids[1]], NV[ids[2]]
        n = fn[index]; e1 = (B - A) / np.linalg.norm(B - A); e2 = np.cross(n, e1)
        to2 = lambda P: np.stack([(P - A) @ e1, (P - A) @ e2], -1)
        loop = []
        for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            pe = edge_points[tuple(sorted((a, b)))]
            loop += [a] + (pe if a < b else pe[::-1])
        tri2 = to2(np.array([A, B, C]))
        lo, hi = tri2.min(0), tri2.max(0)
        # candidats interieurs : grille hexagonale fine legerement agitee, tirage de Poisson a rayon variable
        cand = []
        for k, y in enumerate(np.arange(lo[1], hi[1], h_fine * .866)):
            xs = np.arange(lo[0] + (k % 2) * h_fine * .5, hi[0], h_fine)
            cand.append(np.stack([xs, np.full(len(xs), y)], -1))
        cand = np.concatenate(cand) if cand else np.zeros((0, 2))
        new_ids = []
        if len(cand):
            cand = cand + rng.uniform(-.15, .15, cand.shape) * h_fine
            cand = cand[in_triangle_2d(cand, tri2)]
        if len(cand):
            c3 = A + cand[:, :1] * e1 + cand[:, 1:] * e2
            hc = sizing(c3)
            bd = segment_distance(c3, np.array([A, B, C]), np.array([B, C, A]))
            cell = h_fine * .75; grid = defaultdict(list)
            for i in loop:
                q = to2(V[i]); grid[(int(q[0] // cell), int(q[1] // cell))].append(q)
            for k in np.argsort(hc, kind='stable'):
                if bd[k] < .5 * hc[k]: continue
                q = cand[k]; r = .8 * hc[k]; reach = int(r // cell) + 1
                cx, cy = int(q[0] // cell), int(q[1] // cell)
                if any((o[0] - q[0]) ** 2 + (o[1] - q[1]) ** 2 < r * r
                       for gx in range(cx - reach, cx + reach + 1) for gy in range(cy - reach, cy + reach + 1)
                       for o in grid.get((gx, gy), ())):
                    continue
                grid[(cx, cy)].append(q); new_ids.append(len(V)); V.append(c3[k]); VN.append(n)
        all_ids = loop + new_ids; nb = len(loop)
        coords = [tuple(to2(V[i])) for i in all_ids]
        out = delaunay_2d_cdt(coords, [(i, (i + 1) % nb) for i in range(nb)], [list(range(nb))], 1, 1e-7)
        of, orig_v = out[2], out[3]
        for tri in of:
            if len(tri) != 3 or any(not orig_v[t] for t in tri): continue
            g = [all_ids[orig_v[t][0]] for t in tri]
            if len(set(g)) < 3: continue
            if np.cross(V[g[1]] - V[g[0]], V[g[2]] - V[g[0]]) @ n < 0: g = [g[0], g[2], g[1]]
            T.append(g); S.append(index)
    P0 = np.array(V); VN = np.array(VN); T = np.array(T); S = np.array(S)

    # echantillons reguliers de la surface d'origine (poids = aire)
    spacing = sigma / 3
    SP, SN, SW = [], [], []
    for index, ids in F:
        A, B, C = NV[ids[0]], NV[ids[1]], NV[ids[2]]
        n = fn[index]; e1 = (B - A) / np.linalg.norm(B - A); e2 = np.cross(n, e1)
        tri2 = np.array([[0., 0.], [(B - A) @ e1, (B - A) @ e2], [(C - A) @ e1, (C - A) @ e2]])
        lo, hi = tri2.min(0), tri2.max(0)
        gx, gy = np.meshgrid(np.arange(lo[0] + spacing / 2, hi[0], spacing), np.arange(lo[1] + spacing / 2, hi[1], spacing))
        c = np.stack([gx.ravel(), gy.ravel()], -1)
        c = c[in_triangle_2d(c, tri2)] if len(c) else c
        if len(c) == 0: c = tri2.mean(0)[None]
        area = np.linalg.norm(np.cross(B - A, C - A)) / 2
        SP.append(A + c[:, :1] * e1 + c[:, 1:] * e2); SN.append(np.repeat(n[None], len(c), 0)); SW.append(np.full(len(c), area / len(c)))
    SP = np.concatenate(SP); SN = np.concatenate(SN); SW = np.concatenate(SW)
    tree = KDTree(len(SP))
    for i, q in enumerate(SP): tree.insert(q, i)
    tree.balance()
    # arrondi : centre de gravite gaussien de la surface voisine, projete sur la normale lissee
    R = np.zeros_like(P0); NF = VN.copy()
    for i, q in enumerate(P0):
        found = tree.find_range(q, 3 * sigma)
        if not found: continue
        idx = np.fromiter((x[1] for x in found), int, len(found))
        dist = np.fromiter((x[2] for x in found), float, len(found))
        w = np.exp(-dist ** 2 / (2 * sigma * sigma)) * SW[idx] * ((SN[idx] @ VN[i]) > -.5)
        if w.sum() <= 0: continue
        nf = (w[:, None] * SN[idx]).sum(0); nf /= max(np.linalg.norm(nf), 1e-12)
        c = (w[:, None] * SP[idx]).sum(0) / w.sum()
        NF[i] = nf; R[i] = ((c - q) @ nf) * nf
    cap = 1.0 * sigma
    length = np.linalg.norm(R, axis=1, keepdims=True); R = R * np.minimum(1, cap / np.maximum(length, 1e-9))
    # relief : grandes bosses douces (longueur d'onde que le maillage sait representer)
    amp = min(max(size * .012, .04), .35)
    wave = max(3 * h_coarse, size / 5)
    d = amp * fbm(P0 / wave, 2)

    # UV et poids de couleur par coin : barycentriques de la position d'origine (sur la face native)
    uv = np.zeros((len(T), 3, 2)); bary = np.zeros((len(T), 3, 3))
    for j, (tri, s) in enumerate(zip(T, S)):
        face = ref[s]; A = np.array([v['p'] for v in face['vertices']]); U = np.array([v['uv'] for v in face['vertices']])
        for c in range(3):
            w = barycentric(P0[tri[c]], A)
            bary[j, c] = w; uv[j, c] = w @ U
    return {'P0': P0, 'R': R, 'N': NF, 'd': d, 'T': T, 'S': S, 'uv': uv, 'bary': bary, 'size': size, 'L': h_coarse,
            'sigma': sigma, 'amp': amp, 'ref_points': pts}


def place(model, inst_faces):
    """Geometrie finale d'un exemplaire (monde) : transformation affine exacte + attenuation sur les dessus."""
    A = model['ref_points']; B = np.array([v['p'] for f in inst_faces for v in f['vertices']])
    ca, cb = A.mean(0), B.mean(0)
    M = np.linalg.lstsq(A - ca, B - cb, rcond=None)[0]
    err = np.abs((A - ca) @ M - (B - cb)).max()
    if err > .05: raise RuntimeError(f'transformation non affine ({err:.3f} m)')
    nw = model['N'] @ np.linalg.inv(M).T                    # normales -> monde (inverse transposee)
    nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-12)
    walk = np.clip((nw[:, 1] - .55) / .3, 0, 1)             # dessus praticables de CET exemplaire
    d = model['d'] * (1 - .6 * walk)
    d = d * (1 - walk) + np.minimum(d, .03) * walk           # relief : pas au-dessus de la collision (continu)
    local = model['P0'] + model['R'] + model['N'] * d[:, None]
    W = (local - ca) @ M + cb
    # exemplaire en miroir : l'ordre des sommets s'inverse, pas l'exterieur
    return W, vertex_normals(W, model['T']) * np.sign(np.linalg.det(M)), err


def records(model, inst_faces, W, NW):
    remove = [{**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index')},
               'original_positions': [v['p'] for v in f['vertices']]} for f in inst_faces]
    add = []
    for j, (tri, s) in enumerate(zip(model['T'], model['S'])):
        face = inst_faces[s]
        rec = {k: face[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group')}; rec['vertices'] = []
        ci = [v['color'] for v in face['vertices']]
        for c in range(3):
            i = tri[c]
            rec['vertices'].append({'p': [round(float(x), 4) for x in W[i]],
                                    'uv': [round(float(x), 5) for x in model['uv'][j, c]],
                                    'normal': [round(float(x), 4) for x in NW[i]],
                                    'color_indices': ci,
                                    'color_weights': [round(float(x), 4) for x in model['bary'][j, c]]})
        add.append(rec)
    return remove, add


def blender_mesh(name, W, T, S, uv, ref):
    """Maillage Blender (materiaux et UV d'origine) pour les apercus."""
    mats = sorted({f['material'] for f in ref})
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(p[0], -p[2], p[1]) for p in W], [], [tuple(t) for t in T]); mesh.update()   # Blender : Z vers le haut
    for m in mats: mesh.materials.append(load_material(m, next(f['page'] for f in ref if f['material'] == m)))
    layer = mesh.uv_layers.new(name='UVMap')
    for poly, s, tri_uv in zip(mesh.polygons, S, uv):
        poly.material_index = mats.index(ref[s]['material']); poly.use_smooth = True
        for c, loop in enumerate(poly.loop_indices): layer.data[loop].uv = (tri_uv[c][0], 1 - tri_uv[c][1])
    obj = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj)
    return obj


patch = {'description': 'Arene : falaises (blocs de gres) aux aretes erodees et au relief irregulier', 'remove': [], 'add': []}
report = []
for p, lst in sorted(protos.items()):
    if PREVIEW is not None and p not in PREVIEW: continue
    ref = lst[0][1]
    model = remodel(ref)
    info = {'proto': p, 'instances': len(lst), 'size_m': round(model['size'], 1), 'edge_m': round(model['L'], 2),
            'round_sigma_m': round(model['sigma'], 2), 'relief_m': round(model['amp'], 2),
            'native_triangles': len(ref), 'new_triangles': int(len(model['T'])), 'max_affine_error_m': 0}
    print(f"proto {p}: {len(lst)} exemplaires, {len(ref)} -> {len(model['T'])} triangles "
          f"(aretes {model['L']:.2f} m, arrondi {model['sigma']:.2f} m)", flush=True)
    if PREVIEW is not None:
        reset()
        before = NativeMesh(f'natif{p}', ref)
        render_asset(before.obj, OUT / 'preview' / f'avant-proto{p:02d}.png', view=(4, -7, 3), resolution=600)
        W, NW, _ = place(model, ref)
        np.savez(OUT / 'preview' / f'debug-proto{p:02d}.npz', P0=model['P0'], R=model['R'], N=model['N'], d=model['d'], T=model['T'], S=model['S'], W=W)
        after = blender_mesh(f'nouveau{p}', W, model['T'], model['S'], model['uv'], ref)
        render_asset(after, OUT / 'preview' / f'apres-proto{p:02d}.png', view=(4, -7, 3), resolution=600)
        continue
    for instance, fs in lst:
        W, NW, err = place(model, fs)
        info['max_affine_error_m'] = max(info['max_affine_error_m'], round(float(err), 4))
        remove, add = records(model, fs, W, NW)
        patch['remove'].extend(remove); patch['add'].extend(add)
    report.append(info)

if PREVIEW is None:
    (OUT / 'rocks-patch.json').write_text(json.dumps(patch, separators=(',', ':')))
    (OUT / 'rocks-report.json').write_text(json.dumps(report, indent=2))
    print('Enregistre :', len(patch['remove']), 'retires ->', len(patch['add']), 'ajoutes', flush=True)
