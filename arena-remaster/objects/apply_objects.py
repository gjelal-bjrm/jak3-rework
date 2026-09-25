"""Combine les modifications d'objets de l'arene (braseros, lames, falaises...) et les applique en UNE passe du bridge sur
la copie d'origine wasstada-before-objects.fr3 (les indices natifs changent apres un patch : ne jamais enchainer),
puis installe le resultat dans data/ et la variante remaster.
Usage : python arena-remaster/objects/apply_objects.py [patchs relatifs a ce dossier ; par defaut : tous]
"""
from pathlib import Path
import json, shutil, subprocess, sys
H = Path(__file__).resolve().parent; R = H.parents[1]
BRIDGE = R / 'engine-build/bin/Release/palace_mesh_bridge.exe'


def main(parts):
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
    (H / 'combined-patch.json').write_text(json.dumps(combined, separators=(',', ':')))
    out = H / 'wasstada-objects.fr3'
    subprocess.run([str(BRIDGE), str(H / 'wasstada-before-objects.fr3'), str(H / 'combined-patch.json'), str(out)], check=True)
    shutil.copy2(out, R / 'data/out/jak3/fr3/wasstada.fr3')
    subprocess.run([sys.executable, str(R / 'sync_variant.py'), 'out/jak3/fr3/wasstada.fr3'], check=True)


if __name__ == '__main__':
    main(sys.argv[1:] or ['braziers-patch.json', 'spikes-patch.json', '../rocks/rocks-patch.json'])
