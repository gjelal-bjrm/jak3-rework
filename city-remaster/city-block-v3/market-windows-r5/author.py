"""Ouvre quatre fenetres habitees dans des maisons autour du marche de Spargus (WCB).

A lancer dans Blender en arriere-plan :
  blender.exe --background --python author.py

Reprend la methode du lot R4 (architecture-expanded-r4/author.py) : import des
triangles natifs, decoupe rectangulaire bornee, encadrement en volume, export
d'un patch remove/add pour palace_mesh_bridge. N'ecrit aucune donnee du jeu.
"""
from pathlib import Path
from collections import Counter
import importlib.util, inspect, json, hashlib, struct, bpy
from mathutils import Vector

H = Path(__file__).resolve().parent
A = H.parent / 'architecture'
spec = importlib.util.spec_from_file_location('historical_author', A / 'author_buildings.py')
author = importlib.util.module_from_spec(spec); spec.loader.exec_module(author)
NativeMesh = author.NativeMesh

# Decoupe bornee (identique a R4) : les triangles natifs entiers hors du rectangle
# de l'ouverture sont conserves tels quels.
bounded_cut_source = inspect.getsource(author.cut_windows).replace(
    'if min(z)>2 or max(z)<-4:nxt.append(poly);continue',
    "xs=[p[2].x for p in pp];ys=[p[2].y for p in pp]\n    if min(z)>2 or max(z)<-4 or max(xs)<-w['width']/2 or min(xs)>w['width']/2 or max(ys)<-w['height']/2 or min(ys)>w['height']/2:nxt.append(poly);continue")
exec(compile(bounded_cut_source, 'bounded_window_cutter', 'exec'), author.__dict__)


def read(p): return json.loads(Path(p).read_text())
def write(p, j): Path(p).write_text(json.dumps(j, indent=2) + '\n')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(f): return tuple(f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'stream_index'))


def signature(f):
    pts = [tuple(struct.unpack('f', struct.pack('f', x))[0] for x in v['p']) for v in f['vertices']]
    return (f['tree_type'], f['geom'], f['tree'], f['draw'], f['group'], min(tuple(pts[i:] + pts[:i]) for i in range(3)))


def remove_record(f):
    return {**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index')},
            'original_positions': [v['p'] for v in f['vertices']]}


def new_frame(native, w):
    """Encadrement en volume : tableaux epais, appui large et linteau, dans la pierre du batiment."""
    c, r, u, n = author.frame(w); width = w['width']; height = w['height']; material = w['frame_material']
    thickness = .28
    for sign in (-1, 1):
        author.box(native, c + r * sign * (width / 2 + thickness / 2) - n * .18, r, u, n, (thickness, height + .55, .82), material, .075)
    author.box(native, c - u * (height / 2 + .17) + n * .10, r, u, n, (width + thickness * 2 + .24, .34, 1.0), material, .08)   # appui
    author.box(native, c + u * (height / 2 + .17) - n * .04, r, u, n, (width + thickness * 2 + .14, .34, .85), material, .08)   # linteau
    author.box(native, c + u * (height / 2 + .46) - n * .10, r, u, n, (width + .5, .2, .66), material, .06)                     # corniche
    for sign in (-1, 1):   # deux consoles sous l'appui
        author.box(native, c + r * sign * (width / 2 - .25) - u * (height / 2 + .48) + n * .05, r, u, n, (.3, .34, .6), material, .05)


def difference(before, after):
    old = Counter(signature(f) for f in before); new = Counter(signature(f) for f in after)
    rem = old - new; add = new - old; removed = []; added = []
    for f in before:
        k = signature(f)
        if rem[k]: removed.append(f); rem[k] -= 1
    for f in after:
        k = signature(f)
        if add[k]: added.append(f); add[k] -= 1
    return removed, added


