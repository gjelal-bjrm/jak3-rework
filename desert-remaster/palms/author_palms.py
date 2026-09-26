"""Palmiers du desert : palmes refaites en vraies feuilles (tige, rachis, folioles), par prototype.

Lancement (Blender, en arriere-plan) :
  blender --background --python desert-remaster/palms/author_palms.py -- <export.json> <sortie-patch.json> [apercu X Z R]

Dans le desert, un palmier est un assemblage d'exemplaires TIE : un tronc, un « coeur », et des dizaines de palmes
posees une a une autour du sommet. Chaque palme d'origine = une tige plate + deux cartes « plume » transparentes
(16 triangles). On la remplace par :
  - une tige ronde qui suit la courbe d'origine, puis un rachis qui s'affine jusqu'a la pointe ;
  - des paires de folioles separees (une vraie feuille chacune, pliee en V, arquee, qui retombe), dont la longueur
    suit l'enveloppe de la plume d'origine : la silhouette de chaque palmier est conservee.
La palme est construite UNE fois par prototype (sur un exemplaire de reference), puis posee sur chaque exemplaire
par sa transformation propre (calculee sur les sommets d'origine) : les couronnes gardent exactement leur
disposition. Couleurs (palettes de l'heure du jour) : celles de la face d'origine la plus proche, de CET exemplaire.
Texture des folioles : tissu de feuille 1024 deja cree pour les palmiers du marche (models-v2/leaf-tissue).
"""
import sys, json, math, random
from pathlib import Path
from collections import defaultdict
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'models-v1'))
from blender_common import reset, load_material
HERE = Path(__file__).resolve().parent

args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = args[0], args[1]
MODE = args[2] if len(args) > 2 else 'tout'
if MODE == 'apercu': FOCUS = np.array([float(args[3]), float(args[4])]); RADIUS = float(args[5])

LEAF, STEM = 'des-palm-leaf-01', 'des-palmtree-trunk-02'
LEAFLET_TEXTURE = 'des-palm-leaflet-v1'
LEAFLET_RGBA = ROOT / 'models-v2/leaf-tissue.rgba'
LEAFLET_PNG = ROOT / 'models-v2/leaf-tissue-1024.png'

faces = json.load(open(SRC))
faces = faces['faces'] if isinstance(faces, dict) else faces
instances = defaultdict(list)
for f in faces:
    if f.get('geom', 0) == 0 and f['tree_type'] == 'tie' and f['material'] in (LEAF, STEM):
        instances[(f['tree'], f['proto'], f['instance'])].append(f)
protos = defaultdict(list); trunks = defaultdict(list)
for (tree, proto, inst), fs in sorted(instances.items()):
    if any(f['material'] == LEAF for f in fs):          # prototypes « palme » : tige + cartes plume
        protos[(tree, proto)].append((inst, fs))
    elif len(fs) >= 40:                                  # prototypes « tronc » (tube d'ecorce seul)
        trunks[(tree, proto)].append((inst, fs))


def smooth(t): return t * t * (3 - 2 * t)


def catmull(points, n):
    """Courbe lisse passant par les points (Catmull-Rom centripete simplifiee), n echantillons."""
    P = [points[0] * 2 - points[1]] + list(points) + [points[-1] * 2 - points[-2]]
    out = []
    segs = len(points) - 1
    for k in range(n + 1):
        s = k / n * segs; i = min(int(s), segs - 1); t = s - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return out


