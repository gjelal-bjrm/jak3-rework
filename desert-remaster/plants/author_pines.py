"""Pins du desert : les cartes verticales d'aiguilles (des-pinetree-leaf-01, franges des etages de feuillage) sont
remplacees par de vrais rameaux d'aiguilles en volume.

Lancement :
  blender --background --python desert-remaster/plants/author_pines.py -- <export.json> <sortie-patch.json> [apercu X Z R]

Chaque carte d'origine (colonnes de quads verticales, image d'aiguilles transparente) donne sa ligne de pied et sa
hauteur ; on y plante des rameaux espaces de ~35 cm : rameau plie en V le long de sa nervure, courbe, penche vers
l'exterieur, texture opaque d'aiguilles en chevrons (sprig.png). Construits une fois par prototype puis poses sur
chaque exemplaire par sa transformation propre ; couleurs = palette du sommet d'origine le plus proche.
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
from blender_common import reset
HERE = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = args[0], args[1]
MODE = args[2] if len(args) > 2 else 'tout'
if MODE == 'apercu': FOCUS = np.array([float(args[3]), float(args[4])]); RADIUS = float(args[5])
GRASS = 'des-pinetree-leaf-01'
BLADE_TEXTURE = 'des-pine-sprig-v1'

faces = json.load(open(SRC)); faces = faces['faces'] if isinstance(faces, dict) else faces
instances = defaultdict(list)
for f in faces:
    if f['tree_type'] == 'shrub' and f['material'] == GRASS:
        instances[(f['tree'], f['proto'], f['instance'])].append(f)
protos = defaultdict(list)
for (tree, proto, inst), fs in sorted(instances.items()): protos[(tree, proto)].append((inst, fs))


def cards(fs):
    """Colonnes de cartes : (pied, sommet) pour chaque sommet du bas (v max), sommet = meme u, v min, le plus proche."""
    V = {}
    for f in fs:
        for v in f['vertices']: V[tuple(round(x, 4) for x in v['p'])] = (np.array(v['p']), v['uv'])
    pts = list(V.values())
    vmax = max(uv[1] for _, uv in pts); vmin = min(uv[1] for _, uv in pts)
    bottom = [(p, uv) for p, uv in pts if uv[1] > vmax - 60]
    top = [(p, uv) for p, uv in pts if uv[1] < vmin + 60]
    segs = []
    for f in fs:                                              # aretes du bas (deux sommets au pied)
        b = [np.array(v['p']) for v in f['vertices'] if v['uv'][1] > vmax - 60]
        if len(b) == 2: segs.append(tuple(b))
    def top_of(p, uv):
        c = [q for q, w in top if abs(w[0] - uv[0]) < 40]
        return min(c or [q for q, _ in top], key=lambda q: np.linalg.norm((q - p)[[0, 2]]))
    colmap = {tuple(np.round(p, 4)): top_of(p, uv) for p, uv in bottom}
    return segs, colmap


def author(fs, seed):
    rng = random.Random(seed)
    tris = []
    segs, colmap = cards(fs)
    centre = np.array([v['p'] for f in fs for v in f['vertices']]).mean(0)
    for a, b in segs:
        ta, tb = colmap[tuple(np.round(a, 4))], colmap[tuple(np.round(b, 4))]
        L = float(np.linalg.norm(b - a)); n = max(2, int(L / .35))
        for k in range(n):
            t = (k + rng.uniform(.2, .8)) / n
            base = a + (b - a) * t; tip0 = ta + (tb - ta) * t
            up = tip0 - base; H = float(np.linalg.norm(up))
            if H < .2: continue
            up /= H
            out = (base - centre); out[1] = 0; out = out / max(np.linalg.norm(out), 1e-6)
            d = up + out * rng.uniform(.15, .45) + np.array([rng.uniform(-.15, .15), 0, rng.uniform(-.15, .15)])
            d /= np.linalg.norm(d)
            length = H * rng.uniform(.75, 1.05)
            side = np.cross(d, [0, 1, 0]); side = side / max(np.linalg.norm(side), 1e-6)
            if np.linalg.norm(side) < .5: side = np.array([1., 0, 0])
            normal = np.cross(side, d)
            w0 = min(.28, .16 * length); curl = rng.uniform(.05, .14) * length
            rows = []
            for i, s_ in enumerate((0, .35, .7, 1.0)):
                c = base + d * length * s_ + normal * (math.sin(math.pi * s_) * curl - .12 * length * s_ * s_)
                w = w0 * (math.sin(math.pi * (.08 + .92 * s_)) ** .6) * (1 - .2 * s_)
                if i == 3: w = .003
                rows.append((c - side * w - normal * w * .25, c + normal * w * .15, c + side * w - normal * w * .25, 1 - s_))
            for i in range(3):
                r0, r1 = rows[i], rows[i + 1]
                for j in range(2):
                    p00, p01, p10, p11 = r0[j], r0[j + 1], r1[j], r1[j + 1]
                    u0, u1 = j / 2, (j + 1) / 2
                    tris.append(((Vector(p00), Vector(p01), Vector(p11)), ((u0, r0[3]), (u1, r0[3]), (u1, r1[3]))))
                    tris.append(((Vector(p00), Vector(p11), Vector(p10)), ((u0, r0[3]), (u1, r1[3]), (u0, r1[3]))))
    return tris


def barycentric(p, tri):
    a, b, c = tri; u = b - a; v = c - a; w = p - a
    aa, ab, bb, wa, wb = u @ u, u @ v, v @ v, w @ u, w @ v
    den = aa * bb - ab * ab
    if abs(den) < 1e-12: return np.array([1., 0., 0.])
    y = (bb * wa - ab * wb) / den; z = (aa * wb - ab * wa) / den
    wts = np.clip(np.array([1 - y - z, y, z]), 0, 1); return wts / wts.sum()


def records(ref_fs, tris, chosen):
    P = [np.array([v['p'] for v in f['vertices']]) for f in ref_fs]
    verts = [Vector(x) for p in P for x in p]
    bvh = BVHTree.FromPolygons(verts, [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(len(P))], all_triangles=True)
    V = np.array([[list(p) for p in t[0]] for t in tris])
    near = np.zeros((len(tris), 3), int); W = np.zeros((len(tris), 3, 3))
    for i in range(len(tris)):
        for j in range(3):
            _, _, k, _ = bvh.find_nearest(Vector(V[i, j])); near[i, j] = k; W[i, j] = barycentric(V[i, j], P[k])
    A = np.concatenate(P)
    remove, add, worst = [], [], 0.0
    for inst, fs in chosen:
        B = np.array([v['p'] for f in fs for v in f['vertices']])
        if B.shape != A.shape: raise RuntimeError(f'exemplaire {inst} : sommets differents')
        ca, cb = A.mean(0), B.mean(0)
        M = np.linalg.lstsq(A - ca, B - cb, rcond=None)[0]
        err = float(np.abs((A - ca) @ M - (B - cb)).max()); worst = max(worst, err)
        if err > .05: raise RuntimeError(f'exemplaire {inst} : transformation non affine ({err:.3f} m)')
        remove += [{**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index')},
                    'original_positions': [v['p'] for v in f['vertices']]} for f in fs]
        Wp = (V - ca) @ M + cb
        for i, t in enumerate(tris):
            src0 = fs[near[i, 0]]
            rec = {k: src0[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group')}; rec['texture'] = BLADE_TEXTURE
            rec['vertices'] = []
            for j in range(3):
                src = fs[near[i, j]]; w = W[i, j]
                rgba = [int(round(sum(w[q] * src['vertices'][q].get('rgba', [128] * 3)[ch] for q in range(3)))) for ch in range(3)]
                # shrub : coordonnees de texture en 1/4096 (shrub.vert divise par 4096)
                uv = [float(c) * 4096. for c in t[1][j]] if src0['tree_type'] == 'shrub' else list(t[1][j])
                rec['vertices'].append({'p': [round(float(x), 3) for x in Wp[i, j]], 'uv': uv,
                                        'color_indices': [v['color'] for v in src['vertices']],
                                        'color_weights': [round(float(x), 4) for x in w], 'rgba': rgba})
            add.append(rec)
    return remove, add, worst


def preview(items, name, focus):
    reset()
    img = bpy.data.images.load(str(HERE / 'sprig.png'))
    mat = bpy.data.materials.new('brin'); mat.use_nodes = True
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = img
    mat.node_tree.links.new(tex.outputs['Color'], mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    grey = bpy.data.materials.new('carte'); grey.diffuse_color = (.55, .5, .35, 1)
    for label, tl, m in items:
        verts, polys, uvs = [], [], []
        for (ps, uv) in tl:
            s = len(verts); verts += [(p[0], -p[2], p[1]) for p in ps]; polys.append((s, s + 1, s + 2)); uvs.append(uv)
        mesh = bpy.data.meshes.new(label); mesh.from_pydata(verts, [], polys); mesh.update(); mesh.materials.append(grey if m == 'carte' else mat)
        uvl = mesh.uv_layers.new(name='UVMap')
        for poly, uv in zip(mesh.polygons, uvs):
            for c, li in enumerate(poly.loop_indices): uvl.data[li].uv = (uv[c][0], 1 - uv[c][1])
        obj = bpy.data.objects.new(label, mesh); bpy.context.collection.objects.link(obj)
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 24
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    world = scene.world or bpy.data.worlds.new('ciel'); scene.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.55, .62, .75, 1)
    sun = bpy.data.lights.new('soleil', 'SUN'); sun.energy = 4.5; so = bpy.data.objects.new('soleil', sun); scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(45), 0, math.radians(35))
    cam = bpy.data.cameras.new('cam'); cam.lens = 35; cam.clip_end = 3000
    co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co); scene.camera = co
    fx, fy, fz, size = focus; d = max(size, 4) * .8
    e = Vector((fx + d, -(fz - d), fy + d * .5)); t = Vector((fx, -fz, fy))
    co.location = e; co.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(HERE / 'preview' / name); bpy.ops.render.render(write_still=True)


patch = {'description': 'Desert : rameaux d aiguilles de pin en volume', 'remove': [], 'add': [],
         'new_textures': [{'name': BLADE_TEXTURE, 'page': 'remaster-desert-plants', 'width': 128, 'height': 256,
                           'rgba_file': str(HERE / 'sprig.rgba')}]}
before, after = [], []
for (tree, proto), lst in sorted(protos.items()):
    chosen = lst
    if MODE == 'apercu':
        chosen = [(i, fs) for i, fs in lst if np.linalg.norm(np.array([v['p'] for f in fs for v in f['vertices']]).mean(0)[[0, 2]] - FOCUS) < RADIUS]
        if not chosen: continue
    ref_inst, ref_fs = lst[0]
    tris = author(ref_fs, proto * 131 + tree)
    remove, add, err = records(ref_fs, tris, chosen)
    print(f'pin tree {tree} proto {proto} : {len(chosen)} exemplaires, {len(ref_fs)} -> {len(tris)} triangles', flush=True)
    if MODE == 'apercu':
        for inst, fs in chosen:
            before.append((f'n{proto}_{inst}', [([Vector(v['p']) for v in f['vertices']], [(0, 0)] * 3) for f in fs], None))
        per = len(tris)
        for idx in range(len(chosen)):
            after.append((f'r{proto}_{idx}', [([Vector(x['p']) for x in r['vertices']], [tuple(c / 4096. for c in x['uv']) for x in r['vertices']]) for r in add[idx * per:(idx + 1) * per]], None))
    else:
        patch['remove'] += remove; patch['add'] += add

if MODE == 'apercu':
    (HERE / 'preview').mkdir(exist_ok=True)
    pts = np.array([list(p) for _, tl, _ in after for ps, _ in tl for p in ps])
    lo, hi = pts.min(0), pts.max(0); c = (lo + hi) / 2
    focus = (float(c[0]), float(c[1]), float(c[2]), float(max(hi - lo)))
    preview([(a, b, 'carte') for a, b, _ in before], 'pines-avant.png', focus)
    preview([(a, b, 'brin') for a, b, _ in after], 'pines-apres.png', focus)
else:
    Path(OUT).write_text(json.dumps(patch, separators=(',', ':')))
    print('Enregistre :', len(patch['remove']), 'retires ->', len(patch['add']), 'ajoutes', flush=True)
