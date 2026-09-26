"""Copie des fichiers de data/ vers variants/remaster/ et met a jour leurs empreintes.

A utiliser apres un script qui n'ecrit que dans data/ (ex. models-v2/apply_ocean.py), pour que
le lanceur, qui recopie la variante remaster dans data/ a chaque demarrage et verifie ses
empreintes, prenne bien la nouvelle version.

Usage : python sync_variant.py game/graphics/opengl_renderer/shaders/modern_ocean_surface.frag ...
"""
from pathlib import Path
import hashlib, json, shutil, sys

ROOT = Path(__file__).resolve().parent


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(paths):
    files = json.loads((ROOT / 'variant-files.json').read_text(encoding='utf-8'))
    hashes = json.loads((ROOT / 'variant-hashes.json').read_text(encoding='utf-8'))
    for relative in paths:
        relative = relative.replace('\\', '/')
        source = ROOT / 'data' / relative; target = ROOT / 'variants/remaster' / relative
        if not source.is_file(): sys.exit(f'absent de data/ : {relative}')
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        if relative not in files: files.append(relative)
        hashes['remaster'][relative] = sha(target)
        print(f'{relative}  {hashes["remaster"][relative][:12]}')
    complete_other_variants(files, hashes)
    (ROOT / 'variant-files.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')


def complete_other_variants(files, hashes):
    """Le lanceur verifie chaque fichier de la liste pour la variante lancee : les autres variantes (jeu
    d'origine, remaster-v1) doivent donc aussi l'avoir. On y met la version du jeu d'origine si elle existe,
    sinon le nouveau fichier (un shader que le jeu d'origine n'utilise pas : sans effet)."""
    original_data = ROOT.parents[1] / 'active/jak3/data'
    for variant in hashes:
        if variant == 'remaster': continue
        for relative in files:
            target = ROOT / 'variants' / variant / relative
            if relative in hashes[variant] and target.is_file(): continue
            source = original_data / relative
            if not source.is_file(): source = ROOT / 'variants/remaster' / relative
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
            hashes[variant][relative] = sha(target)
            print(f'{variant} : {relative} ajoute')


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1:])