class Builder:
    """Triangles monde (exemplaire de reference) avec UV, role (tige / foliole) et normale lissee."""
    def __init__(self):
        self.tris = []      # (p0,p1,p2, uv0,uv1,uv2, role)

    def quad(self, a, b, c, d, ua, ub, uc, ud, role):
        self.tris.append((a, b, c, ua, ub, uc, role)); self.tris.append((a, c, d, ua, uc, ud, role))

    def tube(self, path, radii, sides, role, v_scale):
        rows = []
        length = 0.0; acc = [0.0]
        for i in range(1, len(path)): length += (path[i] - path[i - 1]).length; acc.append(length)
        for i, p in enumerate(path):
            t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
            side = t.cross(Vector((0, 1, 0)))
            if side.length < .01: side = t.cross(Vector((1, 0, 0)))
            side.normalize(); other = t.cross(side).normalized()
            rows.append([p + (side * math.cos(2 * math.pi * j / sides) + other * math.sin(2 * math.pi * j / sides)) * radii[i]
                         for j in range(sides + 1)])
        for i in range(len(rows) - 1):
            for j in range(sides):
                v0, v1 = acc[i] * v_scale, acc[i + 1] * v_scale
                self.quad(rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j],
                          (j / sides, v0), ((j + 1) / sides, v0), ((j + 1) / sides, v1), (j / sides, v1), role)

    def blade(self, root, tip, width, normal, rng, steps, fold=.2):
        """Foliole : pliee en V le long de sa nervure, arquee, retombante ; UV : tissu (nervure au centre)."""
        axis = tip - root; length = axis.length
        side = axis.cross(normal).normalized(); normal = side.cross(axis).normalized()
        curl = rng.uniform(.05, .12) * length; twist = rng.uniform(-.2, .2) * width
        rows = []
        for i in range(steps + 1):
            t = i / steps
            c = root + axis * t + normal * (math.sin(math.pi * t) * curl * .6 - .10 * length * t * t) + side * math.sin(math.pi * t) * twist
            w = max(.002, width * math.sin(math.pi * (.06 + .94 * t)) ** .7 * (1 - .25 * t))
            if i == steps: w = .002
            rows.append([c - side * w - normal * w * fold, c + normal * w * .12, c + side * w - normal * w * fold])
        for i in range(steps):
            for j in range(2):
                a, b, cc, d = rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]
                ua, ub = (j / 2, i / steps), (j / 2, (i + 1) / steps)
                uc, ud = ((j + 1) / 2, (i + 1) / steps), ((j + 1) / 2, i / steps)
                self.quad(a, b, cc, d, ua, ub, uc, ud, 'leaf')


def analyse_frond(fs):
    """Bords interieurs / exterieurs des deux cartes plume (5 points chacun, dans l'ordre de la palme), base de tige."""
    cards = [f for f in fs if f['material'] == LEAF]
    pts = {}
    for f in cards:
        for v in f['vertices']:
            pts[tuple(round(x, 3) for x in v['p'])] = (Vector(v['p']), v['uv'])
    inner = [(p, uv) for p, uv in pts.values() if uv[1] > .5]
    outer = [(p, uv) for p, uv in pts.values() if uv[1] <= .5]
    # deux cartes : separer par proximite (chaque bord interieur touche la tige d'un cote)
    stem = [Vector(v['p']) for f in fs if f['material'] == STEM for v in f['vertices']]
    def split(side_pts):
        side_pts = sorted(side_pts, key=lambda x: x[1][0])
        groups = defaultdict(list)
        for p, uv in side_pts: groups[round(uv[0] * 4)].append(p)
        return groups
    gi, go = split(inner), split(outer)
    # dans chaque colonne u : 2 points interieurs (gauche, droite) et 2 exterieurs ; appariement par distance
    cols = sorted(set(gi) & set(go))
    L_in, R_in, L_out, R_out = [], [], [], []
    for k in cols:
        a = gi[k]; b = go[k]
        if len(a) < 2 or len(b) < 2: continue
        a0, a1 = a[0], a[1]
        # exterieur le plus proche de chaque interieur
        b0 = min(b, key=lambda q: (q - a0).length); b1 = min(b, key=lambda q: (q - a1).length)
        if b0 is b1: b1 = [q for q in b if q is not b0][0]
        if L_in and (a0 - L_in[-1]).length > (a1 - L_in[-1]).length:
            a0, a1, b0, b1 = a1, a0, b1, b0
        L_in.append(a0); R_in.append(a1); L_out.append(b0); R_out.append(b1)
    centre = [(l + r) * .5 for l, r in zip(L_in, R_in)]
    # base de la tige : sommets de tige les plus eloignes de la pointe
    tip = centre[-1] if (centre[-1] - centre[0]).length > 0 else centre[0]
    far = sorted(stem, key=lambda p: -(p - tip).length)[:3]
    base = sum(far, Vector()) / len(far)
    if (base - centre[0]).length < .2: base = centre[0] - (centre[1] - centre[0]) * .3
    # orienter : la tige part de la base vers la pointe
    if (centre[0] - base).length > (centre[-1] - base).length:
        centre.reverse(); L_in.reverse(); R_in.reverse(); L_out.reverse(); R_out.reverse()
    return base, centre, L_in, R_in, L_out, R_out


