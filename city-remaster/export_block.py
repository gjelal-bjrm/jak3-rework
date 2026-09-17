"""Export a selected native block; never install or patch game data."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BRIDGE = ROOT / 'engine-build/bin/Release/palace_mesh_bridge.exe'


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, default=HERE / 'export-block.json')
    parser.add_argument('--output', type=Path, default=HERE / 'market-block-native.json')
    args = parser.parse_args()
    selection_path = args.selection.resolve()
    manifest = json.loads(selection_path.read_text(encoding='utf-8'))
    source = Path(manifest['source_fr3']['path'])
    if not source.is_absolute():
        source = selection_path.parent / source
    source = source.resolve()
    output = args.output.resolve()
    if output in (source, selection_path, BRIDGE.resolve()):
        parser.error('Output must not overwrite the source, selection or bridge')
    source_hash = sha(source)
    expected = manifest['source_fr3'].get('sha256')
    if expected and source_hash != expected.lower():
        parser.error(f'Source FR3 changed: {source_hash}')
    if not BRIDGE.is_file():
        parser.error('Build the palace_mesh_bridge target before exporting')
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(BRIDGE), '--export-selected', str(source),
                    str(selection_path), str(output)], check=True, cwd=ROOT)
    document = json.loads(output.read_text(encoding='utf-8'))
    assert document['source_fr3']['sha256'] == source_hash
    assert document['selection'] == manifest
    fields = ('tree_type', 'geom', 'tree', 'draw', 'stream_index')
    keys = [tuple(face[key] for key in fields) for face in document['faces']]
    assert len(keys) == len(set(keys)), 'Duplicate native face identifiers'
    report = {
        'status': 'Native export only; no models generated or installed',
        'level': document['level'], 'source_sha256': source_hash,
        'selection_sha256': sha(selection_path), 'export_sha256': sha(output),
        'faces': len(keys),
        'by_tree_type_and_geom': dict(Counter(
            f"{face['tree_type']}/{face['geom']}" for face in document['faces'])),
        'by_material': dict(Counter(face['material'] for face in document['faces'])),
        'unique_native_keys': True,
    }
    report_path = output.with_name(output.stem + '-summary.json')
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
