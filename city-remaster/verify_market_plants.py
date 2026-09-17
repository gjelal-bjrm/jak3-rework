"""Verify wind world geometry against the original decompiler GLB, not helper vertices."""
from collections import defaultdict
from itertools import permutations, product
from pathlib import Path
import hashlib
import json
import math
import struct

HERE = Path(__file__).resolve().parent
LEAF_MATERIALS = {'wascity-palm-leaf-worn', 'wascity-palm-beard'}
IDENTITY = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def matrix_multiply(a, b):
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]


def main():
    inventory, native = read('inventory.json'), read('all-plants-native.json')
    original = Path(next(m['path'] for m in inventory['levels']['wascityb']['models']
                         if m['path'].endswith('wascityb-background.glb')))
    raw = original.read_bytes()
    json_size = struct.unpack_from('<I', raw, 12)[0]
    glb = json.loads(raw[20:20 + json_size])
    binary_start = 28 + json_size
    cache = {}

    def accessor(index):
        if index not in cache:
            acc = glb['accessors'][index]
            view = glb['bufferViews'][acc['bufferView']]
            width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[acc['type']]
            kind = {5126: 'f', 5125: 'I', 5123: 'H', 5121: 'B'}[acc['componentType']]
            fmt = '<' + kind * width
            start = binary_start + view.get('byteOffset', 0) + acc.get('byteOffset', 0)
            stride = view.get('byteStride', struct.calcsize(fmt))
            cache[index] = [struct.unpack_from(fmt, raw, start + i * stride) for i in range(acc['count'])]
        return cache[index]

    original_triangles = []

    def walk(index, parent):
        node = glb['nodes'][index]
        assert not any(k in node for k in ('translation', 'rotation', 'scale')), 'Unexpected GLB TRS transform'
        world = matrix_multiply(parent, node.get('matrix', IDENTITY))
        if 'mesh' in node:
            for primitive in glb['meshes'][node['mesh']]['primitives']:
                material = glb['materials'][primitive['material']]['name']
                if material not in LEAF_MATERIALS:
                    continue
                assert primitive.get('mode', 4) == 4
                vertices, indices = accessor(primitive['attributes']['POSITION']), accessor(primitive['indices'])
                for offset in range(0, len(indices), 3):
                    ids = [indices[offset + i][0] for i in range(3)]
                    if len(set(ids)) < 3:
                        continue
                    points = [tuple(sum(world[k * 4 + d] * (*vertices[i], 1.)[k] for k in range(4))
                                    for d in range(3)) for i in ids]
                    original_triangles.append((material, points))
        for child in node.get('children', []):
            walk(child, world)

    for root in glb['scenes'][glb.get('scene', 0)]['nodes']:
        walk(root, IDENTITY)

    def cell(points):
        return tuple(math.floor(sum(p[d] for p in points) / .03) for d in range(3))

    buckets = defaultdict(list)
    for material, points in original_triangles:
        buckets[(material, *cell(points))].append(points)
    faces = [f for f in native['faces'] if f['tree_type'] == 'tie_wind' and f['geom'] == 0]
    assert len(faces) == len(original_triangles), (len(faces), len(original_triangles))
    max_error = 0.
    for face in faces:
        points = [v['p'] for v in face['vertices']]
        origin = cell(points)
        found = False
        for shift in product((-1, 0, 1), repeat=3):
            candidates = buckets[(face['material'], *(a + b for a, b in zip(origin, shift)))]
            for i, candidate in enumerate(candidates):
                error = min(max(math.dist(a, b) for a, b in zip(points, order)) for order in permutations(candidate))
                if error < .002:
                    max_error = max(max_error, error)
                    candidates.pop(i)
                    found = True
                    break
            if found:
                break
        assert found, ('Native wind triangle absent from original GLB', face['draw'], face['stream_index'])
    assert not any(buckets.values()), 'Original wind geometry omitted'
    plants, mapping = read('market-plants-native.json'), read('market-plants-map.json')
    assert mapping['palms_complete'] == 2 and mapping['shrubs_complete'] == 69
    assert mapping['shrubs_extended_past_block'] == 12
    full_keys = [tuple(f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'stream_index')) for f in plants['faces']]
    assert len(full_keys) == len(set(full_keys))
    assert {f['material'] for f in plants['faces'] if f['tree_type'] == 'tie_wind'} == LEAF_MATERIALS
    for palm in mapping['palms']:
        parts = {(p['tree_type'], p['geom'], p['tree'], p['instance']) for p in palm['parts_geom0']}
        vertices = [v['p'] for f in plants['faces'] if (f['tree_type'], f['geom'], f['tree'], f['instance']) in parts
                    for v in f['vertices']]
        assert len(vertices) == palm['triangles_geom0'] * 3
        assert [min(v[d] for v in vertices) for d in range(3)] == palm['indexed_aabb_min_m']
        assert [max(v[d] for v in vertices) for d in range(3)] == palm['indexed_aabb_max_m']
    report = {
        'status': 'PASS', 'original_glb': str(original), 'original_glb_sha256': hashlib.sha256(raw).hexdigest(),
        'all_WCB_wind_triangles_compared_to_original_glb': len(faces),
        'max_world_vertex_distance_m': max_error,
        'complete_palms': 2, 'complete_shrubs': 69, 'shrubs_extended': 12,
        'native_face_namespace_unique': True, 'indexed_geometry_bounds_verified': True,
        'export_only': True,
    }
    (HERE / 'market-plants-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