def author_frond(fs, seed):
    base, centre, L_in, R_in, L_out, R_out = analyse_frond(fs)
    b = Builder()
    length = sum((centre[i + 1] - centre[i]).length for i in range(len(centre) - 1)) + (centre[0] - base).length
    path = catmull([base] + centre, 18)
    n = len(path)
    r0 = min(.022 * length, .45)
    radii = [max(.02, r0 * (1 - .82 * smooth(i / (n - 1)))) for i in range(n)]
    b.tube(path, radii, 6, 'stem', 1 / max(r0 * 6.28, .1) * .5)
    # enveloppe des folioles, de chaque cote : ecart bord exterieur - bord interieur le long de la palme
    stem_len = (centre[0] - base).length
    total = stem_len + sum((centre[i + 1] - centre[i]).length for i in range(len(centre) - 1))
    spine = catmull(centre, 40)
    envL = catmull([o - i for o, i in zip(L_out, L_in)], 40)
    envR = catmull([o - i for o, i in zip(R_out, R_in)], 40)
    sideL = catmull([l - c for l, c in zip(L_in, centre)], 40)
    sideR = catmull([r - c for r, c in zip(R_in, centre)], 40)
    rng = random.Random(seed)
    pairs = 24
    for k in range(pairs):
        t = .03 + .94 * (k + .5) / pairs
        idx = t * 40; i0 = min(int(idx), 39); a = idx - i0
        c = spine[i0].lerp(spine[i0 + 1], a)
        tangent = (spine[i0 + 1] - spine[i0]).normalized()
        for side, env, off in ((-1, envL, sideL), (1, envR, sideR)):
            e = env[i0].lerp(env[i0 + 1], a); o = off[i0].lerp(off[i0 + 1], a)
            reach = e.length * rng.uniform(.95, 1.12) + o.length * .5
            if reach < .15: continue
            out = (e + o).normalized()
            sweep = math.radians(28 + 14 * t)                       # les folioles pointent vers la pointe
            d = (out * math.cos(sweep) + tangent * math.sin(sweep)).normalized()
            d.y -= .18 + .25 * t                                    # retombee
            d.normalize()
            root = c + out * min(.3 * r0, .1)
            tipp = root + d * reach
            normal = tangent.cross(d).normalized()
            if normal.y < 0: normal = -normal
            width = max(.05, reach * .085)
            b.blade(root, tipp, width, normal, rng, 3)
    return b


def analyse_trunk(fs):
    """Anneaux du tube d'origine (centre, rayon) le long de son axe, et densite de la texture d'origine."""
    P = np.array([v['p'] for f in fs for v in f['vertices']])
    U = np.array([v['uv'] for f in fs for v in f['vertices']])
    c = P.mean(0); axis = np.linalg.eigh(np.cov((P - c).T))[1][:, -1]
    if axis[1] < 0: axis = -axis
    t = (P - c) @ axis
    order = np.argsort(t); ts = t[order]; span = ts[-1] - ts[0]
    rings, cur = [], [order[0]]
    for i in range(1, len(order)):
        if ts[i] - ts[i - 1] > .02 * span: rings.append(cur); cur = []
        cur.append(order[i])
    rings.append(cur)
    rings = [np.unique(P[r].round(3), axis=0) for r in rings]
    rings = [r for r in rings if len(r) >= 4]
    if len(rings) < 3: return None
    centres = [r.mean(0) for r in rings]
    radii = []
    for r, cc in zip(rings, centres):
        d = r - cc; d -= np.outer(d @ axis, axis); radii.append(float(np.linalg.norm(d, axis=1).mean()))
    # densite : gradient des UV le long de l'axe et autour (metres par repetition)
    along, around = [], []
    for f in fs:
        q = np.array([v['p'] for v in f['vertices']]); uv = np.array([v['uv'] for v in f['vertices']])
        E = np.stack([q[1] - q[0], q[2] - q[0]]); D = np.stack([uv[1] - uv[0], uv[2] - uv[0]])
        G = np.linalg.pinv(E) @ D
        along.append(axis @ G); side = np.cross(axis, [0, 1, 0] if abs(axis[1]) < .9 else [1, 0, 0])
        around.append((side / np.linalg.norm(side)) @ G)
    along = np.median(np.abs(np.array(along)), 0); around = np.median(np.abs(np.array(around)), 0)
    v_is_along = along[1] >= along[0]
    per_m_along = along[1] if v_is_along else along[0]
    per_m_around = around[0] if v_is_along else around[1]
    return [Vector(x) for x in centres], radii, max(per_m_along, .02), max(per_m_around, .02), v_is_along


