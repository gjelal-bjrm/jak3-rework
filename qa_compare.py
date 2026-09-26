"""Comparaison complete d'un lieu : jeu d'origine / remaster aux memes cadrages + controle des textures affichees.

  python qa_compare.py <scene> <prefixe> "EX,EY,EZ/TX,TY,TZ" ["..."] [--hour H] [--only remaster|original]

1. lance le remaster (controle d'affichage des textures actif), capture chaque vue avec la camera libre ;
2. resume du controle des textures (qa_textures.py) ;
3. lance le jeu d'origine, memes vues ;
4. planche qa/<prefixe>-compare.png : une ligne par vue, jeu d'origine a gauche, remaster a droite.
"""
from pathlib import Path
import os, subprocess, sys, time
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
W, H = 960, 540
SETTLE = 30


def launch(variant, scene, hour):
    log = ROOT / 'qa' / f'launch-{scene}-{variant}.log'
    env = dict(os.environ, REMASTER_TEXTURE_AUDIT='1', REMASTER_PERF='1')
    cmd = [sys.executable, '-u', str(ROOT / 'launch.py'), variant, '--replace', '--scene', scene,
           '--hour', str(hour), '--time-ratio', '0']
    if variant == 'remaster': cmd += ['--weather', 'beau-temps']   # le jeu d'origine plante si on force la meteo
    with open(log, 'w', encoding='utf-8') as f:
        subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
    for _ in range(600):
        time.sleep(2)
        text = log.read_text(encoding='utf-8', errors='replace')
        if any(k in text for k in ('vitesse', 'Traceback', 'quitte', 'Erreur')): break
    time.sleep(SETTLE)   # chargement complet du lieu (le volcan met plus longtemps que la ville)
    return log.read_text(encoding='utf-8', errors='replace')


def views(variant, scene, prefix, points):
    subprocess.run([sys.executable, str(ROOT / 'qa_views.py'), '--variant', variant, scene, f'{prefix}-{variant}'] + points,
                   cwd=ROOT, check=True)


def main(args):
    hour, only = 13.0, None
    if '--hour' in args: i = args.index('--hour'); hour = float(args[i + 1]); del args[i:i + 2]
    if '--only' in args: i = args.index('--only'); only = args[i + 1]; del args[i:i + 2]
    scene, prefix, points = args[0], args[1], args[2:]
    variants = [v for v in ('remaster', 'original') if only in (None, v)]
    for variant in variants:
        out = launch(variant, scene, hour)
        if 'Traceback' in out or 'Erreur' in out: print(out[-2000:]); sys.exit(f'lancement {variant} en echec')
        views(variant, scene, prefix, points)
        if variant == 'remaster':
            subprocess.run([sys.executable, str(ROOT / 'qa_textures.py')], cwd=ROOT)
            perf = [l for l in (ROOT / 'remaster-runtime.log').read_text(encoding='utf-8', errors='replace').splitlines() if 'Perf:' in l]
            print('fluidite :'); [print('  ', l) for l in perf[-4:]]
    sheet = Image.new('RGB', (2 * W, len(points) * H), (0, 0, 0)); d = ImageDraw.Draw(sheet)
    for i in range(len(points)):
        for c, variant in enumerate(('original', 'remaster')):
            p = ROOT / 'qa' / f'live-{prefix}-{variant}-{i}-00.png'
            if p.exists(): sheet.paste(Image.open(p).convert('RGB').resize((W, H)), (c * W, i * H))
            d.text((c * W + 8, i * H + 8), f'{variant} {i}', fill=(255, 255, 0))
    sheet.save(ROOT / 'qa' / f'{prefix}-compare.png')
    print('planche :', ROOT / 'qa' / f'{prefix}-compare.png')


if __name__ == '__main__':
    main(sys.argv[1:])
