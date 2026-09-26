"""Construction des niveaux du remaster : geometrie refaite + textures HD, dans TOUS les niveaux concernes.

  python remaster-build/build.py            niveaux dont une entree a change
  python remaster-build/build.py --all      tout reconstruire
  python remaster-build/build.py wascitya   seulement ces niveaux

Pour chaque niveau (fichier .fr3) :
  - base : copie d'avant nos modifications de ce chantier (bases/<niveau>.fr3, prise une seule fois : version
    remaster deja validee si elle existe, sinon le jeu d'origine), ou la base propre au lieu (arene) ;
  - modifications de geometrie du lieu (GEOMETRY), combinees en UNE passe (les indices natifs changent apres
    un patch : ne jamais enchainer) ;
  - toutes les textures HD dont le nom existe dans le niveau (inventaire textures-by-level.json : un meme
    nom peut exister en copie dans plusieurs niveaux, et c'est souvent la copie que le jeu affiche) ;
  - installation dans data/ et la variante remaster (sync_variant), copie d'origine ajoutee aux variantes
    original / remaster-v1 pour que le lanceur puisse toujours comparer.
Controle : le bridge compte les textures remplacees ; le script verifie que ce compte est celui attendu.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ORIGINAL = ROOT.parents[1] / 'active/jak3/data/out/jak3/fr3'
BRIDGE = ROOT / 'engine-build/bin/Release/palace_mesh_bridge.exe'
DATA = ROOT / 'data/out/jak3/fr3'

TEXTURE_SETS = [ROOT / 'arena-remaster/textures/textures-genshin.json',   # arene (76, style Genshin choisi)
                ROOT / 'textures-remaster/textures.json']                   # tout le decor (kit Codex)
AO = ROOT / 'arena-remaster/objects'
GEOMETRY = {
    'wasstada': {'base': AO / 'wasstada-before-objects.fr3',
                 'patches': [AO / 'braziers-patch.json', AO / 'spikes-patch.json',
                             ROOT / 'arena-remaster/rocks/rocks-patch.json', ROOT / 'arena-remaster/uv/uv-patch-wasstada.json']},
    'wasstadb': {'base': AO / 'wasstadb-before-textures.fr3', 'patches': [ROOT / 'arena-remaster/uv/uv-patch-wasstadb.json']},
    'wasstadc': {'base': AO / 'wasstadc-before-textures.fr3', 'patches': []},
}
# patchs de geometrie ajoutes par les chantiers suivants (ville, desert...) : fichier registre
REGISTRY = HERE / 'geometry.json'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 22), b''): h.update(block)
    return h.hexdigest()


def stamp_of(path):
    st = Path(path).stat(); return f'{Path(path).name}:{st.st_size}:{int(st.st_mtime)}'


def geometry():
    g = dict(GEOMETRY)
    if REGISTRY.exists():
        for level, spec in json.loads(REGISTRY.read_text()).items():
            g[level] = {'base': ROOT / spec['base'], 'patches': [ROOT / p for p in spec['patches']]}
    return g


def base_of(level, geo):
    if level in geo: return geo[level]['base']
    base = HERE / 'bases' / f'{level}.fr3'
    if not base.exists():
        base.parent.mkdir(parents=True, exist_ok=True)
        remaster = ROOT / 'variants/remaster/out/jak3/fr3' / f'{level}.fr3'
        shutil.copy2(remaster if remaster.exists() else ORIGINAL / f'{level}.fr3', base)
    return base


def rel_of(level):
    """Chemin du fichier dans les variantes, avec la casse deja enregistree (GAME.fr3 / game.fr3)."""
    files = json.loads((ROOT / 'variant-files.json').read_text(encoding='utf-8'))
    rel = f'out/jak3/fr3/{level}.fr3'
    for f in files:
        if f.lower() == rel.lower(): return f
    return rel


def ensure_variants(level):
    """Le lanceur verifie chaque fichier de variante : la version d'origine doit exister partout."""
    rel = rel_of(level)
    hashes = json.loads((ROOT / 'variant-hashes.json').read_text(encoding='utf-8'))
    changed = False
    for variant in ('original', 'remaster-v1'):
        if rel in hashes.get(variant, {}): continue
        target = ROOT / 'variants' / variant / rel; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ORIGINAL / f'{level}.fr3', target)
        hashes[variant][rel] = sha(target); changed = True
    if changed: (ROOT / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')


def main(args):
    geo = geometry()
    inventory = json.loads((HERE / 'textures-by-level.json').read_text())
    textures = {}
    for path in TEXTURE_SETS:
        if path.exists():
            for t in json.loads(path.read_text())['textures']: textures.setdefault(t['name'], t)
    stamps_path = HERE / 'stamps.json'
    stamps = json.loads(stamps_path.read_text()) if stamps_path.exists() else {}
    force = '--all' in args
    wanted = [a for a in args if not a.startswith('--')]
    levels = sorted(set(inventory) | set(geo))
    report = []
    for level in levels:
        if wanted and level not in wanted: continue
        names = {n for n, w, h in inventory.get(level, [])}
        tex = [textures[n] for n in sorted(names & set(textures))]
        spec = geo.get(level, {'patches': []})
        if not tex and not spec['patches'] and level not in geo: continue
        base = base_of(level, geo)
        stamp = [stamp_of(base)] + [stamp_of(p) for p in spec['patches']] + \
                [f"{t['name']}:{Path(t['rgba_file']).stat().st_mtime:.0f}" for t in tex]
        key = hashlib.sha256('|'.join(stamp).encode()).hexdigest()
        if not force and stamps.get(level) == key and (DATA / f'{level}.fr3').exists():
            continue
        patch = {'description': f'Remaster : {level}', 'remove': [], 'add': [], 'textures': tex, 'textures_optional': True}
        seen = set()
        for p in spec['patches']:
            part = json.loads(Path(p).read_text())
            for face in part['remove']:
                k = tuple(face.get(x) for x in ('tree_type', 'geom', 'tree', 'draw', 'stream_index'))
                assert k not in seen, ('remplacements qui se chevauchent', level, p)
                seen.add(k)
            patch['remove'] += part['remove']; patch['add'] += part['add']
            for t in part.get('new_textures', []):             # textures neuves (ex. folioles des palmiers)
                if all(x['name'] != t['name'] for x in patch.setdefault('new_textures', [])): patch['new_textures'].append(t)
            del part
        (HERE / 'patches').mkdir(exist_ok=True)
        patch_file = HERE / 'patches' / f'{level}.json'
        patch_file.write_text(json.dumps(patch, separators=(',', ':')))
        del patch
        out = HERE / 'out' / f'{level}.fr3'; out.parent.mkdir(exist_ok=True)
        run = subprocess.run([str(BRIDGE), str(base), str(patch_file), str(out)], capture_output=True, text=True, errors='replace')
        replaced = None
        for line in run.stdout.splitlines():
            if line.startswith('Textures replaced in this level:'): replaced = int(line.split(':')[1])
        ok = run.returncode == 0 and (replaced == len(tex) or not tex)
        print(f'{level:12s} textures {replaced}/{len(tex)}  patchs {len(spec["patches"])}  {"OK" if ok else "ECHEC"}', flush=True)
        if not ok:
            print(run.stdout[-1500:], run.stderr[-1500:]); report.append((level, 'echec')); continue
        rel = rel_of(level)
        shutil.copy2(out, ROOT / 'data' / rel)
        subprocess.run([sys.executable, str(ROOT / 'sync_variant.py'), rel], check=True, capture_output=True)
        ensure_variants(level)
        stamps[level] = key
        stamps_path.write_text(json.dumps(stamps, indent=1))
        report.append((level, len(tex)))
    print(f'{len(report)} niveau(x) reconstruit(s)')
    return report


if __name__ == '__main__':
    # une seule construction a la fois (deux constructions simultanees ecrasent les empreintes l'une de l'autre)
    import msvcrt
    lock = (HERE / 'build.lock').open('a+b')
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        sys.exit('Une construction est deja en cours.')
    main(sys.argv[1:])
