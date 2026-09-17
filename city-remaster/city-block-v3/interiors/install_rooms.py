"""Regenere runtime.json des interieurs de ville et l'installe (data + variants/remaster + empreintes).

Les fenetres viennent des ancres installees (par defaut : market-windows-r5/window-anchors-all.json,
soit WCA R4 + marche R5). Les pieces, personnages et leur variete viennent de room_config.rooms_for.
L'acteur assis recoit l'abaissement defini par inhabitants/scale_actors.py.

Usage : python install_rooms.py [--anchors chemin.json] [--dry-run]
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, sys
HERE = Path(__file__).resolve().parent; BLOCK = HERE.parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from room_config import rooms_for, NEIGHBOUR_RADIUS
spec = importlib.util.spec_from_file_location('scale_actors', BLOCK / 'inhabitants/scale_actors.py')
scale_actors = importlib.util.module_from_spec(spec); spec.loader.exec_module(scale_actors)
INTERIORS = 'custom_assets/jak3/city-interiors/runtime.json'
DEFAULT_ANCHORS = BLOCK / 'market-windows-r5/window-anchors-all.json'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(windows):
    rooms = rooms_for(windows)
    seat_shift = scale_actors.SEAT_HEIGHT * (scale_actors.SCALES['sitting-male'] - 1)
    for room in rooms:
        for actor in room['actors']:
            if actor['mesh'] == 'sitting-male':
                actor['position'][1] = round(actor['position'][1] - seat_shift, 4)
    return {'schema': 'city-physical-rooms-v2', 'windows': windows, 'rooms': rooms,
            'scope': 'Spargus authored apertures; shared physical rooms; visual interiors only; stable variety'}


def report(windows, rooms):
    centre = {w['id']: w['center'] for w in windows}
    print(f"{len(windows)} fenetres, {len(rooms)} pieces dont {sum(1 for r in rooms if r['actors'])} habitees")
    for r in rooms:
        print(f"  {r['anchor']:28s} {r.get('variant', r['mesh']):36s} scale x {r['scale'][0]:+.2f}  phase {r['actors'][0]['phase'] if r['actors'] else '-'}")
    identical = 0
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            d = math.dist(centre[rooms[i]['anchor']], centre[rooms[j]['anchor']])
            if d < NEIGHBOUR_RADIUS and rooms[i].get('variant') == rooms[j].get('variant'):
                identical += 1; print(f"  ATTENTION voisines identiques : {rooms[i]['anchor']} / {rooms[j]['anchor']} ({d:.0f} m)")
    print("voisines identiques :", identical)
    return identical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--anchors', default=str(DEFAULT_ANCHORS))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    windows = json.loads(Path(args.anchors).read_text(encoding='utf-8'))
    runtime = build(windows)
    report(windows, runtime['rooms'])
    if args.dry_run: return
    text = json.dumps(runtime, indent=2) + '\n'
    for base in (ROOT / 'data', ROOT / 'variants/remaster'):
        (base / INTERIORS).write_text(text, encoding='utf-8')
    hashes = json.loads((ROOT / 'variant-hashes.json').read_text(encoding='utf-8'))
    hashes['remaster'][INTERIORS] = sha(ROOT / 'variants/remaster' / INTERIORS)
    (ROOT / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    print('runtime.json installe (data + variante remaster), empreinte', hashes['remaster'][INTERIORS][:12])


if __name__ == '__main__': main()
