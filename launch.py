"""Launch the isolated playable A/B prototype using the installed OpenGOAL runtime.

Scenes :
  arena   : arene de Spargus (route de demarrage dediee)
  palace  : palais de Spargus (route de demarrage dediee)
  city    : ville de Spargus. Le jeu demarre par la route du palais, puis le
            compilateur goalc (officiel v0.3.6) est connecte au jeu et deplace Jak
            devant les maisons pilotes du lot city-block-v3. Aucune recompilation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import msvcrt
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('variant', choices=('original', 'remaster', 'remaster-v1'))
parser.add_argument('--scene', choices=('arena', 'palace', 'city'), default='arena')
parser.add_argument('--prepare-only', action='store_true')
parser.add_argument('--capture', action='store_true',
                    help="scene city : prendre une capture d'ecran une fois Jak place (test)")
args = parser.parse_args()

# La scene "city" reutilise la route de demarrage du palais ; le deplacement en ville
# se fait ensuite en direct via goalc, sans toucher aux routes verifiees.
route_scene = 'palace' if args.scene == 'city' else args.scene

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
route = ROOT / 'routes' / route_scene / 'GAME.CGO'
if args.variant == 'remaster':
    route = ROOT / 'routes/remaster' / route_scene / 'GAME.CGO'
if not route.is_file():
    sys.exit(f'Point de test manquant : {route}')
if args.variant == 'remaster' and hashlib.sha256(route.read_bytes()).hexdigest() != manifest['routes'][route_scene]:
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

# ---------------------------------------------------------------------------
# Scene "city" : pilotage du jeu par goalc (nREPL, port 8181)
# ---------------------------------------------------------------------------
GOALC = ROOT.parents[1] / 'versions/official/v0.3.6/goalc.exe'
NREPL_PORT = 8189                      # port dedie : evite un goalc oublie sur le 8181 par defaut
CITY_CONTINUE = 'wascitya-seem'        # point de reprise natif de la ville basse
CITY_VIEWPOINT = (2270.0, 20.5, 3.0)   # metres : rue devant la maison pilote 1 (fenetres habitees)
GOALC_LOG = ROOT / 'city-goalc.log'
POS_PATTERN = re.compile(r'VILLE-POS (\d+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)')


def log_text(path):
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def nrepl_send(sock, form):
    data = form.encode('utf-8')
    sock.sendall(struct.pack('<II', len(data), 10) + data)   # 10 = EVAL


def nrepl_connect(goalc, game):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if goalc.poll() is not None:
            sys.exit(f"goalc s'est arrete (code {goalc.returncode}). Voir {GOALC_LOG.name}.")
        if game.poll() is not None:
            sys.exit("Le jeu s'est ferme pendant le demarrage de goalc.")
        try:
            sock = socket.create_connection(('127.0.0.1', NREPL_PORT), timeout=2)
            sock.settimeout(5)
            try:
                sock.recv(1024)          # message d'accueil du nREPL
            except socket.timeout:
                pass
            return sock
        except OSError:
            time.sleep(1)
    sys.exit(f'Impossible de joindre goalc sur le port {NREPL_PORT}. Voir {GOALC_LOG.name}.')


def probe_position(sock, game, game_log, tag, timeout):
    """Demande au jeu d'ecrire la position de Jak dans son journal et la lit."""
    form = ('(when (and *target* (-> *target* control)) '
            f'(format 0 "VILLE-POS {tag} ~f ~f ~f~%" '
            '(/ (-> *target* control trans x) 4096.0) '
            '(/ (-> *target* control trans y) 4096.0) '
            '(/ (-> *target* control trans z) 4096.0)))')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if game.poll() is not None:
            sys.exit("Le jeu s'est ferme avant la fin de la mise en place.")
        nrepl_send(sock, form)
        time.sleep(2)
        for match in POS_PATTERN.finditer(log_text(game_log)):
            if int(match.group(1)) == tag:
                return tuple(float(match.group(i)) for i in (2, 3, 4))
    return None


