"""Falaises de l'arene de Spargus, version 2 : gres sculpte en strates (TIE, 20 prototypes, ~340 exemplaires).

Lancement : blender.exe --background --python arena-remaster/rocks/remodel_rocks.py -- [mode]
  (aucun)                 : tous les exemplaires -> rocks-patch.json (+ rocks-report.json) ;
  apercu X Z R            : exemplaires a moins de R m de (X, Z) ; rendus avant/apres depuis le point de vue du
                            joueur dans preview/ (pas de patch) ;
  partiel X Z R           : patch limite a ces exemplaires (essai en jeu rapide).

La version 1 (arrondi seul) ne se voyait presque pas a distance de jeu. Ici, la roche est vraiment sculptee :
  - STRATES HORIZONTALES DU MONDE, continues d'un bloc a l'autre (comme une vraie falaise de gres) : couches de
    1 a 2,8 m (bancs massifs de 3,5 a 6 m), legerement ondulees, un quart de couches dures presque a fleur ;
    chaque couche = corniche dure qui affleure en haut,
    creux sous la corniche, pente erodee vers le bas. Profondeur 0,3 a 1,3 m, variable le long de la falaise ;
  - la roche ne sort jamais de la surface d'origine (seulement creusee) : la collision reste juste ;
  - dessus praticables : pas de strates (seulement l'arrondi des rebords) ;
  - aretes vives arrondies (centre de gravite gaussien de la surface d'origine, calcule par prototype) ;
  - maillage par exemplaire (les strates dependent de sa position dans le monde) : rangees de sommets posees
    exactement sur les ruptures de pente des strates, plus fines pres de l'arene, plus larges au loin.
UV et couleurs (palettes de l'heure du jour) : exactement celles d'origine (barycentriques dans la face native).
Niveau de detail 0 seulement : OpenGOAL dessine toujours le niveau 0 des TIE.
"""
import sys, json, math, time
from pathlib import Path
from collections import defaultdict
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'models-v1'))
from blender_common import *
from mathutils.geometry import delaunay_2d_cdt
from mathutils.kdtree import KDTree
OUT = Path(__file__).resolve().parent

# Reglages du lieu : arene par defaut ; autre lieu : premier argument apres -- = fichier de reglages JSON
# {native, materials, centre [x, z], near (m), strata_top (m), patch, report, preview_prefix}
# options d'echelle (grands lieux, ex. desert) : strata_scale, depth_scale, depth_max (m), sigma_max (m, arrondi),
# far_spacing (x espacement du maillage loin du centre : moins de triangles)
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CONFIG = {'native': str(OUT / 'rocks-native.json'), 'materials': ['wstd-rockwall-01', 'wstd-small-rockwall-01'],
          'centre': [2275.0, -450.0], 'near': 100.0, 'strata_top': 240.0,
          'patch': str(OUT / 'rocks-patch.json'), 'report': str(OUT / 'rocks-report.json'), 'preview_prefix': 'v2'}
if args and args[0].endswith('.json'):
    CONFIG.update(json.loads(Path(args[0]).read_text())); args = args[1:]
MATS = tuple(CONFIG['materials'])
ARENA = np.array(CONFIG['centre'])           # centre du lieu (x, z)
NEAR = float(CONFIG['near'])                 # exemplaires plus proches : strates plus fines
MODE = args[0] if args else 'tout'
STYLE = CONFIG.get('style', 'strates')        # 'strates' (gres en couches) ou 'lave' (roche volcanique : bosses, fissures)
if MODE in ('apercu', 'partiel'):
    FOCUS = np.array([float(args[1]), float(args[2])]); RADIUS = float(args[3])

native = json.loads(Path(CONFIG['native']).read_text())
if isinstance(native, dict): native = native['faces']
groups = defaultdict(list)
for f in native:
    if f['geom'] == 0 and f['material'] in MATS and f['tree_type'] in ('tie', 'tfrag'):
        groups[(f['tree_type'], f['tree'], f['proto'], f['instance'])].append(f)
protos = defaultdict(list)
for (tt, tree, p, i), fs in sorted(groups.items()):
    protos[(tt, tree, p)].append((i, fs))


# ---------------------------------------------------------------- outils
def _hash(i, j, k):
    h = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def hash01(k):
    return float(_hash(np.int64(k), np.int64(7), np.int64(11)))


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


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def segment_distance(points, A, B):
    """Distance de chaque point (n,3) au plus proche des segments (A,B) (m,3)."""
    out = np.full(len(points), 1e9)
    if len(A) == 0 or len(points) == 0: return out
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


