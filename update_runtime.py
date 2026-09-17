"""Installe le moteur fraichement compile dans le lanceur du prototype.

Copie engine-build/bin/Release/gk.exe vers runtime/liquids-v3/gk.exe et met a jour
l'empreinte dans liquids-v3/runtime-manifest.json (verifiee par launch.py). Les routes
et les fichiers de variante ne sont pas touches : utiliser ce script apres une
modification du moteur seul (C++), sans repasser par liquids-v3/package.py.

Usage : python update_runtime.py
"""
from pathlib import Path
import hashlib, json, shutil, sys

ROOT = Path(__file__).resolve().parent
BUILT = ROOT / 'engine-build/bin/Release/gk.exe'
MANIFEST = ROOT / 'liquids-v3/runtime-manifest.json'


def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    if not BUILT.is_file(): sys.exit(f'Moteur compile introuvable : {BUILT}')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    runtime = ROOT / manifest['runtime']
    before = sha(runtime) if runtime.is_file() else None
    after = sha(BUILT)
    if before == after:
        print('Le moteur du lanceur est deja a jour :', after[:12]); return
    runtime.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BUILT, runtime)
    assert sha(runtime) == after
    manifest['sha256'] = after
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Moteur du lanceur mis a jour : {before[:12] if before else "aucun"} -> {after[:12]}')


if __name__ == '__main__': main()