def author_trunk(fs, seed):
    a = analyse_trunk(fs)
    if a is None: return None
    centres, radii, g_along, g_around, v_is_along = a
    b = Builder(); rng = random.Random(seed)
    n = max(24, len(centres) * 6)
    path = catmull(centres, n)
    rad = np.interp(np.linspace(0, len(radii) - 1, n + 1), np.arange(len(radii)), radii)
    sides = 14
    acc = [0.0]
    for i in range(1, len(path)): acc.append(acc[-1] + (path[i] - path[i - 1]).length)
    L = acc[-1]; collars = max(6, int(L / 1.1))
    rows = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        side = t.cross(Vector((0, 1, 0)))
        if side.length < .01: side = t.cross(Vector((1, 0, 0)))
        side.normalize(); other = t.cross(side).normalized()
        s = acc[i] / L
        flare = 1 + .55 * (1 - smooth(min(1, s / .12)))                   # evasement des racines
        collar = .07 * math.sin(math.pi * s * collars) ** 8               # bourrelets des anciennes palmes
        row = []
        for j in range(sides + 1):
            th = 2 * math.pi * j / sides
            relief = .035 * math.sin(th * 5 + s * 9) + .02 * math.sin(th * 11 - s * 23)
            r = rad[i] * (flare + relief + collar)
            row.append(p + (side * math.cos(th) + other * math.sin(th)) * r)
        rows.append(row)
    circ = 2 * math.pi * float(np.mean(rad))
    reps = max(1, round(circ * g_around))                                  # repetitions entieres autour
    for i in range(len(rows) - 1):
        for j in range(sides):
            u0, u1 = j / sides * reps, (j + 1) / sides * reps
            w0, w1 = acc[i] * g_along, acc[i + 1] * g_along
            uv = [(u0, w0), (u1, w0), (u1, w1), (u0, w1)]
            if not v_is_along: uv = [(y, x) for x, y in uv]
            b.quad(rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j], *uv, 'stem')
    return b


# ---------------------------------------------------------------- pose sur chaque exemplaire et enregistrements
def affine(A, B):
    ca, cb = A.mean(0), B.mean(0)
    M = np.linalg.lstsq(A - ca, B - cb, rcond=None)[0]
    err = float(np.abs((A - ca) @ M - (B - cb)).max())
    return ca, cb, M, err


def barycentric(p, tri):
    a, b, c = tri; u = b - a; v = c - a; w = p - a
    aa, ab, bb, wa, wb = u @ u, u @ v, v @ v, w @ u, w @ v
    den = aa * bb - ab * ab
    if abs(den) < 1e-12: return np.array([1., 0., 0.])
    y = (bb * wa - ab * wb) / den; z = (aa * wb - ab * wa) / den
    wts = np.clip(np.array([1 - y - z, y, z]), 0, 1); return wts / wts.sum()


