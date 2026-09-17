"""Installe les fenetres du marche dans le jeu : FR3 WCB + pieces habitees + empreintes.

1. Verifie candidate.json (empreintes de tous les fichiers de preuve).
2. Copie le FR3 audite dans data/ et dans variants/remaster/, met a jour variant-hashes.json.
3. Fusionne les ancres de fenetres (WCA R4 + ce lot) et regenere runtime.json des interieurs
   (pieces, lampes, habitants) dans data/ et variants/remaster/, avec l'abaissement de l'acteur
   assis defini par inhabitants/scale_actors.py.
4. Ecrit installed.json.
"""
from pathlib import Path
import importlib.util, json, hashlib, shutil, sys
H = Path(__file__).resolve().parent; R = H.parents[2]; BLOCK = H.parent
sys.path.insert(0, str(BLOCK / 'interiors'))
from room_config import rooms_for
spec = importlib.util.spec_from_file_location('scale_actors', BLOCK / 'inhabitants/scale_actors.py')
scale_actors = importlib.util.module_from_spec(spec); spec.loader.exec_module(scale_actors)
INTERIORS = 'custom_assets/jak3/city-interiors/runtime.json'


def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p, j): Path(p).write_text(json.dumps(j, indent=2) + '\n', encoding='utf-8')


def main():
    c = read(H / 'candidate.json')
    for field in ('base_path', 'output_path', 'patch', 'preservation_report', 'parent_record', 'author_report',
                  'bvh_coverage', 'opening_validation', 'geometry_validation', 'window_anchors'):
        key = {'base_path': 'base_sha256', 'output_path': 'output_sha256'}.get(field, field + '_sha256')
        assert sha(c[field]) == c[key], field
    proof = read(c['preservation_report'])
    assert proof['status'] == 'passed' and all(proof['checks'].values())
    assert proof['before_sha256'] == c['base_sha256'] and proof['after_sha256'] == c['output_sha256']
    record = H / 'installed.json'
    previous = read(record)['output_sha256'] if record.exists() else None      # reinstallation : on remplace l'ancienne sortie du lot

    hashes = read(R / 'variant-hashes.json'); files = read(R / 'variant-files.json')
    assert c['path'] in files and INTERIORS in files

    # 2. FR3 : data + variante remaster (les variantes original / remaster-v1 restent intactes)
    live = R / 'data' / c['path']; variant = R / 'variants/remaster' / c['path']
    assert sha(live) == sha(variant) and sha(live) in (c['base_sha256'], previous), 'WCB actif different de la base du lot et de sa sortie precedente'
    protected = {str(R / 'variants' / v / c['path']): sha(R / 'variants' / v / c['path']) for v in ('original', 'remaster-v1')}
    shutil.copy2(c['output_path'], live); shutil.copy2(c['output_path'], variant)
    assert sha(live) == sha(variant) == c['output_sha256']
    hashes['remaster'][c['path']] = c['output_sha256']

    # 3. Ancres fusionnees et pieces
    r4 = read(BLOCK / 'architecture/revision-004/installed.json')
    previous = read(r4['window_anchors']); assert sha(r4['window_anchors']) == r4['window_anchors_sha256']
    new = read(H / 'window-anchors.json')
    merged = previous + new
    assert len({w['id'] for w in merged}) == len(merged), 'identifiants de fenetres en double'
    write(H / 'window-anchors-all.json', merged)
    rooms = rooms_for(merged)
    seat_shift = scale_actors.SEAT_HEIGHT * (scale_actors.SCALES['sitting-male'] - 1)
    for room in rooms:
        for actor in room['actors']:
            if actor['mesh'] == 'sitting-male':
                actor['position'][1] = round(actor['position'][1] - seat_shift, 4)
    runtime = {'schema': 'city-physical-rooms-v2', 'windows': merged, 'rooms': rooms,
               'scope': 'Spargus authored apertures (WCA R4 + WCB market); shared physical rooms; visual interiors only'}
    for base in (R / 'data', R / 'variants/remaster'):
        write(base / INTERIORS, runtime)
    hashes['remaster'][INTERIORS] = sha(R / 'variants/remaster' / INTERIORS)
    assert sha(R / 'data' / INTERIORS) == hashes['remaster'][INTERIORS]
    write(R / 'variant-hashes.json', hashes)

    c.update(status='installed', protected_variant_hashes=protected, window_anchors_all=str(H / 'window-anchors-all.json'),
             window_anchors_all_sha256=sha(H / 'window-anchors-all.json'), runtime_sha256=hashes['remaster'][INTERIORS],
             windows_total=len(merged), rooms_total=len(rooms))
    write(record, c)
    inhabited = sum(1 for r in rooms if r['actors'])
    print(f"Installe : WCB {c['output_sha256'][:12]} ; {len(merged)} fenetres, {len(rooms)} pieces dont {inhabited} habitees")


if __name__ == '__main__': main()
