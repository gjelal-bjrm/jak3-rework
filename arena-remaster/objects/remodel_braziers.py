"""Braseros de l'arene de Spargus (TIE prototype 14, 14 exemplaires, 4 niveaux de detail) remodeles dans Blender.

Lancement : blender.exe --background --python arena-remaster/objects/remodel_braziers.py
Entree : braziers-native.json (export du bridge). Sortie : braziers-patch.json (remove/add natifs),
braziers-report.json, apercu braziers-preview.png et .blend du premier exemplaire.

Forme fidele a l'original (coupe de bronze bleu-vert a 16 pans, rebord cylindrique evase, braises au centre)
mais construite finement : profil tourne lisse, 16 cotes forgees qui gardent les pans d'origine, deux bandes
en relief, rebord a levre roulee et perle basse, 32 rivets. Les braises (wstd-torchbowl-coal-01) restent
exactement a leur place : les flammes natives reposent dessus. Memes textures et UV d'origine (projetees
depuis les faces natives), memes couleurs de sommets (palettes de l'heure du jour).
"""
import sys, json, math
from pathlib import Path
from collections import defaultdict
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'models-v1'))
from blender_common import *          # bpy, bmesh, Vector, NativeMesh, reset, render_asset
OUT = Path(__file__).resolve().parent  # (blender_common redefinit HERE)

faces = json.loads((OUT / 'braziers-native.json').read_text())['faces']
BOWL, RIM = 'wstd-torchbowl-01', 'wstd-torchbowl-02'
patch = {'description': 'Arene : braseros remodeles (coupe tournee, cotes, bandes, levre, rivets) ; braises intactes',
         'remove': [], 'add': []}
reports = []

# Profil d'origine (hauteur h au-dessus du fond, rayon r), mesure sur les faces natives :
#   coupe : (0,0) (.05,.52) (.09,1.03) (.40,2.03) (1.55,3.78) (3.29,4.94) (5.03,5.33)
#   rebord : (5.03,5.33) -> (5.83,6.51) -> (6.96,6.51) -> levre interieure (5.69,4.47) au niveau des braises
BOWL_PROFILE = [(0.0, 0.0), (0.05, 0.52), (0.09, 1.03), (0.40, 2.03), (1.55, 3.78), (3.29, 4.94), (5.03, 5.33)]


def chaikin(points, iterations=3):
    """Lissage par coupe des coins : reste dans l'enveloppe du profil (pas de depassement), extremites fixes."""
    pts = [Vector(p) for p in points]
    for _ in range(iterations):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [a.lerp(b, .25), a.lerp(b, .75)]
        out.append(pts[-1]); pts = out
    return pts


def piecewise(x, table):
    """Interpolation lineaire dans une table (x croissant) ; bornee aux extremites."""
    if x <= table[0][0]: return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1: return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


# Plaquage d'origine, mesure sur les faces natives (u tourne a l'envers de l'angle) :
#   coupe : u = -angle/90 deg (4 repetitions), v selon la hauteur ;
#   rebord : u = -angle/45 deg (8 repetitions) ; evasement v 1 -> 0,5 ; bande verticale 0,5 -> 0 ;
#            rebord interieur : v 1 (haut) -> 0 (levre, au niveau des braises).
BOWL_V = [(0.09, 1.0), (0.40, .75), (1.55, .5), (3.29, .25), (5.03, 0.0)]