def weld_orient(faces):
    """Sommets soudes (1 cm), faces (index natif, ids) orientees vers l'exterieur, normales des faces."""
    weld, NV, F, seen = {}, [], [], set()
    for index, f in enumerate(faces):
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
    return NV, F, fn


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
                flip[other] = any((o[x], o[(x + 1) % 3]) == (ids[a], ids[b]) for x in range(3))
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


# ---------------------------------------------------------------- strates (coordonnees du monde)
BOUNDS, CAP, DEPTH = [-40.0], [], []
k = 0
while BOUNDS[-1] < CONFIG['strata_top']:
    T_ = (1.0 + 1.8 * hash01(k) ** 1.5) * CONFIG.get('strata_scale', 1.0)
    if hash01(k + 1000) > .82: T_ = (3.5 + 2.5 * hash01(k + 2000)) * CONFIG.get('strata_scale', 1.0)   # banc massif
    hard = hash01(k + 5000) < .25                                        # couche dure : presque a fleur
    BOUNDS.append(BOUNDS[-1] + T_); CAP.append(.14 + .22 * hash01(k + 3000))
    DEPTH.append(.08 + .12 * hash01(k + 4000) if hard else .45 + .55 * hash01(k + 4000))
    k += 1
BOUNDS = np.array(BOUNDS); CAP = np.array(CAP); DEPTH = np.array(DEPTH); THICK = np.diff(BOUNDS)


def warp(P):
    """Hauteur 'geologique' : y du monde, couches legerement ondulees."""
    q = np.c_[P[:, 0] / 30, np.full(len(P), 5.), P[:, 2] / 30]
    r = np.c_[P[:, 0] / 7, np.full(len(P), 9.), P[:, 2] / 7]
    return P[:, 1] + .55 * fbm(q, 2) + .15 * fbm(r, 2)


def row_levels(near):
    """Hauteurs (en coordonnee 'warp') des rangees de sommets : ruptures de pente de chaque couche."""
    lv = []
    for k in range(len(THICK)):
        c = CAP[k]
        ts = [0, .18, .45, 1 - c - .07, 1 - c - .035, 1 - c + .005] if near else [0, .45, 1 - c - .06, 1 - c + .01]
        lv += [BOUNDS[k] + t * THICK[k] for t in ts]
    return np.array(sorted(lv))


LEVELS = {True: row_levels(True), False: row_levels(False)}


def strata_depth(P, dmax):
    """Profondeur (m, vers l'interieur) de la sculpture en strates au point P (monde)."""
    w = warp(P)
    k = np.clip(np.searchsorted(BOUNDS, w, 'right') - 1, 0, len(THICK) - 1)
    t = (w - BOUNDS[k]) / THICK[k]; c = CAP[k]
    under = 1 - smoothstep(1 - c - .05, 1 - c + .005, t)          # corniche dure en haut de la couche
    slope = smoothstep(0, .45, t) ** .8                           # pente erodee vers le bas
    q = np.c_[P[:, 0] / 9, k * 3.7, P[:, 2] / 9]
    along = np.clip(.55 + 1.1 * fbm(q, 2), .1, 1)                 # usure variable le long de la falaise
    return dmax * DEPTH[k] * along * under * slope


def crossings(P, levels):
    """Parametres s (0..1) ou le segment echantillonne P (n,3) traverse les niveaux."""
    if len(P) < 2: return []
    w = warp(P); idx = np.searchsorted(levels, w)
    out = []
    for i in np.nonzero(idx[1:] != idx[:-1])[0]:
        lo, hi = sorted((idx[i], idx[i + 1]))
        for L in levels[lo:hi]:
            a = (L - w[i]) / (w[i + 1] - w[i]) if w[i + 1] != w[i] else .5
            out.append((i + a) / (len(P) - 1))
    return out


def lava_depth(P, dmax):
    """Roche volcanique : grosses bosses arrondies et fissures profondes (bruit « a cretes »), vers l'interieur."""
    s = CONFIG.get('lava_scale', 1.0)
    lumps = (fbm(P / (7.0 * s), 3) + 1) * .5
    ridge = 1 - np.abs(vnoise(P / (3.2 * s) + 11.3))
    ridge2 = 1 - np.abs(vnoise(P / (1.4 * s) + 4.1))
    cracks = smoothstep(.86, .985, ridge) + .45 * smoothstep(.9, .99, ridge2)
    return dmax * np.clip(.45 * lumps ** 1.4 + .8 * cracks, 0, 1.2)


