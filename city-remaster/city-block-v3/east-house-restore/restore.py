"""(Derive de pilot-houses-restore/restore.py.) Rend a la maison du quartier est de la ville basse (WCA, TIE arbre 1, instances 1 et 2) leur
geometrie d'origine, et retire leurs cinq fenetres des interieurs.

Motif (retour utilisateur du 17 septembre) : ces fenetres sont collees a un escalier et la piece
ressortait dans le vide de l'escalier. Les quatre fenetres des quartiers est, ouest, bas et nord
(R4) et les trois du marche (R5) restent.

Etapes : patch (retrait de toutes les faces actuelles des groupes de ces deux maisons, ajout des
faces natives de l'export d'avant remodelage), audit de preservation, installation dans data/ et
variants/remaster/, ancres finales (7 fenetres) et runtime.json.

Usage : python restore.py            (tout enchainer)
"""
from pathlib import Path
import json, hashlib, struct, math, subprocess, shutil, sys
H = Path(__file__).resolve().parent; BLOCK = H.parent; R = H.parents[2]; C = R / 'city-remaster'
BRIDGE = R / 'engine-build/bin/Release/palace_mesh_bridge.exe'
sys.path.insert(0, str(C)); sys.path.insert(0, str(BLOCK / 'interiors'))
from audit_native_patch import audit
INSTANCES = (0,); TREE = 1
PILOT_PREFIXES = ('wca-house-east-room',)


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p, j): Path(p).write_text(json.dumps(j, indent=2) + '\n', encoding='utf-8')
def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def f32(v): return struct.unpack('f', struct.pack('f', v))[0]


def build_patch():
    current = read(H / 'native-east-current.json'); original = read(C / 'environment/architecture/wascitya-native.json')
    live = R / 'data/out/jak3/fr3/wascitya.fr3'
    assert current['source_fr3']['sha256'] == sha(live), 'export des maisons pilotes perime'
    gkey = lambda f: (f['tree_type'], f['geom'], f['tree'], f['draw'], f['group'])
    house = [f for f in original['faces'] if f['tree_type'] == 'tie' and f['tree'] == TREE and f['instance'] in INSTANCES]
    groups = {gkey(f) for f in house}
    remove = [{**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group', 'stream_index')}, 'original_positions': [v['p'] for v in f['vertices']]}
              for f in current['faces'] if gkey(f) in groups]
    add = []
    for f in house:
        ps = [[f32(x) for x in v['p']] for v in f['vertices']]
        a, b, c = ps; u = [b[i] - a[i] for i in range(3)]; w = [c[i] - a[i] for i in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]; L = math.sqrt(sum(x * x for x in n))
        if L < 1e-9: continue
        n = [x / L for x in n]
        add.append({**{k: f[k] for k in ('tree_type', 'geom', 'tree', 'draw', 'group')},
                    'vertices': [{'p': v['p'], 'uv': v['uv'], 'normal': n, 'color_indices': [v['color']] * 3, 'color_weights': [1, 0, 0]} for v in f['vertices']]})
    patch = {'level': 'wascitya', 'source_fr3': current['source_fr3'], 'preserve_bvh': True, 'remove': remove, 'add': add}
    write(H / 'wascitya-patch.json', patch)
    print(f'patch : {len(remove)} faces retirees (maisons remodelees), {len(add)} faces natives restaurees, {len(groups)} groupes')
    return patch


def stage(patch):
    stage = H / 'staging'; stage.mkdir(exist_ok=True)
    r4 = read(BLOCK / 'pilot-houses-restore/installed.json')
    before = R / 'data/out/jak3/fr3/wascitya.fr3'; after = stage / 'wascitya.fr3'; patch_path = H / 'wascitya-patch.json'
    assert sha(before) == r4['output_sha256'] == patch['source_fr3']['sha256'], 'le WCA actif n est pas la sortie R4'
    with (stage / 'coverage.log').open('w') as f:
        subprocess.run([str(BRIDGE), '--audit-bvh-coverage', str(before), str(patch_path), str(H / 'bvh-coverage.json')], stdout=f, stderr=subprocess.STDOUT, check=True)
    with (stage / 'bridge.log').open('w') as f:
        subprocess.run([str(BRIDGE), str(before), str(patch_path), str(after)], stdout=f, stderr=subprocess.STDOUT, check=True)
    proof = stage / 'preservation.json'; result = audit(before, after, patch_path, proof)
    assert result['status'] == 'passed', result
    candidate = {'status': 'staged', 'path': 'out/jak3/fr3/wascitya.fr3', 'base_path': str(before), 'base_sha256': sha(before),
                 'output_path': str(after), 'output_sha256': sha(after), 'patch': str(patch_path), 'patch_sha256': sha(patch_path),
                 'preservation_report': str(proof), 'preservation_report_sha256': sha(proof),
                 'parent_record': str(BLOCK / 'pilot-houses-restore/installed.json'), 'parent_record_sha256': sha(BLOCK / 'pilot-houses-restore/installed.json'),
                 'bvh_coverage': str(H / 'bvh-coverage.json'), 'bvh_coverage_sha256': sha(H / 'bvh-coverage.json'),
                 'scope': 'Maison du quartier est (WCA, TIE arbre 1, instance 0) rendue a sa geometrie native : sa fenetre etait a 47 cm d un angle, aucune piece n y tient.'}
    write(H / 'candidate.json', candidate); print('staging : audit de preservation reussi,', candidate['output_sha256'][:12])
    return candidate


def install(candidate):
    hashes = read(R / 'variant-hashes.json')
    live = R / 'data' / candidate['path']; variant = R / 'variants/remaster' / candidate['path']
    assert sha(live) == sha(variant) == candidate['base_sha256']
    shutil.copy2(candidate['output_path'], live); shutil.copy2(candidate['output_path'], variant)
    assert sha(live) == sha(variant) == candidate['output_sha256']
    hashes['remaster'][candidate['path']] = candidate['output_sha256']
    write(R / 'variant-hashes.json', hashes)
    # ancres finales : R4 sans les maisons pilotes + marche
    final = BLOCK / 'interiors/window-anchors-final.json'
    kept = [w for w in read(final) if not w['id'].startswith(PILOT_PREFIXES)]; write(final, kept)
    subprocess.run([sys.executable, str(BLOCK / 'interiors/install_rooms.py'), '--anchors', str(final)], check=True)
    candidate.update(status='installed', window_anchors_final=str(final), window_anchors_final_sha256=sha(final), windows_total=len(kept))
    write(H / 'installed.json', candidate)
    print(f'installe : WCA {candidate["output_sha256"][:12]} ; {len(kept)} fenetres conservees :', [w['id'] for w in kept])


if __name__ == '__main__':
    install(stage(build_patch()))