def build(centre, base_y, phase, segments=48, smooth=2, rivets=True):
    """Maillage (sommets monde, uv, faces, materiau par face) d'un brasero."""
    verts, uvs, polys, mats = [], [], [], []

    def ring(h, r, v, period, relief=None):
        row = []
        for j in range(segments + 1):          # colonne de couture dupliquee (u continu)
            th = 2 * math.pi * j / segments
            world_th = th + phase0
            rr = r + (relief(world_th) if relief else 0.0)
            row.append(len(verts))
            verts.append((centre[0] + rr * math.cos(world_th), base_y + h, centre[1] + rr * math.sin(world_th)))
            uvs.append((-(math.degrees(world_th) - math.degrees(phase0)) / period, v))
        return row

    def band(rows, mat):
        for a, b in zip(rows, rows[1:]):
            for j in range(segments):
                polys.append((a[j], a[j + 1], b[j + 1], b[j])); mats.append(mat)

    phase0 = phase
    # cotes forgees : 16 aretes legerement saillantes sur les pans d'origine (profil doux)
    def ribs(th):
        x = ((th - phase) * 16 / (2 * math.pi)) % 1.0
        return .045 * math.exp(-((x - .5) / .07) ** 2) - .012
    # coupe
    rows = []
    for p in chaikin(BOWL_PROFILE, smooth):
        h, r = p.x, max(p.y, 0.0)          # BOWL_PROFILE = (hauteur, rayon) : ne pas inverser
        bump = .06 * (math.exp(-((h - 1.55) / .09) ** 2) + math.exp(-((h - 3.29) / .09) ** 2))
        rows.append(ring(h, r + bump, piecewise(h, BOWL_V), 90.0, ribs if r > .5 else None))
    band(rows, BOWL)
    # rebord : perle basse, evasement, bande verticale, levre roulee, rebord interieur jusqu'aux braises
    outer = [(5.03, 5.33), (5.10, 5.47), (5.12, 5.58), (5.22, 5.72), (5.55, 6.18), (5.83, 6.51), (5.95, 6.55),
             (6.40, 6.55), (6.80, 6.55), (6.90, 6.62), (6.98, 6.62), (7.05, 6.52)]
    inner = [(7.02, 6.38), (6.96, 6.30), (6.30, 5.60), (5.85, 4.78), (5.69, 4.47)]
    rows = []
    for h, r in outer:
        v = piecewise(h, [(5.03, 1.0), (5.83, .5), (6.96, 0.0)])
        rows.append(ring(h, r, v, 45.0))
    for h, r in inner:
        rows.append(ring(h, r, piecewise(r, [(4.47, 0.0), (6.38, 1.0)]), 45.0))
    band(rows, RIM)
    # rivets : 32 demi-spheres sur la bande verticale (uv : zone unie de la bande)
    for j in range(32 if rivets else 0):
        th = phase + 2 * math.pi * (j + .5) / 32
        cx, cz, cy = centre[0] + 6.55 * math.cos(th), centre[1] + 6.55 * math.sin(th), base_y + 6.38
        n = Vector((math.cos(th), 0, math.sin(th))); t = Vector((-math.sin(th), 0, math.cos(th))); up = Vector((0, 1, 0))
        u0 = -(math.degrees(th) - math.degrees(phase)) / 45.0
        top = len(verts); verts.append(tuple(Vector((cx, cy, cz)) + n * .09)); uvs.append((u0, .22))
        ringv = []
        for k in range(8):
            a = 2 * math.pi * k / 8
            p = Vector((cx, cy, cz)) + (t * math.cos(a) + up * math.sin(a)) * .085 + n * .035
            ringv.append(len(verts)); verts.append(tuple(p)); uvs.append((u0 + .02 * math.cos(a), .22 + .02 * math.sin(a)))
        for k in range(8):
            polys.append((top, ringv[k], ringv[(k + 1) % 8])); mats.append(RIM)
    return verts, uvs, polys, mats


def targets_for(instance):
    out = defaultdict(list)
    for f in faces:
        if f['proto'] == 14 and f.get('instance') == instance and f['material'] in (BOWL, RIM):
            out[f['geom']].append(f)
    return out


instances = sorted({f.get('instance') for f in faces if f['proto'] == 14 and f['geom'] == 0})
for number, instance in enumerate(instances):
    targets = targets_for(instance)
    base = targets[0]
    pts = [v['p'] for f in base for v in f['vertices']]
    ymin = min(p[1] for p in pts)
    bottom = [p for p in pts if p[1] < ymin + .02]
    centre = (sum(p[0] for p in bottom) / len(bottom), sum(p[2] for p in bottom) / len(bottom))
    # phase des pans d'origine : angle d'un sommet de l'anneau a 3,78 m de rayon
    ring_pts = [p for p in pts if abs(p[1] - ymin - 1.55) < .05]
    phase = math.atan2(ring_pts[0][2] - centre[1], ring_pts[0][0] - centre[0]) if ring_pts else 0.0
    reset()
    asset = NativeMesh(f'Brasero_{instance}', base)
    def make_mesh(label, **kw):
        verts, uvs, polys, mats = build(centre, ymin, phase, **kw)
        mesh = bpy.data.meshes.new(label)
        mesh.from_pydata([asset.local(p) for p in verts], [], polys); mesh.update()
        for m in asset.obj.data.materials: mesh.materials.append(m)
        uvl = mesh.uv_layers.new(name='UVMap')
        for poly, mat in zip(mesh.polygons, mats):
            poly.material_index = asset.materials.index(mat)
            for loop in poly.loop_indices:
                u, v = uvs[mesh.loops[loop].vertex_index]; uvl.data[loop].uv = (u, 1 - v)
        bm = bmesh.new(); bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=list(bm.faces)); bm.normal_update(); bm.to_mesh(mesh); bm.free()
        for p in mesh.polygons: p.use_smooth = True
        return mesh
    high = make_mesh(f'Brasero HD {instance}')
    low = make_mesh(f'Brasero lointain {instance}', segments=24, smooth=1, rivets=False)
    info = {'instance': instance, 'centre': centre, 'original_triangles': {}, 'new_triangles': {}}
    for lod, tfaces in sorted(targets.items()):
        asset.obj.data = low if lod == 3 else high      # niveau 3 : le plus lointain
        remove, add, dist = asset.records(tfaces)
        patch['remove'].extend(remove); patch['add'].extend(add)
        info['original_triangles'][lod] = len(tfaces); info['new_triangles'][lod] = len(add)
    reports.append(info)
    print('brasero', instance, info['original_triangles'][0], '->', info['new_triangles'][0], flush=True)
    asset.obj.data = high
    if number == 0:
        render_asset(asset.obj, OUT / 'braziers-preview.png', view=(4, -7, 3.5))
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'brazier-remodel.blend'))

(OUT / 'braziers-patch.json').write_text(json.dumps(patch, separators=(',', ':')))
(OUT / 'braziers-report.json').write_text(json.dumps(reports, indent=2))
print('Enregistre :', len(patch['remove']), 'retires ->', len(patch['add']), 'ajoutes', flush=True)
