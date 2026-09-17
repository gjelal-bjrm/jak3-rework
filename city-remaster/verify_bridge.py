"""Check the built export selector against native faces and pre-change palace exports."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = HERE / 'bridge-validation'
BRIDGE = ROOT / 'engine-build/bin/Release/palace_mesh_bridge.exe'
MANIFEST = json.loads((HERE / 'export-block.json').read_text(encoding='utf-8'))
SOURCE = Path(MANIFEST['source_fr3']['path'])
CHECKS = []


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def check(name, condition):
    assert condition, name
    CHECKS.append(name)


def key(face):
    return tuple(face[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'stream_index'))


def overlaps(face, bounds):
    points = [v['p'] for v in face['vertices']]
    return (max(v[0] for v in points) >= bounds[0] and
            min(v[0] for v in points) <= bounds[1] and
            max(v[2] for v in points) >= bounds[2] and
            min(v[2] for v in points) <= bounds[3])


def export(name, manifest, rejected=False):
    selection, output = WORK / f'{name}-selection.json', WORK / f'{name}.json'
    selection.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    before = output.read_bytes() if output.exists() else None
    result = subprocess.run([str(BRIDGE), '--export-selected', str(SOURCE),
                             str(selection), str(output)], cwd=ROOT,
                            capture_output=True, text=True)
    check(name + ' exit code', result.returncode == (2 if rejected else 0))
    if rejected:
        check(name + ' no output modification',
              (output.read_bytes() if output.exists() else None) == before)
        return None
    return json.loads(output.read_text(encoding='utf-8'))


def main():
    WORK.mkdir(exist_ok=True)
    # These baseline files were produced by the old executable before recompilation.
    palace = ROOT / 'models-v1/waspala-before-models.fr3'
    for name, flags in [('brazier', ['--export-brazier']), ('rocks', []),
                        ('objects', ['--export-objects'])]:
        output = WORK / f'new-{name}.json'
        subprocess.run([str(BRIDGE), *flags, str(palace), str(output)],
                       cwd=ROOT, check=True, capture_output=True)
        check(name + ' legacy output byte-identical', sha(output) == sha(WORK / f'legacy-{name}.json'))

    block = export('block', MANIFEST)
    faces = {key(f): f for f in block['faces']}
    check('source hash matches hashlib', block['source_fr3']['sha256'] == sha(SOURCE))
    check('native keys unique', len(faces) == len(block['faces']))
    check('all static tree types exported', {f['tree_type'] for f in faces.values()} == {'tie', 'tfrag', 'shrub'})
    check('material filter', all(f['material'] in MANIFEST['materials'] for f in faces.values()))
    check('world XZ bounds', all(overlaps(f, MANIFEST['bounds_xz_m']) for f in faces.values()))
    check('draw inventory selected totals', sum(d['selected_triangles'] for d in block['draw_inventory']) == len(faces))

    old_city = json.loads((HERE / 'wascityb-native.json').read_text())
    old_overlap = [f for f in old_city['faces'] if f['material'] in MANIFEST['materials']
                   and overlaps(f, MANIFEST['bounds_xz_m'])]
    check('legacy city reference is nonempty', bool(old_overlap))
    check('native face keys and attributes unchanged', all(faces.get(key(f)) == f for f in old_overlap))

    for tree_type in ('tfrag', 'tie', 'shrub'):
        exemplar = next(f for f in faces.values() if f['tree_type'] == tree_type)
        selection = deepcopy(MANIFEST)
        selection['tree_types'] = [tree_type]
        selection['geoms'] = [exemplar['geom']]
        selection['trees'] = [{'tree_type': tree_type, 'geom': exemplar['geom'], 'tree': exemplar['tree']}]
        selected = export(tree_type + '-tree', selection)
        expected = {k: f for k, f in faces.items() if f['tree_type'] == tree_type and
                    f['geom'] == exemplar['geom'] and f['tree'] == exemplar['tree']}
        check(tree_type + ' exact tree/LOD selection', {key(f): f for f in selected['faces']} == expected)

    # A tiny rectangle inside a real triangle keeps its entire native face even
    # though none of its vertices falls inside that rectangle.
    for face in faces.values():
        points = [v['p'] for v in face['vertices']]
        x, z = (sum(p[d] for p in points) / 3 for d in (0, 2))
        bounds = [x - .0001, x + .0001, z - .0001, z + .0001]
        if all(not (bounds[0] <= p[0] <= bounds[1] and bounds[2] <= p[2] <= bounds[3]) for p in points):
            selection = deepcopy(MANIFEST)
            selection['bounds_xz_m'] = bounds
            crossing = export('crossing-triangle', selection)
            check('whole crossing triangle with no interior vertex',
                  {key(f): f for f in crossing['faces']}.get(key(face)) == face)
            break
    else:
        raise AssertionError('No native crossing triangle found for validation')

    bad_cases = {
        'bad-hash': ('source_fr3', {**MANIFEST['source_fr3'], 'sha256': '0' * 64}),
        'bad-size': ('source_fr3', {**MANIFEST['source_fr3'], 'bytes': 1}),
        'bad-level': ('level', 'waspala'),
        'bad-bounds': ('bounds_xz_m', [10, -10, 0, 1]),
        'bad-geom': ('geoms', [0.5]),
        'bad-tree-type': ('tree_types', ['merc']),
    }
    for name, (field, value) in bad_cases.items():
        selection = deepcopy(MANIFEST)
        selection[field] = value
        export(name, selection, rejected=True)
    selection = deepcopy(MANIFEST)
    selection['materials'] = []
    check('empty material list selects nothing', not export('empty-materials', selection)['faces'])
    check('source FR3 unchanged', sha(SOURCE) == MANIFEST['source_fr3']['sha256'])
    report = {
        'status': 'PASS', 'checks': CHECKS, 'count': len(CHECKS),
        'block_faces': len(faces), 'legacy_city_faces_compared': len(old_overlap),
        'block_by_tree_type_geom': dict(Counter(f"{f['tree_type']}/{f['geom']}" for f in faces.values())),
        'source_sha256': sha(SOURCE), 'bridge_sha256': sha(BRIDGE),
        'limitations': 'Static export validation only; no model import, collision, performance or visual validation',
    }
    (WORK / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
