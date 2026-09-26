"""Arene de Spargus : nouveau plaquage des textures (fin de l'effet « tordu »).

Lancement : blender.exe --background --python arena-remaster/uv/reuv_arena.py -- <niveau> [<export natif>]
  niveau : wasstada (defaut : ../objects/wasstada-all-native.json), wasstadb, wasstadc...
Sortie : uv-patch-<niveau>.json (memes triangles, memes couleurs ; seuls les UV et les normales changent)
et uv-report-<niveau>.json (etirement avant/apres par matiere).

Le plaquage d'origine etire les textures de 1,5 a 5 fois et les cisaille ; la meme texture n'a pas la meme
taille d'une face a l'autre. Invisible avec les textures floues de 2004, « tordu » avec les textures HD.
Pour chaque objet (prototype TIE, ou arbre TFRAG entier) :
  1. depliage conforme dans Blender (aucun etirement ni cisaillement), coutures aux aretes vives (> 35 deg)
     et aux changements de matiere ;
  2. chaque ile est tournee pour que le dessin garde le sens d'origine (le sens du u natif, meme parite),
     et mise a l'echelle commune de sa matiere (densite mediane d'origine : meme taille partout) ;
  3. textures a MOTIF (plaques rivetees, marches, frises...) : un nombre entier de repetitions par ile, pour
     que les bords du dessin tombent sur les bords de la piece ; axe trop petit (tranches) : echelle commune ;
     textures CONTINUES (tole, bois, pierre...) : echelle commune, position moyenne d'origine conservee.
Les roches (plaquage selon le monde dans le shader), les braseros et les lames (remodeles) ne sont pas touches.
"""
import sys, json, math, functools
from pathlib import Path
from collections import defaultdict
import numpy as np
import bpy, bmesh
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CONFIG = {}
if args and args[0].endswith('.json'):
    # autre lieu : {level, native, materials (a replaquer), motif (textures a motif), out (dossier)}
    CONFIG = json.loads(Path(args[0]).read_text()); args = [CONFIG['level'], str(ROOT / CONFIG['native'])]
LEVEL = args[0] if args else 'wasstada'
SOURCE = Path(args[1]) if len(args) > 1 else ROOT / 'arena-remaster/objects/wasstada-all-native.json'
if CONFIG.get('out'): OUT = ROOT / CONFIG['out']

MOTIF = {
    'wstd-floor-panel01', 'wstd-floor-panel02', 'wstd-floor-panel03', 'wstd-tentacle-plate02', 'wstd-tentacle-plate03',
    'wstd-throne-wall01', 'wstd-throne-wall02', 'wstd-stands-plateedge', 'wstd-stands-lowall01', 'wstd-stands-stairs01',
    'wstd-stands-seats02', 'wstd-stands-ceiling', 'wstd-stands-ceilingplate', 'wstd-throne-plat02', 'wstd-throne-plat03',
    'wstd-throne-floor02', 'wstd-platform-floor', 'wstd-platform-base', 'wstd-scaffold-wall-edge', 'wstd-scaffold-teeth',
    'wstd-mount-post', 'wstd-ladder', 'common_sandstone_taper01', 'wstd-fight-plat-box-end', 'wstd-fight-plat-box-side',
    'wstd-fight-plat-box-top', 'wstd-fight-plat-door', 'wstd-fight-plat-floor-01', 'wstd-fight-plat-floor-02',
    'wstd-fight-plat-floor-03', 'wstd-fight-plat-lrg-floor-01', 'wstd-fight-plat-lrg-floor-02',
    'wstd-fight-plat-lrg-floor-03', 'wstd-fight-plat-lrg-floor-04', 'wstd-fight-plat-lrg-floor-05',
    'wstd-fight-plat-wall-01', 'wstd-fight-plat-wall-02', 'wstd-fight-plat-wall-03', 'wstd-fight-plat-tube',
}
SKIP = {'wstd-rockwall-01', 'wstd-small-rockwall-01', 'wstd-interior-rock01', 'wstd-torchbowl-01', 'wstd-torchbowl-02',
        'wstd-torchbowl-coal-01', 'wstd-spike-01', 'wstd-canopy', 'wstd-flag', 'wstd-stands-black', 'wstd-spear01',
        'wstd-spear02', 'wstd-rock-shrubs', 'wstd-shrub-pebbles'}
