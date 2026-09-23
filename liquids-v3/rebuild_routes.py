"""Reconstruit les routes de demarrage du prototype (GAME.CGO par scene) apres une modification du code GOAL
commun (ex. water.gc). Pour chaque scene : apply_boot.py --scene X, compilation (mi) via compile_iso.py,
copie de data/out/jak3/iso/GAME.CGO dans routes/remaster/X/GAME.CGO, puis empreintes du manifeste.
Le jeu doit etre ferme. Usage : python liquids-v3/rebuild_routes.py [arena palace]
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]


def main(scenes):
    manifest_path = ROOT / 'liquids-v3/runtime-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for scene in scenes:
        subprocess.run([sys.executable, str(ROOT / 'apply_boot.py'), '--scene', scene], check=True)
        subprocess.run([sys.executable, str(ROOT / 'liquids-v3/compile_iso.py'), 'out/jak3/iso/GAME.CGO'], check=True)
        target = ROOT / 'routes/remaster' / scene / 'GAME.CGO'
        shutil.copy2(ROOT / 'data/out/jak3/iso/GAME.CGO', target)
        manifest['routes'][scene] = hashlib.sha256(target.read_bytes()).hexdigest()
        print(f'route {scene} : {manifest["routes"][scene][:12]}')
    manifest_path.write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:] or ['arena', 'palace'])
