"""Combine les modifications de l'arene (braseros, lames, falaises..., textures HD) et les applique en UNE passe du
bridge sur la copie d'origine wasstada-before-objects.fr3 (les indices natifs changent apres un patch : ne jamais
enchainer), puis installe le resultat dans data/ et la variante remaster.

Usage : python arena-remaster/objects/apply_objects.py [--textures genshin|fidele|sans] [--autres-parties] [patchs]
  --autres-parties : ne refait que wasstadb et wasstadc (textures), wasstada etant deja a jour.
  sans patch : tous (braseros, lames, falaises) ; --textures : textures HD preparees par
  arena-remaster/textures/prepare_textures.py (le resultat est aussi garde dans wasstada-<version>.fr3).
"""
from pathlib import Path
import json, shutil, subprocess, sys
H = Path(__file__).resolve().parent; R = H.parents[1]
BRIDGE = R / 'engine-build/bin/Release/palace_mesh_bridge.exe'
DEFAULT = ['braziers-patch.json', 'spikes-patch.json', '../rocks/rocks-patch.json', '../uv/uv-patch-wasstada.json']


def main(parts, textures=None, others_only=False):
    combined = {'description': 'Arene : objets remodeles (' + ', '.join(Path(n).stem for n in parts) + ')', 'remove': [], 'add': []}
    seen = set()
    for name in parts:
        part = json.loads((H / name).read_text())
        for face in part['remove']:
            key = tuple(face.get(k) for k in ('tree_type', 'geom', 'tree', 'draw', 'stream_index'))
            assert key not in seen, ('remplacements qui se chevauchent', name, key)
            seen.add(key)
        combined['remove'] += part['remove']; combined['add'] += part['add']
        print(name, len(part['remove']), '->', len(part['add']), flush=True)
        del part
    hd = json.loads((R / f'arena-remaster/textures/textures-{textures}.json').read_text())['textures']         if textures and textures != 'sans' else []
    level_of = lambda t: t['page'].split('-')[0]
    if hd:
        combined['textures'] = [t for t in hd if level_of(t) == 'wasstada']
        combined['description'] += f' + textures HD ({textures})'
        print('textures', textures, len(combined['textures']), flush=True)
    if not others_only:
        (H / 'combined-patch.json').write_text(json.dumps(combined, separators=(',', ':')))
        out = H / 'wasstada-objects.fr3'
        subprocess.run([str(BRIDGE), str(H / 'wasstada-before-objects.fr3'), str(H / 'combined-patch.json'), str(out)], check=True)
        if textures: shutil.copy2(out, H / f'wasstada-{textures}.fr3')
        if textures == 'sans':                  # version de comparaison : textures d'origine partout
            for level in ('wasstadb', 'wasstadc'):
                base = H / f'{level}-before-textures.fr3'
                if base.exists(): shutil.copy2(base, H / f'{level}-sans.fr3')
        shutil.copy2(out, R / 'data/out/jak3/fr3/wasstada.fr3')
        subprocess.run([sys.executable, str(R / 'sync_variant.py'), 'out/jak3/fr3/wasstada.fr3'], check=True)
    # autres parties de l'arene (wasstadb, wasstadc) : textures seulement, depuis leur copie d'avant textures.
    # Elles contiennent aussi des COPIES des textures de wasstada (poutres, barres, murs d'echafaudage...) que
    # le jeu affiche a la place : on leur envoie donc toute la liste (textures absentes ignorees).
    for level in ('wasstadb', 'wasstadc') if hd else ():
        base = H / f'{level}-before-textures.fr3'
        if not base.exists(): shutil.copy2(R / f'data/out/jak3/fr3/{level}.fr3', base)
        other = {'description': f'Arene : textures HD ({textures})', 'remove': [], 'add': [], 'textures': hd,
                 'textures_optional': True}
        uv = R / f'arena-remaster/uv/uv-patch-{level}.json'           # plaquage sans etirement de cette partie
        if uv.exists():
            part = json.loads(uv.read_text()); other['remove'] = part['remove']; other['add'] = part['add']
            other['description'] += ' + plaquage sans etirement'
        (H / f'{level}-patch.json').write_text(json.dumps(other, separators=(',', ':')))
        target = H / f'{level}-{textures}.fr3'
        subprocess.run([str(BRIDGE), str(base), str(H / f'{level}-patch.json'), str(target)], check=True)
        shutil.copy2(target, R / f'data/out/jak3/fr3/{level}.fr3')
        subprocess.run([sys.executable, str(R / 'sync_variant.py'), f'out/jak3/fr3/{level}.fr3'], check=True)


if __name__ == '__main__':
    args = sys.argv[1:]; textures = None
    others_only = '--autres-parties' in args
    if others_only: args.remove('--autres-parties')
    if '--textures' in args:
        i = args.index('--textures'); textures = args[i + 1]; del args[i:i + 2]
    main(args or DEFAULT, textures, others_only)