# ---------------------------------------------------------------- arrondi (champ par prototype, repere de reference)
def build_field(ref):
    pts = np.array([v['p'] for f in ref for v in f['vertices']])
    size = float((pts.max(0) - pts.min(0)).max())
    sigma = min(max(size * .03, .2), CONFIG.get('sigma_max', .85))
    NV, F, fn = weld_orient(ref)
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
    return {'pts': pts, 'size': size, 'sigma': sigma, 'tree': tree, 'SP': SP, 'SN': SN, 'SW': SW}


def field_eval(field, Q, VN):
    """Deplacement d'arrondi R et normale lissee NF aux points Q (repere de reference)."""
    sigma = field['sigma']; SP, SN, SW = field['SP'], field['SN'], field['SW']
    R = np.zeros_like(Q); NF = VN.copy()
    for i, q in enumerate(Q):
        found = field['tree'].find_range(q, 3 * sigma)
        if not found: continue
        idx = np.fromiter((x[1] for x in found), int, len(found))
        dist = np.fromiter((x[2] for x in found), float, len(found))
        w = np.exp(-dist ** 2 / (2 * sigma * sigma)) * SW[idx] * ((SN[idx] @ VN[i]) > -.5)
        if w.sum() <= 0: continue
        nf = (w[:, None] * SN[idx]).sum(0); nf /= max(np.linalg.norm(nf), 1e-12)
        c = (w[:, None] * SP[idx]).sum(0) / w.sum()
        NF[i] = nf; R[i] = ((c - q) @ nf) * nf
    length = np.linalg.norm(R, axis=1, keepdims=True)
    return R * np.minimum(1, sigma / np.maximum(length, 1e-9)), NF


