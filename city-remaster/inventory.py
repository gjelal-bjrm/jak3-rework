"""Read-only Spargus source audit; write only city-remaster/inventory.json.

Native exports are diagnostic outputs from the existing palace bridge. Their
draw_inventory is complete for positive texture IDs, but their faces retain the
bridge's palace-specific selection and are explicitly not a full city export.
"""
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image
import hashlib
import json
import re
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ORIGINAL = ROOT.parents[1] / 'active/jak3/data/decompiler_out/jak3'
LEVELS = {'wascitya': 'WCA', 'wascityb': 'WCB', 'waswide': 'WWD', 'wasdoors': 'WSD'}
BLOCK = [1735.0, 1820.0, -355.0, -290.0]


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def path_record(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def glb(path):
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    base = 28 + size
    cache = {}

    def accessor(i):
        if i not in cache:
            acc = doc['accessors'][i]
            view = doc['bufferViews'][acc['bufferView']]
            kind = {5126: 'f', 5125: 'I', 5123: 'H', 5121: 'B'}[acc['componentType']]
            width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[acc['type']]
            fmt = '<' + kind * width
            stride = view.get('byteStride', struct.calcsize(fmt))
            offset = base + view.get('byteOffset', 0) + acc.get('byteOffset', 0)
            cache[i] = [struct.unpack_from(fmt, raw, offset + j * stride)
                        for j in range(acc['count'])]
        return cache[i]

    usage = Counter()
    block_usage = Counter()
    for mesh in doc.get('meshes', []):
        for primitive in mesh['primitives']:
            name = doc['materials'][primitive.get('material', 0)].get('name', '<unnamed>')
            count = doc['accessors'][primitive['indices']]['count']
            usage[name] += count // 3
            if path.name == 'wascityb-background.glb':
                vertices = accessor(primitive['attributes']['POSITION'])
                indices = accessor(primitive['indices'])
                for j in range(0, len(indices) - 2, 3):
                    tri = [vertices[indices[j + k][0]] for k in range(3)]
                    if (max(v[0] for v in tri) >= BLOCK[0] and
                        min(v[0] for v in tri) <= BLOCK[1] and
                        max(v[2] for v in tri) >= BLOCK[2] and
                        min(v[2] for v in tri) <= BLOCK[3]):
                        block_usage[name] += 1
    return {
        **path_record(path),
        'mesh_names': [m.get('name') for m in doc.get('meshes', [])],
        'material_indexed_triangles': dict(usage),
        'triangles': sum(usage.values()),
        'skin_joint_counts': [len(s['joints']) for s in doc.get('skins', [])],
        'joint_names': [[doc['nodes'][j].get('name') for j in s['joints']]
                        for s in doc.get('skins', [])],
        'animation_names': [a.get('name') for a in doc.get('animations', [])],
        'market_block_aabb_overlap_triangles': dict(block_usage),
    }


def actor_record(actor, level):
    return {
        'level': level, 'aid': actor['aid'], 'etype': actor['etype'],
        'name': actor.get('lump', {}).get('name'), 'trans_m': actor['trans'][:3],
        'quat': actor.get('quat'), 'scale': actor.get('lump', {}).get('scale'),
        'art_name': actor.get('lump', {}).get('art-name'),
        'game_task': actor.get('game_task'),
        'kill_mask': actor.get('lump', {}).get('kill-mask'),
    }


def main():
    report = {'status': 'Source inventory and preparation only; no city assets installed',
              'levels': {}, 'textures': [], 'shared_pixel_images': {},
              'native': {}, 'source_actor_fire_candidates_all_maps': []}
    pixel_groups = defaultdict(list)
    models_by_name = defaultdict(list)
    for level, dgo in LEVELS.items():
        actors_path = ORIGINAL / 'entities' / (level + '-actors.json')
        actors = json.loads(actors_path.read_text()) if actors_path.exists() else []
        models = [glb(p) for p in sorted((ORIGINAL / 'levels' / level).glob('*.glb'))]
        report['levels'][level] = {
            'dgo': dgo, 'actors_source': path_record(actors_path),
            'actor_type_counts': dict(Counter(a['etype'] for a in actors)),
            'actors': [actor_record(a, level) for a in actors], 'models': models,
        }
        for model in models:
            models_by_name[Path(model['path']).name].append({
                'level': level, 'path': model['path'], 'sha256': model['sha256']})

    for page in sorted((ORIGINAL / 'textures').iterdir()):
        if not page.is_dir() or not page.name.startswith(tuple(x + '-' for x in LEVELS)):
            continue
        for path in sorted(page.glob('*.png')):
            with Image.open(path) as image:
                image = image.convert('RGBA')
                digest = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
                record = {**path_record(path), 'page': page.name, 'name': path.stem,
                          'size': list(image.size), 'alpha': list(image.getchannel('A').getextrema()),
                          'pixels_sha256': digest}
            report['textures'].append(record)
            pixel_groups[digest].append(page.name + '/' + path.name)
    report['shared_pixel_images'] = {k: v for k, v in pixel_groups.items() if len(v) > 1}
    report['shared_model_names'] = {k: v for k, v in models_by_name.items() if len(v) > 1}

    for level in ('wascitya', 'wascityb'):
        path = HERE / (level + '-native.json')
        native = json.loads(path.read_text())
        groups = defaultdict(Counter)
        for draw in native['draw_inventory']:
            if draw['geom'] == 0:
                groups[(draw['type'], draw['tree'], draw['proto'])][draw['material']] += draw['triangles']
        nearby = defaultdict(lambda: {'materials': set(), 'triangles': 0})
        for face in native['faces']:
            if face['geom'] != 0 or level != 'wascityb':
                continue
            vs = [v['p'] for v in face['vertices']]
            if not (max(v[0] for v in vs) >= BLOCK[0] and min(v[0] for v in vs) <= BLOCK[1]
                    and max(v[2] for v in vs) >= BLOCK[2] and min(v[2] for v in vs) <= BLOCK[3]):
                continue
            key = (face['tree_type'], face['tree'], face['proto'], face['instance'])
            nearby[key]['triangles'] += 1
            nearby[key]['materials'].add(face['material'])
        report['native'][level] = {
            'source_fr3': path_record(ROOT / 'data/out/jak3/fr3' / (level + '.fr3')),
            'diagnostic_export': path_record(path),
            'geometry_face_selection': 'Incomplete: palace-specific bridge filters still active',
            'draw_inventory_scope': 'All TFRAG/TIE positive-texture draws; shrub limited by palace filters',
            'geom0_groups': [{'tree_type': key[0], 'tree': key[1], 'proto': key[2],
                             'triangles_by_material': dict(mats)} for key, mats in sorted(groups.items())],
            'market_block_partial_instances': [
                {'tree_type': k[0], 'geom': 0, 'tree': k[1], 'proto': k[2], 'instance': k[3],
                 'triangles': v['triangles'], 'materials': sorted(v['materials'])}
                for k, v in sorted(nearby.items())],
        }

    # Static source candidates only. Dynamic damage/projectile fire still needs a
    # launch-controller hook; this name search must never become a global kill list.
    for path in sorted((ORIGINAL / 'entities').glob('*-actors.json')):
        level = path.name[:-len('-actors.json')]
        for actor in (json.loads(path.read_text()) or []):
            name = actor.get('lump', {}).get('art-name', '')
            if re.search(r'fire|flame|torch|gaslamp|burn', name, re.I):
                report['source_actor_fire_candidates_all_maps'].append(actor_record(actor, level))
    candidates = report['source_actor_fire_candidates_all_maps']
    report['city_fire_counts'] = dict(Counter(a['art_name'] for a in candidates if a['level'] in LEVELS))
    report['all_maps_fire_group_counts'] = dict(Counter(a['art_name'] for a in candidates))

    actors = report['levels']['wascityb']['actors']
    block_actors = [a for a in actors if BLOCK[0] <= a['trans_m'][0] <= BLOCK[1]
                    and BLOCK[2] <= a['trans_m'][2] <= BLOCK[3]]
    report['first_block'] = {
        'name': 'WCB fruit market, ground, walls and immediate vegetation', 'level': 'wascityb',
        'dgo': 'WCB.DGO', 'shared_dgo': 'WWD.DGO',
        'xz_bounds_m': BLOCK, 'actors': block_actors,
        'actor_type_counts': dict(Counter(a['etype'] for a in block_actors)),
        'preview_position_m': [1768.0, 34.0, -347.0],
        'preview_position_status': 'Proposed from actor positions; not yet validated live',
        'actor_entry': {'aid': 42091, 'model_control': 'cty-fruit-stand-lod0'},
    }
    (HERE / 'inventory.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'levels': {k: sum(v['actor_type_counts'].values()) for k, v in report['levels'].items()},
                      'texture_placements': len(report['textures']), 'unique_pixels': len(pixel_groups),
                      'first_block_actors': len(block_actors), 'city_fire_counts': report['city_fire_counts'],
                      'all_map_fire_candidates': len(candidates)}, indent=2))


if __name__ == '__main__':
    main()
