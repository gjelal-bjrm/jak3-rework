"""Associate native palm crowns with market trunks and export complete plant instances."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def identity(record):
    return tuple(record[k] for k in ('tree_type', 'geom', 'tree', 'instance'))


def face_key(record):
    return tuple(record[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'stream_index'))


def source_id(key):
    return dict(zip(('tree_type', 'geom', 'tree', 'instance'), key))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def distance_to_triangle(p, a, b, c):
    ab, ac, ap = sub(b, a), sub(c, a), sub(p, a)
    aa, bb, cc = dot(ab, ab), dot(ab, ac), dot(ac, ac)
    denominator = aa * cc - bb * bb
    if denominator > 1e-15:
        u = (cc * dot(ap, ab) - bb * dot(ap, ac)) / denominator
        v = (aa * dot(ap, ac) - bb * dot(ap, ab)) / denominator
        if u >= 0 and v >= 0 and u + v <= 1:
            residual = tuple(ap[i] - u * ab[i] - v * ac[i] for i in range(3))
            return math.sqrt(dot(residual, residual))
    best = math.inf
    for start, end in ((a, b), (b, c), (c, a)):
        edge, delta = sub(end, start), sub(p, start)
        length = dot(edge, edge)
        t = max(0, min(1, dot(edge, delta) / length)) if length else 0
        residual = tuple(delta[i] - t * edge[i] for i in range(3))
        best = min(best, math.sqrt(dot(residual, residual)))
    return best


def geometry(faces):
    # Only vertices referenced by real exported triangles contribute; no helper vertices.
    points = [v['p'] for f in faces for v in f['vertices']]
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    center = [(a + b) / 2 for a, b in zip(low, high)]
    return {
        'indexed_aabb_min_m': low, 'indexed_aabb_max_m': high,
        'indexed_center_m': center,
        'indexed_radius_m': max(math.dist(p, center) for p in points),
        'indexed_radius_xz_m': max(math.hypot(p[0] - center[0], p[2] - center[2]) for p in points),
    }


def main():
    subprocess.run([sys.executable, str(HERE / 'export_block.py'),
                    '--selection', str(HERE / 'all-plants-selection.json'),
                    '--output', str(HERE / 'all-plants-native.json')], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
    document, block = read('all-plants-native.json'), read('market-block-native.json')
    groups = defaultdict(list)
    for face in document['faces']:
        groups[identity(face)].append(face)
    instances = {identity(r): r for r in document['instance_inventory']}
    seeds = {identity(f) for f in block['faces'] if f['material'] in document['selection']['materials']}
    trunk_seeds = sorted(k for k in seeds if k[0] == 'tie' and k[1] == 0)
    shrub_seeds = sorted(k for k in seeds if k[0] == 'shrub')
    all_trunks = {k: faces for k, faces in groups.items() if k[0] == 'tie' and k[1] == 0}
    attached = defaultdict(list)
    distances = {}
    for wind, info in instances.items():
        if wind[0] != 'tie_wind' or wind[1] != 0:
            continue
        # Native wind origins sit at crown/old-frond attachments, not at trunk roots.
        candidates = sorted((min(distance_to_triangle(info['origin_m'], *[v['p'] for v in f['vertices']])
                                 for f in faces), trunk)
                            for trunk, faces in all_trunks.items())
        nearest, trunk = candidates[0]
        if trunk in trunk_seeds and nearest <= 2.0:
            assert candidates[1][0] - nearest > .5, 'Ambiguous crown/trunk association'
            attached[trunk].append(wind)
            distances[wind] = {'distance_to_indexed_trunk_m': nearest,
                               'next_trunk_distance_m': candidates[1][0]}

    selected = set(shrub_seeds)
    palms = []
    for trunk in trunk_seeds:
        crown = sorted(attached[trunk])
        part_materials = Counter(groups[k][0]['material'] for k in crown)
        assert part_materials == {'wascity-palm-leaf-worn': 3, 'wascity-palm-beard': 4}, (trunk, part_materials)
        parts = [trunk, *crown]
        lod_keys = sorted(k for k in groups if any(k[0] == p[0] and k[2:] == p[2:] for p in parts))
        for k in lod_keys:
            base = (k[0], 0, k[2], k[3])
            assert instances[k]['matrix_columns'] == instances[base]['matrix_columns'], 'Instance IDs differ between LODs'
        selected.update(lod_keys)
        faces = [f for k in lod_keys if k[1] == 0 for f in groups[k]]
        palms.append({
            'id': f"wascityb/tie/tree-{trunk[2]}/trunk-{trunk[3]}",
            'trunk_source': source_id(trunk), 'trunk_proto': groups[trunk][0]['proto'],
            'trunk_origin_m': instances[trunk]['origin_m'],
            'parts_geom0': [dict(source_id(k), material=groups[k][0]['material'],
                                origin_m=instances[k]['origin_m'], **distances.get(k, {})) for k in parts],
            'all_lod_source_ids': [source_id(k) for k in lod_keys],
            'triangles_all_lods': sum(len(groups[k]) for k in lod_keys),
            'triangles_geom0': len(faces), **geometry(faces),
        })

    selection = {k: v for k, v in document['selection'].items() if k not in ('label', 'bounds_xz_m')}
    selection['label'] = 'Marché WCB : deux palmiers complets et tous les buissons touchant le bloc'
    selection['instances'] = [source_id(k) for k in sorted(selected)]
    write('market-plants-selection.json', selection)
    subprocess.run([sys.executable, str(HERE / 'export_block.py'),
                    '--selection', str(HERE / 'market-plants-selection.json'),
                    '--output', str(HERE / 'market-plants-native.json')], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
    exported = read('market-plants-native.json')
    expected = {face_key(f): f for k in selected for f in groups[k]}
    assert {face_key(f): f for f in exported['faces']} == expected, 'Incomplete plant instance export'
    shrubs = []
    block_counts = Counter(identity(f) for f in block['faces'])
    for k in shrub_seeds:
        faces = groups[k]
        shrubs.append({
            'id': f'wascityb/shrub/tree-{k[2]}/instance-{k[3]}',
            'source': source_id(k), 'proto': faces[0]['proto'],
            'origin_m': instances[k]['origin_m'], 'triangles': len(faces),
            'triangles_in_original_block': block_counts[k], **geometry(faces),
        })
    with (ROOT / 'data/out/jak3/fr3/wascityb.fr3').open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert source_hash == selection['source_fr3']['sha256']
    report = {
        'status': 'Native plants fully selected; no remeshing or deployment',
        'source_sha256': source_hash,
        'association': 'Nearest indexed trunk triangle to each native wind attachment; <=2m, next trunk >0.5m farther',
        'bounds': 'Geometry bounds/radii use only vertices of indexed exported triangles',
        'palms_complete': len(palms), 'crown_wind_instances_geom0': sum(len(p['parts_geom0']) - 1 for p in palms),
        'shrubs_complete': len(shrubs),
        'shrubs_extended_past_block': sum(s['triangles'] > s['triangles_in_original_block'] for s in shrubs),
        'faces_all_lods': len(exported['faces']),
        'palms': palms, 'shrubs': shrubs,
        'checks': {'all_selected_instance_faces_preserved': True, 'all_palms_have_trunk_three_crown_parts_four_beard_parts': True,
                   'all_lod_matrices_consistent': True, 'source_unchanged': True},
        'limitation': 'tie_wind needs a dedicated native import path; static patcher cannot replace crowns',
    }
    write('market-plants-map.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('palms', 'shrubs')}, indent=2))
    for palm in palms:
        print(palm['id'], 'parts', [p['instance'] for p in palm['parts_geom0']],
              'center', palm['indexed_center_m'], 'radius XZ', palm['indexed_radius_xz_m'])


if __name__ == '__main__':
    main()