SEAM_ANGLE = math.radians(35)


@functools.lru_cache(maxsize=None)
def texture_size(name):
    for p in (ROOT / 'data/decompiler_out/jak3/textures').glob(f'*/{name}.png'):
        head = p.read_bytes()[16:24]                     # en-tete PNG : largeur, hauteur (PIL absent de Blender)
        return int.from_bytes(head[:4], 'big'), int.from_bytes(head[4:], 'big')
    return None


if CONFIG.get('motif'): MOTIF = set(CONFIG['motif'])


def eligible(name):
    if CONFIG.get('materials'): return name in CONFIG['materials'] and texture_size(name) is not None
    return (name.startswith('wstd-') or name.startswith('common_sandstone_')) and name not in SKIP and \
        'lava' not in name and texture_size(name) is not None


# ---------------------------------------------------------------- mesures
def jacobian(P, U):
    """Metres par unite de UV (3x2) d'un triangle ; None si UV degeneres."""
    E = np.array([P[1] - P[0], P[2] - P[0]]).T
    D = np.array([U[1] - U[0], U[2] - U[0]]).T
    if abs(np.linalg.det(D)) < 1e-12: return None
    return E @ np.linalg.inv(D)


def stretch(P, U, size):
    J = jacobian(P, U)
    if J is None: return None
    s = np.linalg.svd(J @ np.diag([1 / size[0], 1 / size[1]]), compute_uv=False)
    return s[0] / max(s[1], 1e-12), math.sqrt(s[0] * s[1])


