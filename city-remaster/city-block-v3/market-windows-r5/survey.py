"""Releve des facades autour de la place du marche (WCB) pour de nouvelles fenetres habitees.

Lecture seule. A lancer avec le Python de Blender (module mathutils) :
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" survey.py

Etape 1 : batiments candidats (objets TIE avec de grandes surfaces murales verticales).
Etape 2 : pour chaque batiment, points de facade ou une ouverture 3,2 x 2,8 m
          tient dans un mur plan, avec 3,5 m libres derriere et le sol devant.
Ecrit survey.json et affiche un resume.
"""
from pathlib import Path
from collections import defaultdict
import json, math, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

H = Path(__file__).resolve().parent
SQUARE = Vector((1775.0, 30.0, -325.0))      # centre approximatif de la place du marche
WALL_MATERIALS = {'wascity-stucco-wall-bleached-01', 'wascity-stone-plain-wall-3', 'wascitya-stone-top',
                  'wascity-stone-wall', 'wascity-stucco-wall', 'wascity-mud-wall', 'wascity-plaster-wall'}
WIDTH, HEIGHT, ROOM_DEPTH = 3.2, 2.8, 3.5

data = json.loads((H / 'native-market.json').read_text())
faces = [f for f in data['faces'] if f['geom'] == 0]


def tri(f):
    return [Vector(v['p']) for v in f['vertices']]


def build_tree(fs):
    ps, tris = [], []
    for f in fs:
        i = len(ps); ps.extend(tri(f)); tris.append((i, i + 1, i + 2))
    return BVHTree.FromPolygons(ps, tris, all_triangles=True)


# ---- Etape 1 : batiments -----------------------------------------------------
by_instance = defaultdict(list)
for f in faces:
    if f['tree_type'] == 'tie' and f['instance'] >= 0:
        by_instance[(f['tree'], f['instance'])].append(f)

buildings = []
for key, fs in by_instance.items():
    wall_area = 0.0; mats = defaultdict(float); pts = []
    for f in fs:
        ps = tri(f); pts.extend(ps)
        n = (ps[1] - ps[0]).cross(ps[2] - ps[0]); area = n.length / 2
        if area <= 0: continue
        if abs(n.normalized().y) < 0.35 and (f['material'] in WALL_MATERIALS or 'stucco' in f['material'] or 'stone-plain' in f['material'] or 'stone-bricks' in f['material'] or 'stone-bottom' in f['material']):
            wall_area += area; mats[f['material']] += area
    if wall_area < 15: continue
    lo = Vector([min(p[a] for p in pts) for a in range(3)]); hi = Vector([max(p[a] for p in pts) for a in range(3)])
    if hi.y - lo.y < 4.5: continue
    centre = (lo + hi) / 2
    buildings.append({'tree': key[0], 'instance': key[1], 'wall_area': round(wall_area, 1),
                      'bbox_min': [round(v, 1) for v in lo], 'bbox_max': [round(v, 1) for v in hi],
                      'distance_to_square': round((Vector((centre.x, SQUARE.y, centre.z)) - SQUARE).length, 1),
                      'materials': sorted(mats.items(), key=lambda kv: -kv[1])[:3], 'faces': len(fs)})
buildings.sort(key=lambda b: b['distance_to_square'])
print(f"{len(buildings)} batiments candidats (surface murale >= 30 m2, hauteur >= 4,5 m)")
for b in buildings[:25]:
    print(f"  tree {b['tree']} inst {b['instance']:4d}  dist {b['distance_to_square']:6.1f} m  murs {b['wall_area']:7.1f} m2  "
          f"X {b['bbox_min'][0]:.0f}..{b['bbox_max'][0]:.0f}  Y {b['bbox_min'][1]:.0f}..{b['bbox_max'][1]:.0f}  Z {b['bbox_min'][2]:.0f}..{b['bbox_max'][2]:.0f}  "
          f"{b['materials'][0][0] if b['materials'] else ''}")

