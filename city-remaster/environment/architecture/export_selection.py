"""Read-only FR3 export: complete static TIE instances containing native stucco.

Uses the current ENV-pinned LOD0 surface inventory to select full instances,
all component materials and all native LODs. Never patches/deploys any FR3.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BRIDGE = ROOT / 'engine-build/bin/Release/palace_mesh_bridge.exe'


def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def bounds(faces):
    points = [v['p'] for face in faces for v in face['vertices']]
    return [[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]


def main():
    report = {'status': 'native_selection_only', 'levels': {}, 'scope': 'Complete static TIE instances with stucco, all materials and LODs; no TFRAG'}
    actors = json.loads((ROOT / 'city-remaster/inventory.json').read_text())['levels']
    for level in ('wascitya', 'wascityb'):
        source_export = ROOT / f'city-remaster/sand-steps/{level}-surfaces.json'
        source = json.loads(source_export.read_text())
        pinned = Path(source['selection']['source_fr3']['path'])
        assert sha(pinned) == source['source_fr3']['sha256'] == sha(ROOT / f'data/out/jak3/fr3/{level}.fr3')
        chosen = sorted({(f['tree'], f['instance']) for f in source['faces']
                         if f['tree_type'] == 'tie' and f['geom'] == 0 and f['material'].startswith('wascity-stucco-')})
        assert chosen and all(i >= 0 for _, i in chosen)
        selection = {'level': level, 'source_fr3': {'path': str(pinned), 'bytes': pinned.stat().st_size, 'sha256': sha(pinned)},
                     'tree_types': ['tie'], 'instances': [{'tree_type': 'tie', 'tree': t, 'instance': i} for t, i in chosen],
                     'label': 'Complete native stucco architecture instances, all component materials and all LODs'}
        selection_path = HERE / f'{level}-selection.json'; output = HERE / f'{level}-native.json'
        selection_path.write_text(json.dumps(selection, indent=2) + '\n')
        subprocess.run([str(BRIDGE), '--export-selected', str(pinned), str(selection_path), str(output)], cwd=ROOT, check=True)
        data = json.loads(output.read_text())
        assert data['source_fr3'] == source['source_fr3']
        assert {(f['tree'], f['instance']) for f in data['faces']} <= set(chosen)
        groups = defaultdict(list)
        for face in data['faces']: groups[face['tree'], face['instance'], face['geom']].append(face)
        index = {(r['tree'], r['instance'], r['geom']): r for r in data['instance_inventory'] if r['tree_type'] == 'tie'}
        instances = []
        for tree, instance in chosen:
            rows = []
            for (t, i, geom), faces in sorted(groups.items()):
                if (t, i) != (tree, instance): continue
                row = index[t, i, geom]
                rows.append({'geom': geom, 'triangles': len(faces), 'proto': faces[0]['proto'], 'bounds_m': bounds(faces),
                             'origin_m': row['origin_m'], 'matrix_columns': row['matrix_columns'],
                             'materials': dict(Counter(f['material'] for f in faces)),
                             'draws': sorted({f['draw'] for f in faces})})
            assert rows and rows[0]['geom'] == 0
            # LODs use the same source matrix anchor; no synthesized instance is accepted.
            assert all(row['origin_m'] == rows[0]['origin_m'] and row['matrix_columns'] == rows[0]['matrix_columns'] for row in rows)
            lo, hi = rows[0]['bounds_m']; extent = [hi[i] - lo[i] for i in range(3)]
            instances.append({'tree': tree, 'instance': instance, 'prototype_lod0': rows[0]['proto'],
                              'origin_m': rows[0]['origin_m'], 'bounds_m': rows[0]['bounds_m'], 'extent_m': extent,
                              'major_house_candidate': extent[0] > 7 and extent[1] > 8 and extent[2] > 7,
                              'lods': rows})
        report['levels'][level] = {'source_fr3': selection['source_fr3'], 'source_export': str(source_export),
                                  'source_export_sha256': sha(source_export), 'selection': str(selection_path),
                                  'selection_sha256': sha(selection_path), 'export': str(output), 'export_sha256': sha(output),
                                  'instances': instances, 'instance_count': len(instances),
                                  'triangles_by_lod': dict(Counter(f['geom'] for f in data['faces'])),
                                  'materials_lod0': dict(Counter(f['material'] for f in data['faces'] if f['geom'] == 0)),
                                  'moving_actor_anchors': [a for a in actors[level]['actors'] if any(w in a['etype'] for w in ('door', 'airlock', 'elevator'))]}
        print(level, len(instances), 'whole instances;', report['levels'][level]['triangles_by_lod'], flush=True)
        del source, data
        (HERE / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__': main()
