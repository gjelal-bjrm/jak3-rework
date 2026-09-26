"""Herbe seche du desert : touffes refaites en vrais brins (au lieu de cartes croisees transparentes).

Lancement :
  blender --background --python desert-remaster/plants/author_grass.py -- <export.json> <sortie-patch.json> [apercu X Z R]

Chaque touffe d'origine (« shrub » des-sand-grass-01) = quelques cartes verticales avec une image de brins.
On garde l'emplacement, la hauteur et l'etendue de chaque touffe, et on la remplace par des brins separes :
effiles, qui s'ecartent du centre et se courbent, hauteurs variees. Construits une fois par prototype (exemplaire de
reference) puis poses sur chaque exemplaire par sa transformation propre. Couleurs : palette et teinte du sommet
d'origine le plus proche (de CET exemplaire). Texture : degrade paille (desert-remaster/plants/grass-blade.png).
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
GRASS = 'des-sand-grass-01'
BLADE_TEXTURE = 'des-grass-blade-v1'

faces = json.load(open(SRC)); faces = faces['faces'] if isinstance(faces, dict) else faces
instances = defaultdict(list)
for f in faces:
    if f['tree_type'] == 'shrub' and f['material'] == GRASS:
        instances[(f['tree'], f['proto'], f['instance'])].append(f)
protos = defaultdict(list)
for (tree, proto, inst), fs in sorted(instances.items()): protos[(tree, proto)].append((inst, fs))


def tufts(fs):
    """Touffes de la reference : centre (x, z), sol, hauteur, rayon (cartes groupees par leur pied)."""
    cards = []
    for f in fs:
        P = np.array([v['p'] for v in f['vertices']])
        cards.append(P)
    feet = [P[P[:, 1].argmin()] for P in cards]
    groups = []
    for i, p in enumerate(feet):
        for g in groups:
            if np.linalg.norm(np.array(g['feet']).mean(0)[[0, 2]] - p[[0, 2]]) < 1.3:
                g['feet'].append(p); g['cards'].append(cards[i]); break
        else:
            groups.append({'feet': [p], 'cards': [cards[i]]})
    out = []
    for g in groups:
        pts = np.concatenate(g['cards']); c = np.array(g['feet']).mean(0)
        ground = float(pts[:, 1].min()); height = float(pts[:, 1].max() - ground)
        radius = float(np.linalg.norm(pts[:, [0, 2]] - c[[0, 2]], axis=1).max())
        out.append((c, ground, height, radius))
    return out


def author(fs, seed):
    rng = random.Random(seed)
    tris = []
    for c, ground, h, radius in tufts(fs):
        n = int(max(5, min(16, 5 + 6 * radius)))          # budget : ~3 triangles par brin
        for k in range(n):
            ang = rng.uniform(0, 2 * math.pi); rr = radius * .32 * math.sqrt(rng.random())
            dirx, dirz = math.cos(ang), math.sin(ang)
            base = Vector((c[0] + dirx * rr, ground - .04, c[2] + dirz * rr))
            hh = h * rng.uniform(.5, 1.0)
            lean = math.radians(rng.uniform(8, 32) + 18 * rr / max(radius, .1))
            reach = math.sin(lean) * hh * 1.1
            out = Vector((dirx, 0, dirz)); face = Vector((-dirz, 0, dirx))
            w0 = max(.018, min(.08, .045 * hh))
            rows = []
            for i, t in enumerate((0, .55, 1.0)):
                bend = reach * t * t + rng.uniform(-.03, .03) * hh * t
                p = base + Vector((0, hh * (t - .12 * t * t), 0)) + out * bend
                w = w0 * (1 - t) ** .8
                rows.append((p - face * w, p + face * w, 1 - t))
            for i in range(2):
                (a0, a1, va), (b0, b1, vb) = rows[i], rows[i + 1]
                if i < 1:
                    tris.append(((a0, a1, b1), ((0, va), (1, va), (1, vb))))
                    tris.append(((a0, b1, b0), ((0, va), (1, vb), (0, vb))))
                else:
                    tip = (b0 + b1) * .5
                    tris.append(((a0, a1, tip), ((0, va), (1, va), (.5, vb))))
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
                rec['vertices'].append({'p': [round(float(x), 3) for x in Wp[i, j]], 'uv': list(t[1][j]),
                                        'color_indices': [v['color'] for v in src['vertices']],
                                        'color_weights': [round(float(x), 4) for x in w], 'rgba': rgba})
            add.append(rec)
    return remove, add, worst


def preview(items, name, focus):
    reset()
    img = bpy.data.images.load(str(HERE / 'grass-blade.png'))
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


patch = {'description': 'Desert : herbe seche en vrais brins', 'remove': [], 'add': [],
         'new_textures': [{'name': BLADE_TEXTURE, 'page': 'remaster-desert-plants', 'width': 64, 'height': 256,
                           'rgba_file': str(HERE / 'grass-blade.rgba')}]}
before, after = [], []
for (tree, proto), lst in sorted(protos.items()):
    chosen = lst
    if MODE == 'apercu':
        chosen = [(i, fs) for i, fs in lst if np.linalg.norm(np.array([v['p'] for f in fs for v in f['vertices']]).mean(0)[[0, 2]] - FOCUS) < RADIUS]
        if not chosen: continue
    ref_inst, ref_fs = lst[0]
    tris = author(ref_fs, proto * 131 + tree)
    remove, add, err = records(ref_fs, tris, chosen)
    print(f'herbe tree {tree} proto {proto} : {len(chosen)} exemplaires, {len(ref_fs)} -> {len(tris)} triangles', flush=True)
    if MODE == 'apercu':
        for inst, fs in chosen:
            before.append((f'n{proto}_{inst}', [([Vector(v['p']) for v in f['vertices']], [(0, 0)] * 3) for f in fs], None))
        per = len(tris)
        for idx in range(len(chosen)):
            after.append((f'r{proto}_{idx}', [([Vector(x['p']) for x in r['vertices']], [tuple(x['uv']) for x in r['vertices']]) for r in add[idx * per:(idx + 1) * per]], None))
    else:
        patch['remove'] += remove; patch['add'] += add

if MODE == 'apercu':
    (HERE / 'preview').mkdir(exist_ok=True)
    pts = np.array([list(p) for _, tl, _ in after for ps, _ in tl for p in ps])
    lo, hi = pts.min(0), pts.max(0); c = (lo + hi) / 2
    focus = (float(c[0]), float(c[1]), float(c[2]), float(max(hi - lo)))
    preview([(a, b, 'carte') for a, b, _ in before], 'grass-avant.png', focus)
    preview([(a, b, 'brin') for a, b, _ in after], 'grass-apres.png', focus)
else:
    Path(OUT).write_text(json.dumps(patch, separators=(',', ':')))
    print('Enregistre :', len(patch['remove']), 'retires ->', len(patch['add']), 'ajoutes', flush=True)