# ---------------------------------------------------------------- depliage d'un groupe
def unwrap(faces):
    """faces : faces natives (monde). Renvoie par face : uv (3x2) depliees en metres, et id d'ile."""
    weld, V, T, M = {}, [], [], []
    mats = sorted({f['material'] for f in faces})
    for f in faces:
        ids = []
        for v in f['vertices']:
            key = tuple(round(x * 1000) for x in v['p'])
            if key not in weld: weld[key] = len(V); V.append(v['p'])
            ids.append(weld[key])
        T.append(ids); M.append(mats.index(f['material']))
    bm = bmesh.new()
    bv = [bm.verts.new(p) for p in V]
    uv_layer = bm.loops.layers.uv.new('UVMap')
    made = []
    for ids, m in zip(T, M):
        try:
            face = bm.faces.new([bv[i] for i in ids]) if len(set(ids)) == 3 else None
        except ValueError:
            face = None                                      # face en double : traitee a part
        if face is not None: face.material_index = m
        made.append(face)
    bm.normal_update()
    for e in bm.edges:
        lf = e.link_faces
        e.seam = len(lf) != 2 or lf[0].material_index != lf[1].material_index or e.calc_face_angle(math.pi) > SEAM_ANGLE
    mesh = bpy.data.meshes.new('groupe'); bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new('groupe', mesh); bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='CONFORMAL', margin=0.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    uvl = mesh.uv_layers.active.data
    # iles : faces reliees par des aretes non coupees
    parent = list(range(len(mesh.polygons)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    edge_faces = defaultdict(list)
    for poly in mesh.polygons:
        for k in poly.edge_keys: edge_faces[k].append(poly.index)
    seams = {tuple(sorted(e.vertices)) for e in mesh.edges if e.use_seam}
    for k, fl in edge_faces.items():
        if len(fl) == 2 and tuple(sorted(k)) not in seams: parent[find(fl[0])] = find(fl[1])
    result = [None] * len(faces)
    polys = iter(mesh.polygons)
    for i, face in enumerate(made):
        if face is None: continue
        poly = next(polys)
        loops = {mesh.loops[l].vertex_index: uvl[l].uv[:] for l in poly.loop_indices}
        result[i] = (np.array([loops[j] for j in T[i]]), find(poly.index))
    bpy.data.objects.remove(obj, do_unlink=True); bpy.data.meshes.remove(mesh)
    return result


def fit_islands(faces, unwrapped, density):
    """UV finales par face : orientation d'origine, echelle commune, repetitions entieres (motifs)."""
    islands = defaultdict(list)
    for i, u in enumerate(unwrapped):
        if u is not None: islands[u[1]].append(i)
    new_uv = [None] * len(faces)
    for members in islands.values():
        mat = faces[members[0]]['material']; size = texture_size(mat)
        Tu, Tv = density[mat] * size[0], density[mat] * size[1]          # metres par repetition
        P = [np.array([v['p'] for v in faces[i]['vertices']]) for i in members]
        Q = [unwrapped[i][0] for i in members]
        N = [np.array([v['uv'] for v in faces[i]['vertices']]) for i in members]
        # echelle du depliage -> metres
        aw = sum(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) / 2 for p in P)
        aq = sum(abs(np.cross(q[1] - q[0], q[2] - q[0])) / 2 for q in Q)
        if aw < 1e-8 or aq < 1e-12: continue
        c = math.sqrt(aw / aq); Qm = [q * c for q in Q]
        # sens du dessin d'origine : gradients de u et v natifs dans le plan deplie
        gu = np.zeros(2); gv = np.zeros(2)
        for q, n, p in zip(Qm, N, P):
            D = np.array([q[1] - q[0], q[2] - q[0]]).T
            if abs(np.linalg.det(D)) < 1e-12: continue
            K = np.array([n[1] - n[0], n[2] - n[0]]).T @ np.linalg.inv(D)      # d(uv natif)/d(metres)
            a = np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) / 2
            if np.linalg.norm(K[0]) > 1e-9: gu += a * K[0] / np.linalg.norm(K[0])
            if np.linalg.norm(K[1]) > 1e-9: gv += a * K[1] / np.linalg.norm(K[1])
        ex = gu / np.linalg.norm(gu) if np.linalg.norm(gu) > 1e-9 else np.array([1., 0.])
        ey = np.array([-ex[1], ex[0]])
        if gv @ ey < 0: ey = -ey                                              # meme parite que l'original
        R = [np.stack([q @ ex, q @ ey], -1) for q in Qm]
        allp = np.concatenate(R); lo, hi = allp.min(0), allp.max(0); ext = hi - lo
        if mat in MOTIF:
            best = None
            for nu in range(1, max(2, int(ext[0] / Tu) + 3)):
                for nv in range(1, max(2, int(ext[1] / Tv) + 3)):
                    su, sv = ext[0] / nu, ext[1] / nv
                    cost = abs(math.log(su / Tu)) + abs(math.log(sv / Tv)) + 2 * abs(math.log((su / sv) / (Tu / Tv)))
                    if best is None or cost < best[0]: best = (cost, nu, nv)
            _, nu, nv = best
            fit_u = ext[0] >= .6 * Tu; fit_v = ext[1] >= .6 * Tv
            su = ext[0] / nu if fit_u else Tu; sv = ext[1] / nv if fit_v else Tv
            if not fit_u and fit_v: su = sv * Tu / Tv                          # tranche : garder les proportions
            if fit_u and not fit_v: sv = su * Tv / Tu
            for i, r in zip(members, R):
                new_uv[i] = np.stack([(r[:, 0] - lo[0]) / su, (r[:, 1] - lo[1]) / sv], -1)
        else:
            centre_native = np.concatenate(N).mean(0)
            centre_new = np.array([allp[:, 0].mean() / Tu, allp[:, 1].mean() / Tv])
            shift = centre_native - centre_new
            for i, r in zip(members, R):
                new_uv[i] = np.stack([r[:, 0] / Tu, r[:, 1] / Tv], -1) + shift
    return new_uv


def corner_normals(faces, unwrapped):
    """Normales lissees a l'interieur de chaque ile, vives entre les iles (objets fabriques)."""
    acc = defaultdict(lambda: np.zeros(3))
    fn = []
    for i, f in enumerate(faces):
        P = np.array([v['p'] for v in f['vertices']]); n = np.cross(P[1] - P[0], P[2] - P[0])
        fn.append(n)
        if unwrapped[i] is None: continue
        for v in f['vertices']: acc[(unwrapped[i][1], tuple(round(x * 1000) for x in v['p']))] += n
    out = []
    for i, f in enumerate(faces):
        ns = []
        for v in f['vertices']:
            n = acc[(unwrapped[i][1], tuple(round(x * 1000) for x in v['p']))] if unwrapped[i] is not None else fn[i]
            ns.append(n / max(np.linalg.norm(n), 1e-12))
        out.append(ns)
    return out


