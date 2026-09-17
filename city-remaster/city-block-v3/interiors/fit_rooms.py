"""Mesure l'espace interieur reel derriere chaque fenetre et en deduit l'echelle de la piece.

Blender en arriere-plan (mathutils) :  blender.exe --background --python fit_rooms.py

Depuis des points situes dans la piece, juste derriere l'ouverture, on lance des rayons vers la
gauche, la droite, le fond et le haut jusqu'a la premiere surface native (murs et toit du
batiment). Les degagements obtenus donnent l'echelle a appliquer a la piece homes/ (4,8 m de
large, 3,6 m de profondeur avec le mur du fond, 0,95 m de couloir) pour qu'elle ne ressorte pas
du batiment. Ecrit room-fit.json : {id: {"scale": [sx, 1, sz], "clearance": {...}}}.
Une piece dont l'echelle tomberait sous 0,6 est signalee : la fenetre est mal placee.
"""
from pathlib import Path
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
anchors = json.loads((HERE / 'window-anchors-final.json').read_text(encoding='utf-8'))
HALF_W, DEPTH_TOTAL, TOP = 2.4, 3.6 + .95, 3.1     # demi-largeur, profondeur avec couloir, plafond (dalle comprise)
MARGIN = .15


def load_tree(path):
    data = json.loads(Path(path).read_text())
    pts = []; tris = []
    for f in data['faces']:
        i = len(pts); pts.extend(Vector(v['p']) for v in f['vertices']); tris.append((i, i + 1, i + 2))
    return BVHTree.FromPolygons(pts, tris, all_triangles=True), len(tris)


def clearance(tree, origin, direction, limit):
    hit = tree.ray_cast(origin, direction, limit)
    return hit[3] if hit[0] is not None else limit


def main():
    results = {}
    for w in anchors:
        tree, count = load_tree(HERE / 'fit' / f"native-{w['id']}.json")
        n = Vector(w['normal']).normalized(); r = Vector(w['right']).normalized(); up = Vector((0, 1, 0))
        origin = Vector(w['center']) - n * .54; origin.y -= w['height'] * .5 + .1
        world = lambda x, y, z: origin + r * x + up * y + n * z
        # points de depart : dans l'ouverture, un peu en retrait, a deux hauteurs et trois largeurs
        starts = [(x, y, z) for x in (-1.0, 0.0, 1.0) for y in (.6, 1.8) for z in (-.6, -1.4)]
        left = min(clearance(tree, world(x, y, z), -r, 12) + x for x, y, z in starts)       # distance depuis x=0
        right = min(clearance(tree, world(x, y, z), r, 12) - x for x, y, z in starts)
        back = min(clearance(tree, world(x, y, z), -n, 12) - z for x, y, z in starts)       # distance depuis z=0
        ceiling = min(clearance(tree, world(x, y, z), up, 12) + y for x, y, z in starts)     # hauteur depuis y=0
        sx = min(1.0, (min(left, right) - MARGIN) / HALF_W)
        sz = min(1.0, (back - MARGIN) / DEPTH_TOTAL)
        flag = 'A REVOIR' if min(sx, sz) < .6 else ('reduite' if min(sx, sz) < 1 else 'entiere')
        results[w['id']] = {'scale': [round(max(sx, .3), 3), 1, round(max(sz, .3), 3)],
                            'clearance': {'gauche': round(left, 2), 'droite': round(right, 2), 'fond': round(back, 2), 'plafond': round(ceiling, 2)},
                            'ceiling_ok': ceiling >= TOP, 'status': flag, 'native_triangles': count}
        print(f"{w['id']:28s} gauche {left:5.2f} droite {right:5.2f} fond {back:5.2f} plafond {ceiling:5.2f}  -> echelle x {sx:.2f} z {sz:.2f}  {flag}"
              + ('' if ceiling >= TOP else '  (plafond natif bas)'), flush=True)
    (HERE / 'room-fit.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')


main()