def main():
    author.reset()
    source = read(H / 'native-market.json'); windows = read(H / 'new-window-specs.json')
    patch = {'level': 'wascityb', 'source_fr3': source['source_fr3'], 'preserve_bvh': True, 'remove': [], 'add': []}
    report = {'status': 'authored', 'source_fr3': source['source_fr3'], 'author_sha256': sha(__file__),
              'historical_author': str(A / 'author_buildings.py'), 'historical_author_sha256': sha(A / 'author_buildings.py'), 'windows': []}
    for w in windows:
        for lod in range(4):
            originals = [f for f in source['faces'] if f['tree_type'] == 'tie' and f['tree'] == w['tree']
                         and f['instance'] in w['building_native_instances'] and f['geom'] == lod]
            groups = {(f['tree_type'], f['tree'], f['draw'], f['group']) for f in originals}
            target = [f for f in source['faces'] if f['geom'] == lod and (f['tree_type'], f['tree'], f['draw'], f['group']) in groups]
            assert target, (w['id'], lod)
            assert w['frame_material'] in {f['material'] for f in target}, (w['id'], lod, 'materiau d encadrement absent du batiment')
            native = NativeMesh(w['id'] + ' LOD' + str(lod), target)
            cut = author.cut_windows(native, [w]); new_frame(native, w)
            _, after, _ = native.records(target); valid = []
            for f in after:
                ps = [Vector(v['p']) for v in f['vertices']]; n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
                if n.length < 1e-8: continue
                n.normalize()
                for v in f['vertices']:
                    v['normal'] = list(n); weights = [max(0, x) for x in v['color_weights']]; v['color_weights'] = [x / sum(weights) for x in weights]
                valid.append(f)
            rem, add = difference(target, valid)
            # Un triangle ajoute doit appartenir a un groupe de dessin deja touche par la decoupe
            # (exigence de l'audit de preservation). On le rattache au groupe retire de meme materiau.
            material_of = {(f['draw'], f['group']): f['material'] for f in target}
            removed_groups = {(f['draw'], f['group']) for f in rem}
            by_material = {}
            for f in rem: by_material.setdefault(f['material'], (f['draw'], f['group']))
            assert w['frame_material'] in by_material, (w['id'], lod, 'le materiau d encadrement n est pas parmi les faces decoupees', sorted(by_material))
            remapped = 0
            for f in add:
                if (f['draw'], f['group']) not in removed_groups:
                    material = material_of.get((f['draw'], f['group']), w['frame_material'])
                    f['draw'], f['group'] = by_material.get(material, by_material[w['frame_material']]); remapped += 1
            patch['remove'].extend(remove_record(f) for f in rem); patch['add'].extend(add)
            report['windows'].append({'id': w['id'], 'lod': lod, 'native_instances': w['building_native_instances'], 'cut_polygons': cut,
                                      'removed': len(rem), 'added': len(add), 'remapped': remapped, 'groups': sorted({(f['tree'], f['draw'], f['group']) for f in rem + add})})
            native.obj.location = (native.origin.x, -native.origin.z, native.origin.y); native.obj.hide_set(lod != 0); native.obj.hide_render = lod != 0
    assert len({key(f) for f in patch['remove']}) == len(patch['remove'])
    report['faces_removed'] = len(patch['remove']); report['faces_added'] = len(patch['add'])
    write(H / 'wascityb-patch.json', patch); write(H / 'author-report.json', report)
    anchors = [{k: w[k] for k in ('id', 'center', 'normal', 'right', 'up', 'width', 'height', 'wall_depth', 'room_depth',
                                  'building_native_instance', 'building_native_instances', 'tree', 'level', 'inhabited',
                                  'street_ground_y', 'street_camera', 'region')} for w in windows]
    write(H / 'window-anchors.json', anchors)
    bpy.ops.wm.save_as_mainfile(filepath=str(H / 'market-houses.blend'))
    print(json.dumps({k: v for k, v in report.items() if k != 'windows'}, indent=2))
    for entry in report['windows']:
        print(entry['id'], 'LOD', entry['lod'], 'coupes', entry['cut_polygons'], 'retires', entry['removed'], 'ajoutes', entry['added'])


if __name__ == '__main__':
    main()
