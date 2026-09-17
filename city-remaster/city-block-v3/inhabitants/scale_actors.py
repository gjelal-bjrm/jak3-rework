"""Agrandit les habitants des fenetres sans recompiler le moteur.

Le moteur dessine les acteurs a l'echelle 1 : on met donc a l'echelle les
sommets des fichiers .bin installes (positions seulement, toutes les poses),
autour de l'origine qui est au niveau des pieds. L'acteur assis est aussi
abaisse pour rester pose sur le canape.

Usage :
  python scale_actors.py            # applique les facteurs ci-dessous
  python scale_actors.py --restore  # remet les fichiers d'origine (sauvegarde locale)

Les fichiers sont modifies dans variants/remaster (source des lancements) et
dans data (copie active), puis variant-hashes.json est mis a jour.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct

ROOT = Path(__file__).resolve().parents[3]          # prototype spargus-arena-v0.1
REL = Path('custom_assets/jak3/city-interiors')
TARGETS = [ROOT / 'variants/remaster' / REL, ROOT / 'data' / REL]
BACKUP = Path(__file__).resolve().parent / 'scale-backup'
HASHES = ROOT / 'variant-hashes.json'

# facteur d'echelle par acteur, et abaissement (m) pour l'acteur assis
SCALES = {'conversing-male': 1.2, 'conversing-female': 1.2, 'sitting-male': 1.15}
SEAT_HEIGHT = 0.6624                 # hauteur de l'assise dans le modele d'origine (m)
FLOATS_PER_VERTEX = 12               # position3 normale3 uv2 couleur4


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scale_bin(source, destination, factor, vertex_count):
    data = bytearray(source.read_bytes())
    stride = FLOATS_PER_VERTEX * 4
    frames = len(data) // (vertex_count * stride)
    assert frames * vertex_count * stride == len(data), source
    for i in range(frames * vertex_count):
        offset = i * stride
        x, y, z = struct.unpack_from('<3f', data, offset)
        struct.pack_into('<3f', data, offset, x * factor, y * factor, z * factor)
    destination.write_bytes(bytes(data))
    return frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    source_dir = TARGETS[0]
    BACKUP.mkdir(exist_ok=True)

    # Sauvegarde unique des fichiers d'origine (echelle 1).
    for name in list(SCALES) + ['runtime']:
        for ext in ('.bin', '.json'):
            src = source_dir / f'{name}{ext}'
            if src.exists() and not (BACKUP / src.name).exists():
                shutil.copy2(src, BACKUP / src.name)

    hashes = json.loads(HASHES.read_text(encoding='utf-8'))
    changed = []
    for name, factor in SCALES.items():
        meta = json.loads((BACKUP / f'{name}.json').read_text(encoding='utf-8'))
        for target in TARGETS:
            if args.restore:
                shutil.copy2(BACKUP / f'{name}.bin', target / f'{name}.bin')
            else:
                frames = scale_bin(BACKUP / f'{name}.bin', target / f'{name}.bin', factor, meta['vertex_count'])
                print(f'{name:18s} x{factor}  {frames} poses, {meta["vertex_count"]} sommets')
        changed.append(f'{name}.bin')

    runtime = json.loads((BACKUP / 'runtime.json').read_text(encoding='utf-8'))
    if not args.restore:
        for room in runtime['rooms']:
            for actor in room['actors']:
                if actor['mesh'] == 'sitting-male':
                    actor['position'][1] = round(actor['position'][1] - SEAT_HEIGHT * (SCALES['sitting-male'] - 1), 4)
    for target in TARGETS:
        (target / 'runtime.json').write_text(json.dumps(runtime, indent=2) + '\n', encoding='utf-8')
    changed.append('runtime.json')

    for file in changed:
        key = (REL / file).as_posix()
        hashes['remaster'][key] = sha256(source_dir / file)
    HASHES.write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    print('restaure' if args.restore else 'applique', ':', ', '.join(changed), '; empreintes mises a jour')


if __name__ == '__main__':
    main()
