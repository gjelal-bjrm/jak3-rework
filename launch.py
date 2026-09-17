"""Launch the isolated playable A/B prototype using the installed OpenGOAL runtime."""
from pathlib import Path
import argparse
import hashlib
import json
import msvcrt
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('variant', choices=('original', 'remaster', 'remaster-v1'))
parser.add_argument('--scene', choices=('arena', 'palace'), default='arena')
parser.add_argument('--prepare-only', action='store_true')
args = parser.parse_args()

lock = (ROOT / 'prototype.lock').open('a+b')
lock.seek(0)
try:
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    sys.exit('Le prototype est deja ouvert. Fermez sa fenetre avant de changer de version.')

files = json.loads((ROOT / 'variant-files.json').read_text(encoding='utf-8'))
expected = json.loads((ROOT / 'variant-hashes.json').read_text(encoding='utf-8'))
runtime = ROOT.parents[1] / 'versions/official/v0.3.6/gk.exe'
if args.variant == 'remaster':
    manifest = json.loads((ROOT / 'liquids-v3/runtime-manifest.json').read_text())
    runtime = ROOT / manifest['runtime']
    if not runtime.is_file() or hashlib.sha256(runtime.read_bytes()).hexdigest() != manifest['sha256']:
        sys.exit('Moteur V3 manquant ou modifie. Relancer le conditionnement du prototype.')
route = ROOT / 'routes' / args.scene / 'GAME.CGO'
if args.variant == 'remaster':
    route = ROOT / 'routes/remaster' / args.scene / 'GAME.CGO'
if not route.is_file():
    sys.exit(f'Point de test manquant : {route}')
if args.variant == 'remaster' and hashlib.sha256(route.read_bytes()).hexdigest() != manifest['routes'][args.scene]:
    sys.exit('Code de demarrage V3 modifie. Relancer le conditionnement du prototype.')
for relative in files:
    source = ROOT / 'variants' / args.variant / relative
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected[args.variant][relative]:
        sys.exit(f'Fichier de variante manquant ou modifie : {source}')
for relative in files:
    shutil.copy2(ROOT / 'variants' / args.variant / relative, ROOT / 'data' / relative)
(ROOT / 'current-variant.txt').write_text(args.variant, encoding='utf-8')
shutil.copy2(route, ROOT / 'data/out/jak3/iso/GAME.CGO')
(ROOT / 'current-scene.txt').write_text(args.scene, encoding='utf-8')
print(f'SPARGUS - {args.variant.upper()} - {args.scene} - eclairage fixe a 09:00', flush=True)
if args.prepare_only:
    sys.exit(0)

profile = ROOT / 'profiles' / (args.variant if args.scene == 'arena' else args.variant + '-palace')
profile.mkdir(parents=True, exist_ok=True)
settings = profile / 'OpenGOAL/jak3/settings'
if not settings.exists():
    shutil.copytree(ROOT / 'profiles/original/OpenGOAL/jak3/settings', settings)
pc_settings = settings / 'pc-settings.gc'
if pc_settings.exists():
    content = pc_settings.read_text(encoding='utf-8')
    muted = re.sub(r'(\(memcard-volume-(?:sfx|music|dialog)\s+)[^)]*', r'\g<1>0.0000', content)
    if muted != content:
        backup = pc_settings.with_name('pc-settings-before-mute.gc')
        if not backup.exists():
            shutil.copy2(pc_settings, backup)
        pc_settings.write_text(muted, encoding='utf-8')
environment = os.environ.copy()
environment['OPENGOAL_TEST_MUTE'] = '1'
with (ROOT / f'{args.variant}-runtime.log').open('w', encoding='utf-8') as log:
    process = subprocess.Popen([str(runtime), '--game', 'jak3', '--proj-path', str(ROOT / 'data'),
                                '--config-path', str(profile), '--disable-ansi', '--',
                                '-fakeiso', '-boot', '-debug', '-nosound'], cwd=ROOT, stdout=log,
                                stderr=subprocess.STDOUT, env=environment,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    (ROOT / f'{args.variant}.pid').write_text(str(process.pid), encoding='utf-8')
    result = process.wait()
if result:
    sys.exit(f'Le jeu a quitte avec le code {result}. Voir {args.variant}-runtime.log.')
