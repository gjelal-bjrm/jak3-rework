"""Read-only, bounded-memory checks of authored native vegetation patches.

Run with Blender's Python (numpy). No bridge invocation or installation occurs.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, hashlib, json, math, sys
import numpy as np

HERE = Path(__file__).resolve().parent
ALLOWED = {'wascity-shrub-orange-01', 'wascity-cactus-green', 'wascity-cactus-flower'}

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def patch_rows(path):
    """Yield the small metadata header, then each addition without loading GBs."""
    decoder = json.JSONDecoder()
    with Path(path).open('r') as stream:
        buf = ''
        while ',"add":[' not in buf:
            chunk = stream.read(1 << 20)
            if not chunk:
                raise ValueError('Missing additions array')
            buf += chunk
        header, buf = buf.split(',"add":[', 1)
        yield json.loads(header + '}')
        pos = 0
        while True:
            while pos < len(buf) and buf[pos] in ' \r\n\t,':
                pos += 1
            if pos < len(buf) and buf[pos] == ']':
                assert (buf[pos:] + stream.read()).strip() == ']}'
                return
            try:
                obj, end = decoder.raw_decode(buf, pos)
            except json.JSONDecodeError:
                chunk = stream.read(1 << 20)
                if not chunk:
                    raise
                buf = buf[pos:] + chunk
                pos = 0
                continue
            yield obj
            pos = end
            if pos > (1 << 20):
                buf = buf[pos:]
                pos = 0

def identity(face):
    return tuple(face[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index'))

def topology(rows, root):
    points = np.asarray([[v['p'] for v in f['vertices']] for f in rows], dtype=np.float32)
    # Exact float32 coordinates match the native packed-vertex precision.
    unique, inverse = np.unique(points.reshape(-1, 3), axis=0, return_inverse=True)
    tris = inverse.reshape(-1, 3)
    local = unique.astype(np.float64) - np.asarray(root)
    area = np.linalg.norm(np.cross(local[tris[:, 1]] - local[tris[:, 0]],
                                   local[tris[:, 2]] - local[tris[:, 0]]), axis=1)
    directed = np.concatenate((tris[:,[0,1]],tris[:,[1,2]],tris[:,[2,0]]))
    edges, edge_indices, edge_counts = np.unique(np.sort(directed,axis=1),axis=0,return_inverse=True,return_counts=True)
    directions = np.bincount(edge_indices,weights=np.where(directed[:,0]<directed[:,1],1,-1))
    parents = list(range(len(unique)))
    def find(v):
        while parents[v] != v:
            parents[v] = parents[parents[v]]
            v = parents[v]
        return v
    for u,v in edges.tolist():
        parents[find(v)] = find(u)
    tri_components=np.asarray([find(int(a))for a in tris[:,0]])
    volumes=np.bincount(tri_components,weights=np.einsum('ij,ij->i',local[tris[:,0]],np.cross(local[tris[:,1]],local[tris[:,2]]))/6)
    volumes=volumes[np.unique(tri_components)]
    return {'zero_area_triangles': int(np.sum(area < 1e-12)),
            'nonmanifold_edges': int(np.sum(edge_counts!=2)),
            'inconsistent_edges': int(np.sum(directions!=0)),
            'components': len(volumes), 'nonpositive_components': int(np.sum(volumes<=0)),
            'minimum_component_volume_m3': float(np.min(volumes)),
            'min': unique.min(axis=0).tolist(), 'max': unique.max(axis=0).tolist()}

def validate(level, sample=False):
    suffix = '-sample' if sample else ''
    source = json.loads((HERE / (level + '-native.json')).read_text())
    report = json.loads((HERE / (level + suffix + '-report.json')).read_text())
    path = HERE / (level + suffix + '-patch.json')
    stream = patch_rows(path)
    header = next(stream)
    assert header['source_fr3'] == source['source_fr3'] == report['source_fr3']
    assert header['preserve_bvh'] is True
    assert sha(path) == report['patch_sha256']
    expected_instances = {i['instance'] for i in report['instances']}
    source_faces = [f for f in source['faces'] if f['instance'] in expected_instances]
    assert set(f['material'] for f in source_faces) == ALLOWED
    expected = {identity(f): f for f in source_faces}
    assert len(expected) == len(header['remove'])
    assert set(identity(f) for f in header['remove']) == set(expected)
    for f in header['remove']:
        assert f['original_positions'] == [v['p'] for v in expected[identity(f)]['vertices']]
    inventory = {i['instance']: i for i in source['instance_inventory']}
    native = defaultdict(list)
    for f in source_faces:
        native[f['instance']].append(f)
    failures = []
    def check(value, message):
        if not value:
            failures.append(message)
    per_instance = []
    for number, instance in enumerate(report['instances']):
        index = instance['instance']
        assert instance['origin_m'] == inventory[index]['origin_m']
        assert instance['matrix_columns'] == inventory[index]['matrix_columns']
        rows = [next(stream) for _ in range(instance['triangles'])]
        palette = set(v['color'] for f in native[index] for v in f['vertices'])
        source_draws = set((f['tree_type'],f['geom'],f['tree'],f['draw'],f['group']) for f in native[index])
        for f in rows:
            assert (f['tree_type'],f['geom'],f['tree'],f['draw'],f['group']) in source_draws
            assert len(f['vertices']) == 3
            assert f.get('texture') in ({'market-shrub-orange-v1'} if instance['kind']=='grass' else {'city-cactus-green-v2',None})
            for v in f['vertices']:
                assert all(math.isfinite(x) for x in v['p']+v['uv']+v['normal'])
                assert all(-.01 <= x <= 4096.01 for x in v['uv'])
                assert all(c in palette for c in v['color_indices'])
                assert min(v['color_weights']) >= 0 and abs(sum(v['color_weights'])-1) < 1e-6
                assert all(0 <= c <= 255 for c in v['rgba'])
        topo = topology(rows, instance['origin_m'])
        for key in ('zero_area_triangles','nonmanifold_edges','inconsistent_edges','nonpositive_components'):
            check(topo[key] == 0, f'{index}: {key}={topo[key]}')
        check(topo['components'] == instance['closed_components'], f'{index}: component count {topo["components"]}')
        check(instance['radius_ratio'] <= 1.15, f'{index}: footprint ratio {instance["radius_ratio"]}')
        check(abs(instance['base_y_change_m']) <= .15, f'{index}: base shift {instance["base_y_change_m"]}m')
        per_instance.append({'instance':index,'kind':instance['kind'],**topo})
        if number % 100 == 0:
            print(level, number+1, '/',len(report['instances']), 'failures', len(failures), flush=True)
    assert next(stream, None) is None
    for t in header['new_textures']:
        pixels = np.memmap(t['rgba_file'],dtype=np.uint8,mode='r')
        assert len(pixels) == t['width']*t['height']*4
        assert np.all(pixels[3::4] == 128)
        assert sha(t['rgba_file']) == next(x['sha256'] for x in report['textures'] if x['name']==t['name'])
    result = {'level':level,'passed':not failures,'failures':failures,
              'patch_sha256':sha(path),'source_fr3':header['source_fr3'],
              'checked_instances':len(per_instance),'checked_triangles':sum(i['triangles'] for i in report['instances']),
              'removed_triangles':len(header['remove']),'native_visual_validation':False,
              'checks':'Exact removal identities/positions; native palette provenance; unchanged roots/matrices; finite native float32 geometry; closed oriented positive-volume components; bounds; texture bytes/alpha; no runtime mutation.',
              'instances':per_instance}
    (HERE / (level + suffix + '-validation.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('level','passed','checked_instances','checked_triangles','failures')}),flush=True)
    return result['passed']

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');parser.add_argument('--level',choices=['wascitya','wascityb'])
    args=parser.parse_args()
    success=[validate(level,args.sample) for level in ([args.level] if args.level else ['wascitya','wascityb'])]
    sys.exit(0 if all(success) else 1)