# ---- Etape 2 : facades --------------------------------------------------------
all_tree = build_tree(faces)
ground_faces = [f for f in faces if f['tree_type'] == 'tfrag']
ground = build_tree(ground_faces)
results = []
for b in buildings[:25]:
    key = (b['tree'], b['instance']); house = by_instance[key]
    house_ids = {id(f) for f in house}
    is_house = lambda idx: id(faces[idx]) in house_ids
    pts = [p for f in house for p in tri(f)]
    centre = Vector([(min(p[a] for p in pts) + max(p[a] for p in pts)) / 2 for a in range(3)])
    candidates = []
    for f in house:
        ps = tri(f); norm = (ps[1] - ps[0]).cross(ps[2] - ps[0]); area = norm.length / 2
        if area < 4 or abs(norm.normalized().y) > 0.35: continue
        c = sum(ps, Vector()) / 3; n = Vector((norm.x, 0, norm.z)).normalized()
        if (c - centre).dot(n) < 0: n = -n                      # normale vers l'exterieur du batiment
        for step in (5, 9, 14):
            foot = c + n * step; foot.y = 95
            hit = ground.ray_cast(foot, Vector((0, -1, 0)), 150)
            if hit[0] is None: continue
            gy = hit[0].y
            for dy in (3.1, 3.7, 4.4):
                outside = c + n * step; outside.y = gy + dy
                hit = all_tree.ray_cast(outside, -n, step + 3)
                if hit[0] is None or not is_house(hit[2]): continue
                c2 = hit[0]; r = Vector((n.z, 0, -n.x)); ok = True
                for x in (-.4, 0, .4):
                    for y in (-.4, 0, .4):
                        p = c2 + r * x * WIDTH + Vector((0, y * HEIGHT, 0))
                        hp = all_tree.ray_cast(p + n * step, -n, step + 3)
                        if hp[0] is None or not is_house(hp[2]) or (hp[0] - p).length > .6: ok = False
                if not ok: continue
                blockers = []
                for x in (-.35, 0, .35):
                    for y in (-.35, 0, .35):
                        origin = c2 + r * x * WIDTH + Vector((0, y * HEIGHT, 0)) - n * .15
                        hp = all_tree.ray_cast(origin, -n, ROOM_DEPTH)
                        if hp[0] is not None and not is_house(hp[2]): blockers.append(faces[hp[2]]['material'])
                faces_square = n.dot((SQUARE - c2).normalized())   # > 0 : la facade regarde vers la place
                candidates.append({'tree': key[0], 'instance': key[1], 'center': [round(v, 3) for v in c2], 'normal': [round(v, 4) for v in n],
                                   'ground_y': round(gy, 3), 'sill_above_ground': round(c2.y - HEIGHT / 2 - gy, 2),
                                   'camera': [round(v, 2) for v in (c2 + n * step + Vector((0, 1.7 - dy, 0)))],
                                   'blockers': blockers, 'faces_square': round(faces_square, 2), 'distance': step, 'area': round(area, 1)})
    unique = {tuple(round(v, 1) for v in x['center'] + x['normal']): x for x in candidates}
    candidates = sorted(unique.values(), key=lambda x: (len(x['blockers']), -x['faces_square'], abs(x['sill_above_ground'] - 1.9)))
    results.append({'building': b, 'candidates': candidates[:12]})
    best = candidates[0] if candidates else None
    print(f"tree {key[0]} inst {key[1]:4d} : {len(candidates):3d} points de facade ; meilleur : "
          + (f"centre {best['center']} normale {best['normal']} appui {best['sill_above_ground']} m, bloqueurs {len(best['blockers'])}, vers place {best['faces_square']}" if best else "aucun"))
(H / 'survey.json').write_text(json.dumps(results, indent=2))
print('survey.json ecrit')