def build_records(ref_fs, builder, inst_list):
    # face d'origine la plus proche (meme role) pour chaque sommet neuf : couleurs et draw
    role_faces = {'leaf': [k for k, f in enumerate(ref_fs) if f['material'] == LEAF],
                  'stem': [k for k, f in enumerate(ref_fs) if f['material'] == STEM]}
    P = [np.array([v['p'] for v in f['vertices']]) for f in ref_fs]
    bvh = {}
    for role, ids in role_faces.items():
        if not ids: ids = list(range(len(ref_fs)))
        verts = [Vector(x) for k in ids for x in P[k]]
        bvh[role] = (BVHTree.FromPolygons(verts, [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(len(ids))], all_triangles=True), ids)
    tris = builder.tris
    V = np.array([[list(t[j]) for j in range(3)] for t in tris])                # (n,3,3)
    near = np.zeros((len(tris), 3), int); W = np.zeros((len(tris), 3, 3)); tri_face = np.zeros(len(tris), int)
    for i, t in enumerate(tris):
        tree, ids = bvh['leaf' if t[6] == 'leaf' else 'stem']
        for j in range(3):
            _, _, mi, _ = tree.find_nearest(Vector(V[i, j])); k = ids[mi]
            near[i, j] = k; W[i, j] = barycentric(V[i, j], P[k])
        _, _, mi, _ = tree.find_nearest(Vector(V[i].mean(0))); tri_face[i] = ids[mi]
    # normales lissees (monde de reference)
    N = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    A = np.concatenate(P)
    remove, add, worst = [], [], 0.0
    for inst, fs in inst_list:
        B = np.array([v['p'] for f in fs for v in f['vertices']])
        if B.shape != A.shape: raise RuntimeError(f'exemplaire {inst} : nombre de sommets different')
        ca, cb, M, err = affine(A, B)
        if err > .05: raise RuntimeError(f'exemplaire {inst} : transformation non affine ({err:.3f} m)')
        worst = max(worst, err)
        Minv_t = np.linalg.inv(M).T
        remove += [{**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index')},
                    'original_positions': [v['p'] for v in f['vertices']]} for f in fs]
        Wp = (V - ca) @ M + cb
        Nw = N @ Minv_t.T if False else N @ np.linalg.inv(M)       # normale : (M^-1)^T appliquee a n (vecteur ligne)
        Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12)
        for i, t in enumerate(tris):
            face = fs[tri_face[i]]
            rec = {k: face[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group')}
            if t[6] == 'leaf': rec['texture'] = LEAFLET_TEXTURE
            rec['vertices'] = []
            for j in range(3):
                src = fs[near[i, j]]
                rec['vertices'].append({'p': [round(float(x), 3) for x in Wp[i, j]], 'uv': [round(t[3 + j][0], 4), round(t[3 + j][1], 4)],
                                        'normal': [round(float(x), 3) for x in Nw[i]],
                                        'color_indices': [v['color'] for v in src['vertices']],
                                        'color_weights': [round(float(x), 4) for x in W[i, j]]})
            add.append(rec)
    return remove, add, worst


def preview(items, name, focus):
    reset()
    mats = {}
    leaf_mat = bpy.data.materials.new('feuille'); leaf_mat.use_nodes = True
    img = bpy.data.images.load(str(LEAFLET_PNG)); tex = leaf_mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = img
    bsdf = leaf_mat.node_tree.nodes['Principled BSDF']; leaf_mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    for label, tris_world in items:
        verts = []; polys = []; uvs = []; roles = []
        for t in tris_world:
            s = len(verts); verts += [(p[0], -p[2], p[1]) for p in t[:3]]; polys.append((s, s + 1, s + 2)); uvs.append(t[3:6]); roles.append(t[6])
        mesh = bpy.data.meshes.new(label); mesh.from_pydata(verts, [], polys); mesh.update()
        stem_mat = load_material(STEM, 'desertb-vis-tfrag') if STEM not in mats else mats[STEM]; mats[STEM] = stem_mat
        card_mat = load_material(LEAF, 'desertb-vis-tfrag') if LEAF not in mats else mats[LEAF]; mats[LEAF] = card_mat
        for m in (stem_mat, leaf_mat, card_mat): mesh.materials.append(m)
        uvl = mesh.uv_layers.new(name='UVMap')
        for poly, uv, role in zip(mesh.polygons, uvs, roles):
            poly.material_index = {'stem': 0, 'leaf': 1, 'card': 2}[role]; poly.use_smooth = True
            for c, li in enumerate(poly.loop_indices): uvl.data[li].uv = (uv[c][0], 1 - uv[c][1])
        obj = bpy.data.objects.new(label, mesh); bpy.context.collection.objects.link(obj)
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 24
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    world = scene.world or bpy.data.worlds.new('ciel'); scene.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.55, .62, .75, 1)
    sun = bpy.data.lights.new('soleil', 'SUN'); sun.energy = 4.5; so = bpy.data.objects.new('soleil', sun); scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(45), 0, math.radians(35))
    cam = bpy.data.cameras.new('cam'); cam.lens = 30; co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co); scene.camera = co
    fx, fy, fz, size = focus
    d = max(size, 10.0) * .9
    e = Vector((fx + d, -(fz - d), fy + d * .35)); t = Vector((fx, -fz, fy))
    cam.clip_end = 5000
    co.location = e; co.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(HERE / 'preview' / name); bpy.ops.render.render(write_still=True)