# ---------------------------------------------------------------- maillage d'un exemplaire (monde)
def mesh_instance(faces, near, sigma):
    NV, F, fn = weld_orient(faces)
    levels = LEVELS[near]
    FS = 1.0 if near else CONFIG.get('far_spacing', 1.0)
    hx = 1.0 if near else 1.8 * FS
    h_fine, h_coarse = .85 * sigma, (2.0 if near else 3.0 * FS)
    steep = {index: abs(n[1]) < .8 and STYLE == 'strates' for index, n in fn.items()}
    edges = defaultdict(list)
    for index, ids in F:
        for a, b in ((0, 1), (1, 2), (2, 0)): edges[tuple(sorted((ids[a], ids[b])))].append(index)
    crease = [e for e, fl in edges.items() if len(fl) != 2 or fn[fl[0]] @ fn[fl[1]] < math.cos(math.radians(30))]
    CA = NV[[e[0] for e in crease]] if crease else np.zeros((0, 3))
    CB = NV[[e[1] for e in crease]] if crease else np.zeros((0, 3))

    def sizing(points):
        d = segment_distance(np.atleast_2d(points), CA, CB)
        return h_fine + (h_coarse - h_fine) * np.clip((d - .5 * sigma) / (2.5 * sigma), 0, 1)

    vn_native = np.zeros_like(NV)
    for index, ids in F:
        for i in ids: vn_native[i] += fn[index]
    vn_native /= np.maximum(np.linalg.norm(vn_native, axis=1, keepdims=True), 1e-12)
    V = [NV[i] for i in range(len(NV))]; VN = [vn_native[i] for i in range(len(NV))]
    edge_points = {}
    for e, fl in edges.items():
        a, b = NV[e[0]], NV[e[1]]; length = float(np.linalg.norm(b - a))
        n_s = max(2, int(math.ceil(length / .02)) + 1); s = np.linspace(0, 1, n_s); P = a + s[:, None] * (b - a)
        if any(steep[x] for x in fl):
            ss = sorted(crossings(P, levels))
            gap = hx
        else:
            ss = []; gap = None
        # complement : pas plus de 'gap' (aretes des strates) ou taille selon les aretes vives (dessus)
        pts = [0.0] + [x for x in ss if .02 / max(length, 1e-9) < x < 1 - .02 / max(length, 1e-9)] + [1.0]
        filled = []
        for x0, x1 in zip(pts, pts[1:]):
            seg = (x1 - x0) * length
            g = gap if gap else float(sizing((a + (b - a) * (x0 + x1) / 2)[None])[0])
            m = int(math.ceil(seg / g)) if seg > g else 1
            filled += [x0 + (x1 - x0) * j / m for j in range(m)]
        filled = filled[1:]
        clean = []
        for x in filled:
            if not clean or (x - clean[-1]) * length > .03: clean.append(x)
        nref = sum(fn[x] for x in fl); nref = nref / max(np.linalg.norm(nref), 1e-12)
        edge_points[e] = []
        for x in clean:
            edge_points[e].append(len(V)); V.append(a + x * (b - a)); VN.append(nref)

    T, S = [], []
    rng = np.random.default_rng(7)
    up = np.array([0., 1., 0.])
    for index, ids in F:
        A, B, C = NV[ids[0]], NV[ids[1]], NV[ids[2]]; n = fn[index]
        loop = []
        for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            pe = edge_points[tuple(sorted((a, b)))]
            loop += [a] + (pe if a < b else pe[::-1])
        new_ids = []
        if steep[index]:
            e1 = np.cross(up, n); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
            if e2[1] < 0: e2 = -e2
            to2 = lambda P: np.stack([(P - A) @ e1, (P - A) @ e2], -1)
            tri2 = to2(np.array([A, B, C])); lo, hi = tri2.min(0), tri2.max(0)
            margin = .12 if near else .25 * FS
            cand = []
            for u in np.arange(lo[0] + hx / 2, hi[0], hx):
                # intervalle vertical de la colonne u dans le triangle
                vs = []
                for p, q in ((tri2[0], tri2[1]), (tri2[1], tri2[2]), (tri2[2], tri2[0])):
                    if (p[0] - u) * (q[0] - u) <= 0 and p[0] != q[0]:
                        vs.append(p[1] + (q[1] - p[1]) * (u - p[0]) / (q[0] - p[0]))
                if len(vs) < 2: continue
                v0, v1 = min(vs), max(vs)
                if v1 - v0 < 2 * margin: continue
                m = max(2, int(math.ceil((v1 - v0) / .02)) + 1); vv = np.linspace(v0, v1, m)
                Pc = A + u * e1 + vv[:, None] * e2
                ss = crossings(Pc, levels)
                rows = sorted(v0 + x * (v1 - v0) for x in ss)
                full = [v0] + rows + [v1]; pts = []
                for r0, r1 in zip(full, full[1:]):
                    k = int(math.ceil((r1 - r0) / (.6 if near else 1.2 * FS)))
                    pts += [r0 + (r1 - r0) * j / k for j in range(k)]
                pts = pts[1:]
                cand += [(u, v) for v in pts if v0 + margin < v < v1 - margin]
            cand = np.array(cand) if cand else np.zeros((0, 2))
            aniso = .35 if near else .4
        else:
            e1 = (B - A) / np.linalg.norm(B - A); e2 = np.cross(n, e1)
            to2 = lambda P: np.stack([(P - A) @ e1, (P - A) @ e2], -1)
            tri2 = to2(np.array([A, B, C])); lo, hi = tri2.min(0), tri2.max(0)
            cand = []
            for k, y in enumerate(np.arange(lo[1], hi[1], h_fine * .866)):
                xs = np.arange(lo[0] + (k % 2) * h_fine * .5, hi[0], h_fine)
                cand.append(np.stack([xs, np.full(len(xs), y)], -1))
            cand = np.concatenate(cand) if cand else np.zeros((0, 2))
            if len(cand): cand = cand + rng.uniform(-.15, .15, cand.shape) * h_fine
            aniso = 1.0
        if len(cand):
            cand = cand[in_triangle_2d(cand, tri2)]
        if len(cand):
            c3 = A + cand[:, :1] * e1 + cand[:, 1:] * e2
            if steep[index]:
                bd = segment_distance(c3, np.array([A, B, C]), np.array([B, C, A]))
                for k in np.nonzero(bd > margin)[0]:
                    new_ids.append(len(V)); V.append(c3[k]); VN.append(n)
            else:
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
        coords = [(float(q[0]) * aniso, float(q[1])) for q in (to2(V[i]) for i in all_ids)]
        out = delaunay_2d_cdt(coords, [(i, (i + 1) % nb) for i in range(nb)], [list(range(nb))], 1, 1e-7)
        of, orig_v = out[2], out[3]
        for tri in of:
            if len(tri) != 3 or any(not orig_v[t] for t in tri): continue
            g = [all_ids[orig_v[t][0]] for t in tri]
            if len(set(g)) < 3: continue
            if np.cross(V[g[1]] - V[g[0]], V[g[2]] - V[g[0]]) @ n < 0: g = [g[0], g[2], g[1]]
            T.append(g); S.append(index)
    P0 = np.array(V); VN = np.array(VN); T = np.array(T); S = np.array(S)
    uv = np.zeros((len(T), 3, 2)); bary = np.zeros((len(T), 3, 3))
    for j, (tri, s) in enumerate(zip(T, S)):
        face = faces[s]; A = np.array([v['p'] for v in face['vertices']]); U = np.array([v['uv'] for v in face['vertices']])
        for c in range(3):
            w = barycentric(P0[tri[c]], A); bary[j, c] = w; uv[j, c] = w @ U
    return P0, VN, T, S, uv, bary


