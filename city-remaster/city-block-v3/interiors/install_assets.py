"""Installe des meshes de pieces et d'habitants dans les interieurs de ville.

Pour chaque nom donne : copie <nom>.json et <nom>.bin dans data/custom_assets/jak3/city-interiors/
et dans variants/remaster/..., convertit les textures PNG des acteurs en .rgba (u32 largeur,
u32 hauteur, RGBA8) comme interiors/prepare.py, ajoute les chemins a variant-files.json et met a
jour les empreintes de la variante remaster. Idempotent.

Usage : python install_assets.py --rooms homes/home-lounge homes/home-bedroom ... --actors ../inhabitants/sitting-female ...
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct
from PIL import Image
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
ASSETS = 'custom_assets/jak3/city-interiors'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def install(source, dest):
    """Copie un mesh (json + bin) vers dest ; renvoie les chemins relatifs ecrits."""
    meta = json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
    written = []
    binary = source.parent / meta['binary']
    shutil.copy2(binary, dest / meta['binary']); written.append(meta['binary'])
    for draw in meta['draws']:
        if 'texture' in draw and draw['texture'].endswith('.png'):
            png = source.parent / draw['texture']; out = dest / Path(draw['texture']).with_suffix('.rgba')
            out.parent.mkdir(parents=True, exist_ok=True)
            image = Image.open(png).convert('RGBA'); out.write_bytes(struct.pack('<II', *image.size) + image.tobytes())
            draw['texture'] = out.relative_to(dest).as_posix(); written.append(draw['texture'])
    (dest / (source.name + '.json')).write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8'); written.append(source.name + '.json')
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rooms', nargs='*', default=[]); parser.add_argument('--actors', nargs='*', default=[])
    args = parser.parse_args()
    files = json.loads((ROOT / 'variant-files.json').read_text(encoding='utf-8'))
    hashes = json.loads((ROOT / 'variant-hashes.json').read_text(encoding='utf-8'))
    relatives = []
    for base in (ROOT / 'data' / ASSETS, ROOT / 'variants/remaster' / ASSETS):
        base.mkdir(parents=True, exist_ok=True)
        for item in args.rooms + args.actors:
            relatives = install((HERE / item).resolve(), base)
            for rel in relatives:
                key = f'{ASSETS}/{rel}'
                if key not in files: files.append(key)
    for item in args.rooms + args.actors:
        source = (HERE / item).resolve(); meta = json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
        keys = [f'{ASSETS}/{meta["binary"]}', f'{ASSETS}/{source.name}.json'] + [f'{ASSETS}/{Path(d["texture"]).with_suffix(".rgba").as_posix()}' for d in meta['draws'] if 'texture' in d]
        for key in keys:
            variant = ROOT / 'variants/remaster' / key; live = ROOT / 'data' / key
            assert variant.is_file() and live.is_file(), key
            hashes['remaster'][key] = sha(variant); assert sha(live) == hashes['remaster'][key]
            for other in ('original', 'remaster-v1'):     # variantes de comparaison : meme fichier, jamais rendu par leur moteur
                target = ROOT / 'variants' / other / key
                if not target.exists(): target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(variant, target)
                hashes[other][key] = sha(target)
        print('installe :', source.name, '->', len(keys), 'fichiers')
    (ROOT / 'variant-files.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    print('variant-files :', len(files), 'entrees')


if __name__ == '__main__': main()