def native_tris(fs):
    out = []
    for f in fs:
        p = [Vector(v['p']) for v in f['vertices']]; uv = [tuple(v['uv']) for v in f['vertices']]
        out.append((p[0], p[1], p[2], uv[0], uv[1], uv[2], 'card' if f['material'] == LEAF else 'stem'))
    return out


patch = {'description': 'Desert : palmes refaites (tige, rachis, folioles separees)', 'remove': [], 'add': [],
         'new_textures': [{'name': LEAFLET_TEXTURE, 'page': 'remaster-desert-plants', 'width': 1024, 'height': 1024,
                           'rgba_file': str(LEAFLET_RGBA)}]}
report = []; before = []; after = []
jobs = [('palme', k, v) for k, v in sorted(protos.items())] + [('tronc', k, v) for k, v in sorted(trunks.items())]
for kind, (tree, proto), lst in jobs:
    chosen = lst
    if MODE == 'apercu':
        chosen = [(i, fs) for i, fs in lst
                  if np.linalg.norm(np.array([v['p'] for f in fs for v in f['vertices']]).mean(0)[[0, 2]] - FOCUS) < RADIUS]
        if not chosen: continue
    ref_inst, ref_fs = lst[0]
    b = author_frond(ref_fs, proto * 97 + tree) if kind == 'palme' else author_trunk(ref_fs, proto * 97 + tree)
    if b is None: print(f'{kind} proto {proto} : forme non reconnue, garde tel quel'); continue
    remove, add, err = build_records(ref_fs, b, chosen)
    report.append({'tree': tree, 'proto': proto, 'instances': len(chosen), 'native_triangles': len(ref_fs),
                   'new_triangles_each': len(b.tris), 'max_affine_error_m': round(err, 4)})
    print(f'{kind} tree {tree} proto {proto} : {len(chosen)} exemplaires, {len(ref_fs)} -> {len(b.tris)} triangles', flush=True)
    if MODE == 'apercu':
        for inst, fs in chosen:
            before.append((f'n{proto}_{inst}', native_tris(fs)))
        by_inst = defaultdict(list)
        k = 0
        per = len(b.tris)
        for idx, (inst, fs) in enumerate(chosen):
            recs = add[idx * per:(idx + 1) * per]
            after.append((f'r{proto}_{inst}', [(Vector(r['vertices'][0]['p']), Vector(r['vertices'][1]['p']), Vector(r['vertices'][2]['p']),
                                                 tuple(r['vertices'][0]['uv']), tuple(r['vertices'][1]['uv']), tuple(r['vertices'][2]['uv']),
                                                 'leaf' if r.get('texture') else 'stem') for r in recs]))
    else:
        patch['remove'] += remove; patch['add'] += add

if MODE == 'apercu':
    (HERE / 'preview').mkdir(exist_ok=True)
    allp = np.array([list(t[k]) for _, tl in after for t in tl for k in range(3)])
    lo, hi = allp.min(0), allp.max(0); c = (lo + hi) / 2
    focus = (float(c[0]), float(c[1]), float(c[2]), float(max(hi - lo)))
    preview(before, 'palms-avant.png', focus); preview(after, 'palms-apres.png', focus)
else:
    Path(OUT).write_text(json.dumps(patch, separators=(',', ':')))
    (Path(OUT).with_suffix('.report.json')).write_text(json.dumps(report, indent=1))
    print('Enregistre :', len(patch['remove']), 'retires ->', len(patch['add']), 'ajoutes', flush=True)