# ---------------------------------------------------------------- programme
data = json.loads(SOURCE.read_text())
faces_all = [f for f in data['faces'] if f['geom'] == 0 and eligible(f['material'])]
print(f'{LEVEL} : {len(faces_all)} faces a replaquer', flush=True)
# densite commune par matiere : mediane (ponderee par l'aire) des metres par pixel d'origine
samples = defaultdict(list)
for f in faces_all:
    P = np.array([v['p'] for v in f['vertices']]); U = np.array([v['uv'] for v in f['vertices']])
    r = stretch(P, U, texture_size(f['material']))
    if r: samples[f['material']].append((np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])) / 2, r[1], r[0]))
density, report = {}, {}
for m, l in samples.items():
    a = np.array(l); o = np.argsort(a[:, 1]); cw = np.cumsum(a[o, 0]) / a[:, 0].sum()
    density[m] = a[o][min(np.searchsorted(cw, .5), len(a) - 1), 1]
    o2 = np.argsort(a[:, 2]); cw2 = np.cumsum(a[o2, 0]) / a[:, 0].sum()
    report[m] = {'surface_m2': round(float(a[:, 0].sum())), 'etirement_median_avant': round(float(a[o2][min(np.searchsorted(cw2, .5), len(a) - 1), 2]), 2),
                 'cm_par_pixel_origine': round(float(density[m]) * 100, 2), 'mode': 'motif' if m in MOTIF else 'continu'}

groups = defaultdict(list)
for f in faces_all:
    groups[(f['tree_type'], f['tree'], f['proto'] if f['tree_type'] != 'tfrag' else -1, f['instance'])].append(f)
protos = defaultdict(list)
for (tt, tree, proto, inst), fs in sorted(groups.items()):
    protos[(tt, tree, proto)].append((inst, fs))

patch = {'description': f'Arene ({LEVEL}) : textures replaquees sans etirement (fin de l effet tordu)', 'remove': [], 'add': []}
after = defaultdict(list)
for key, lst in sorted(protos.items()):
    ref = lst[0][1]
    unwrapped = unwrap(ref)
    new_uv = fit_islands(ref, unwrapped, density)
    Aref = np.array([v['p'] for f in ref for v in f['vertices']]); ca = Aref.mean(0)
    for inst, fs in lst:
        B = np.array([v['p'] for f in fs for v in f['vertices']]); cb = B.mean(0)
        if len(fs) != len(ref): continue
        M = np.linalg.lstsq(Aref - ca, B - cb, rcond=None)[0]
        if np.abs((Aref - ca) @ M - (B - cb)).max() > .05: continue           # exemplaire non conforme : laisse tel quel
        normals = corner_normals(fs, unwrapped)
        for j, f in enumerate(fs):
            if new_uv[j] is None: continue
            patch['remove'].append({**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index')},
                                    'original_positions': [v['p'] for v in f['vertices']]})
            rec = {k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group')}; rec['vertices'] = []
            ci = [v['color'] for v in f['vertices']]
            for c, v in enumerate(f['vertices']):
                w = [0.0, 0.0, 0.0]; w[c] = 1.0
                rec['vertices'].append({'p': v['p'], 'uv': [round(float(x), 5) for x in new_uv[j][c]],
                                        'normal': [round(float(x), 4) for x in normals[j][c]],
                                        'color_indices': ci, 'color_weights': w})
            patch['add'].append(rec)
            P = np.array([v['p'] for v in f['vertices']])
            r = stretch(P, new_uv[j], texture_size(f['material']))
            if r: after[f['material']].append((np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])) / 2, r[0]))
    print(f'{key} : {len(lst)} exemplaire(s), {len(ref)} faces', flush=True)
for m, l in after.items():
    a = np.array(l); o = np.argsort(a[:, 1]); cw = np.cumsum(a[o, 0]) / a[:, 0].sum()
    report.setdefault(m, {})['etirement_median_apres'] = round(float(a[o][min(np.searchsorted(cw, .5), len(a) - 1), 1]), 2)
    report[m]['etirement_90pc_apres'] = round(float(a[o][min(np.searchsorted(cw, .9), len(a) - 1), 1]), 2)
(OUT / f'uv-patch-{LEVEL}.json').write_text(json.dumps(patch, separators=(',', ':')))
(OUT / f'uv-report-{LEVEL}.json').write_text(json.dumps(report, indent=1, ensure_ascii=False))
print('Enregistre :', len(patch['remove']), 'faces replaquees', flush=True)