def sculpt(field, faces, near):
    """Exemplaire final : maillage, arrondi (champ du prototype), strates du monde."""
    A = field['pts']; B = np.array([v['p'] for f in faces for v in f['vertices']])
    ca, cb = A.mean(0), B.mean(0)
    M = np.linalg.lstsq(A - ca, B - cb, rcond=None)[0]
    err = float(np.abs((A - ca) @ M - (B - cb)).max())
    if err > .05: raise RuntimeError(f'transformation non affine ({err:.3f} m)')
    Minv = np.linalg.inv(M)
    P0, VN, T, S, uv, bary = mesh_instance(faces, near, field['sigma'])
    Q = (P0 - cb) @ Minv + ca                                      # -> repere du prototype
    VNr = VN @ M.T; VNr /= np.maximum(np.linalg.norm(VNr, axis=1, keepdims=True), 1e-12)
    R, NF = field_eval(field, Q, VNr)
    R = R @ M                                                      # vecteurs -> monde
    N = NF @ Minv.T; N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    steepw = 1 - smoothstep(.5, .78, np.abs(N[:, 1]))
    dmax = min(.85 if near else CONFIG.get('depth_max', 1.25), .08 * field['size']) * CONFIG.get('depth_scale', 1.0)
    if 'thin_ratio' in CONFIG:
        # aiguilles et lames : creuser au plus une fraction de leur epaisseur (sinon cous etrangles, piles d'assiettes)
        H = B[:, [0, 2]] - B[:, [0, 2]].mean(0)
        axis = np.linalg.eigh(H.T @ H)[1][:, 0]
        minor = float(np.ptp(H @ axis))
        dmax = min(dmax, CONFIG['thin_ratio'] * minor)
    depth = strata_depth(P0, dmax) * steepw if STYLE == 'strates' else lava_depth(P0, dmax) * (.35 + .65 * steepw)
    walk = np.clip((N[:, 1] - .55) / .3, 0, 1)
    bump = min(max(field['size'] * .008, .03), .2) * fbm(P0 / max(6., field['size'] / 5), 2) * (1 - walk)
    bump = np.minimum(bump, 0) + np.maximum(bump, 0) * (1 - walk)
    W = P0 + R + N * (bump - depth)[:, None]
    return W, vertex_normals(W, T), T, S, uv, bary, err