def place_jak_in_city(game, game_log, capture):
    started = time.monotonic()

    def say(message):
        print(f'VILLE [+{time.monotonic() - started:3.0f}s] : {message}', flush=True)

    goalc_out = GOALC_LOG.open('w', encoding='utf-8')
    goalc = subprocess.Popen([str(GOALC), '--game', 'jak3', '--proj-path', str(ROOT / 'data'),
                              '--port', str(NREPL_PORT)],
                             cwd=ROOT, stdin=subprocess.PIPE, stdout=goalc_out,
                             stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    say('demarrage du compilateur goalc...')
    sock = nrepl_connect(goalc, game)

    # 0. Un goalc neuf ne connait pas les symboles du jeu (*target*, types...). On lui fait
    #    lire le fichier de types complet pendant que le jeu demarre ; aucune ecriture.
    nrepl_send(sock, '(asm-file "decompiler/config/jak3/all-types.gc")')
    say('lecture des types du jeu par goalc (en parallele du demarrage du jeu)...')

    # 1. Attendre que le jeu soit en place au palais.
    deadline = time.monotonic() + 180
    while 'SPARGUS-PROTOTYPE:' not in log_text(game_log):
        if game.poll() is not None or time.monotonic() > deadline:
            say("le jeu n'a pas signale son demarrage. Jak reste au palais.")
            return goalc
        time.sleep(1)
    say('jeu demarre au palais')

    # 2. Connecter goalc au jeu, puis verifier la liaison par une vraie reponse du jeu.
    #    Les messages s'empilent tant que goalc lit encore les types ; c'est attendu.
    tag = 1
    position = None
    deadline = time.monotonic() + 300
    while position is None and time.monotonic() < deadline:
        nrepl_send(sock, '(lt)')
        time.sleep(3)
        position = probe_position(sock, game, game_log, tag, 8)
        tag += 1
    if position is None:
        say("goalc n'a pas pu se connecter au jeu. Jak reste au palais. Voir city-goalc.log.")
        return goalc
    say(f'liaison etablie, Jak est a {position}')

    # 3. Aller en ville par le point de reprise natif.
    nrepl_send(sock, f'(start \'play (get-continue-by-name *game-info* "{CITY_CONTINUE}"))')
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        time.sleep(3)
        tag += 1
        position = probe_position(sock, game, game_log, tag, 8)
        if position and abs(position[0] - 2240) < 60 and abs(position[2] + 41) < 60:
            break
    else:
        say("le point de reprise de la ville n'a pas repondu. Verifier le journal runtime.")
        return goalc
    say(f'arrivee en ville a {position}')
    time.sleep(3)

    # 4. Placer Jak dans la rue devant les maisons pilotes (meme logique que le lot herbe,
    #    ecrite sans macros pour rester lisible par un compilateur neuf : 1 m = 4096 unites).
    x, y, z = (value * 4096.0 for value in CITY_VIEWPOINT)
    nrepl_send(sock, '(when (and *target* (-> *target* control)) '
                     "(let ((destination (new 'stack-no-clear 'vector))) "
                     f'(set! (-> destination x) {x!r}) '
                     f'(set! (-> destination y) {y!r}) '
                     f'(set! (-> destination z) {z!r}) '
                     '(set! (-> destination w) 1.0) '
                     '(move-to-point! (-> *target* control) destination) '
                     '(vector-copy! (-> *target* root trans) destination) '
                     '(vector-copy! (-> *target* control transv) *zero-vector*)))')
    time.sleep(3)
    tag += 1
    position = probe_position(sock, game, game_log, tag, 10)
    say(f'Jak est place devant les maisons pilotes, position {position}')
    if capture:
        time.sleep(4)
        nrepl_send(sock, '(pc-screen-shot)')
        say('capture demandee (dossier screenshots du profil).')
    return goalc


profile = ROOT / 'profiles' / (args.variant if args.scene == 'arena' else f'{args.variant}-{args.scene}')
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
game_log = ROOT / f'{args.variant}-runtime.log'
goalc = None
with game_log.open('w', encoding='utf-8') as log:
    process = subprocess.Popen([str(runtime), '--game', 'jak3', '--proj-path', str(ROOT / 'data'),
                                '--config-path', str(profile), '--disable-ansi', '--',
                                '-fakeiso', '-boot', '-debug', '-nosound'], cwd=ROOT, stdout=log,
                                stderr=subprocess.STDOUT, env=environment,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    (ROOT / f'{args.variant}.pid').write_text(str(process.pid), encoding='utf-8')
    try:
        if args.scene == 'city':
            goalc = place_jak_in_city(process, game_log, args.capture)
        result = process.wait()
    finally:
        # goalc reste ouvert pendant la partie ; on le coupe net a la fin, sans passer par (e)
        # qui redemarrerait le jeu.
        if goalc is not None and goalc.poll() is None:
            goalc.kill()
if result:
    sys.exit(f'Le jeu a quitte avec le code {result}. Voir {args.variant}-runtime.log.')