def records(faces, W, NW, T, S, uv, bary):
    remove = [{**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index')},
               'original_positions': [v['p'] for v in f['vertices']]} for f in faces]
    add = []
    for j, (tri, s) in enumerate(zip(T, S)):
        face = faces[s]
        rec = {k: face[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group')}; rec['vertices'] = []
        ci = [v['color'] for v in face['vertices']]
        for c in range(3):
            i = tri[c]
            rec['vertices'].append({'p': [round(float(x), 3) for x in W[i]],
                                    'uv': [round(float(x), 4) for x in uv[j, c]],
                                    'normal': [round(float(x), 3) for x in NW[i]],
                                    'color_indices': ci,
                                    'color_weights': [round(float(x), 4) for x in bary[j, c]]})
        add.append(rec)
    return remove, add


# ---------------------------------------------------------------- apercu (point de vue du joueur)
def preview_scene(items, name):
    reset()
    mats = {}
    for label, W, T, S, uv, faces in items:
        names = sorted({f['material'] for f in faces})
        mesh = bpy.data.meshes.new(label)
        mesh.from_pydata([(p[0], -p[2], p[1]) for p in W], [], [tuple(t) for t in T]); mesh.update()
        for m in names:
            if m not in mats: mats[m] = load_material(m, next(f['page'] for f in faces if f['material'] == m))
            mesh.materials.append(mats[m])
        layer = mesh.uv_layers.new(name='UVMap')
        for poly, s, tri_uv in zip(mesh.polygons, S, uv):
            poly.material_index = names.index(faces[s]['material']); poly.use_smooth = True
            for c, loop in enumerate(poly.loop_indices): layer.data[loop].uv = (tri_uv[c][0], 1 - tri_uv[c][1])
        obj = bpy.data.objects.new(label, mesh); bpy.context.collection.objects.link(obj)
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 32
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    scene.view_settings.view_transform = 'AgX'
    world = scene.world or bpy.data.worlds.new('ciel'); scene.world = world
    world.use_nodes = True; world.node_tree.nodes['Background'].inputs[0].default_value = (.55, .62, .75, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .8
    sun = bpy.data.lights.new('soleil', 'SUN'); sun.energy = 4.5; sun.angle = math.radians(2)
    so = bpy.data.objects.new('soleil', sun); scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), 0, math.radians(35))
    for view, (eye, target) in enumerate(VIEWS):
        cam = bpy.data.cameras.new('cam'); cam.lens = 24; cam.clip_end = 2000
        co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co)
        e = Vector((eye[0], -eye[2], eye[1])); t = Vector((target[0], -target[2], target[1]))
        co.location = e; co.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler(); scene.camera = co
        scene.render.filepath = str(OUT / 'preview' / f'{name}-vue{view}.png'); bpy.ops.render.render(write_still=True)


# points de vue du joueur (camera derriere Jak au centre de l'arene) : vers le tas de rochers, vers la lave
VIEWS = [tuple(map(tuple, v)) for v in CONFIG['views']] if 'views' in CONFIG else [
         ((2272.5, 19.5, -450.4), (2272.0, 24.0, -380.0)),
         ((2280.0, 19.5, -442.4), (2210.0, 22.0, -442.0)),
         ((2272.5, 30.0, -450.4), (2330.0, 60.0, -560.0))]

t0 = time.time()
patch = {'description': 'Arene : falaises sculptees en strates de gres (v2)', 'remove': [], 'add': []}
report, before, after = [], [], []
for p, lst in sorted(protos.items()):
    chosen = []
    for instance, fs in lst:
        c = np.array([v['p'] for f in fs for v in f['vertices']]).mean(0)
        dist = float(np.linalg.norm(c[[0, 2]] - ARENA))
        if MODE in ('apercu', 'partiel') and np.linalg.norm(c[[0, 2]] - FOCUS) > RADIUS: continue
        chosen.append((instance, fs, dist < NEAR))
    if not chosen: continue
    field = build_field(lst[0][1])
    info = {'proto': list(p), 'instances': len(chosen), 'size_m': round(field['size'], 1), 'round_sigma_m': round(field['sigma'], 2),
            'native_triangles': len(lst[0][1]), 'new_triangles': 0, 'max_affine_error_m': 0}
    for instance, fs, near in chosen:
        W, NW, T, S, uv, bary, err = sculpt(field, fs, near)
        info['new_triangles'] += int(len(T)); info['max_affine_error_m'] = max(info['max_affine_error_m'], round(err, 4))
        if MODE == 'apercu':
            before.append((f'n{p}_{instance}', np.array([v['p'] for f in fs for v in f['vertices']]),
                           np.arange(3 * len(fs)).reshape(-1, 3), np.arange(len(fs)),
                           np.array([[v['uv'] for v in f['vertices']] for f in fs]), fs))
            after.append((f'r{p}_{instance}', W, T, S, uv, fs))
        else:
            remove, add = records(fs, W, NW, T, S, uv, bary)
            patch['remove'].extend(remove); patch['add'].extend(add)
    report.append(info)
    print(f"proto {p}: {len(chosen)} exemplaires, {info['native_triangles']} -> {info['new_triangles']} triangles "
          f"({time.time() - t0:.0f} s)", flush=True)

if MODE == 'apercu':
    preview_scene(before, CONFIG['preview_prefix'] + '-avant'); preview_scene(after, CONFIG['preview_prefix'] + '-apres')
else:
    Path(CONFIG['patch']).write_text(json.dumps(patch, separators=(',', ':')))
    Path(CONFIG['report']).write_text(json.dumps(report, indent=2))
    print('Enregistre :', len(patch['remove']), 'retires ->', len(patch['add']), 'ajoutes', flush=True)
