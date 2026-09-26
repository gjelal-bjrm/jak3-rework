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
parser.add_argument('--scene', choices=('arena', 'palace', 'city', 'market', 'coast', 'port', 'intro', 'desert', 'wasdoors'), default='arena')
parser.add_argument('--face', metavar='X,Z', help='scenes de ville : point (m) vers lequel Jak se tourne apres placement')
parser.add_argument('--burst', type=int, metavar='N', help='scenes de ville : N captures a 3 s d intervalle dans qa/ (test)')
parser.add_argument('--stops', metavar='X,Y,Z/FX,FZ;...', help='scenes de ville : apres le premier placement, enchaine ces arrets (position puis point vise), avec une rafale --burst a chacun')
parser.add_argument('--prepare-only', action='store_true')
parser.add_argument('--textures', choices=('fidele', 'genshin', 'sans'),
                    help="remaster : textures de l'arene (Codex couleurs d'origine, Codex couleurs vives, textures du jeu)")
parser.add_argument('--replace', action='store_true', help='ferme la partie deja ouverte au lieu de refuser de demarrer (tests)')
parser.add_argument('--hour', type=float, metavar='H', help="heure du jour a imposer apres le placement (0-24, decimales acceptees)")
parser.add_argument('--time-ratio', type=float, metavar='R', help="vitesse du temps (0 = fige, 1 = temps reel, 30 = un jour en 48 min)")
WEATHERS = ['beau-temps', 'voile', 'couvert', 'pluie', 'orage', 'neige', 'tempete-de-sable', 'brouillard']
parser.add_argument('--weather', choices=WEATHERS + ['hasard'],
                    help="meteo imposee apres le placement (sinon tirage au hasard selon la ville et l'heure)")
parser.add_argument('--eval', metavar='FORME;;FORME', help='tests : formes GOAL envoyees au jeu apres le placement (separees par ;;)')
parser.add_argument('--eval-end', metavar='FORME;;FORME', help='tests : formes GOAL envoyees apres les arrets et les heures')
parser.add_argument('--hours', metavar='H1,H2,...', help='tests : impose chaque heure a son tour et prend une rafale (qa/burst-<scene>-hNN-*.png)')
parser.add_argument('--sound', action='store_true', help='avec le son du jeu (sinon muet, pour les tests)')
parser.add_argument('--quit', action='store_true', help='ferme le jeu une fois les captures faites (tests enchaines)')
parser.add_argument('--capture', action='store_true',
                    help="scene city : prendre une capture d'ecran une fois Jak place (test)")
parser.add_argument('--viewpoint', metavar='X,Y,Z',
                    help='scene city : autre point de placement de Jak, en metres (test)')
parser.add_argument('--tour', action='store_true',
                    help='scenes de ville : passer devant chaque fenetre habitee et capturer (controle qualite)')
args = parser.parse_args()

# Les scenes de ville reutilisent la route de demarrage du palais ; le deplacement
# se fait ensuite en direct via goalc, sans toucher aux routes verifiees.
CITY_SCENES = {
    # point de reprise natif, position (x, z) attendue a l'arrivee, point de placement final (m)
    'city': {'continue': 'wascitya-seem', 'arrival': (2240.3, -40.8), 'viewpoint': (2270.0, 20.5, 3.0),
             'label': "devant l'appartement de l'entree de la ville (double fenetre, couple)"},
    'market': {'continue': 'wascityb-start', 'arrival': (1776.4, -375.5), 'viewpoint': (1821.1, 29.6, -359.6),
               'label': 'devant la maison sud du marche (fenetre habitee)'},
    'coast': {'continue': 'wascityb-start', 'arrival': (1776.4, -375.5), 'viewpoint': (1685.0, 20.0, -440.0),
              'face': (1450.0, -600.0), 'label': 'sur la cote de Spargus, face au large'},
    # Port de Haven (ctyport-start, level-info.gc) : eau native pour l'instant, le nouveau rendu de mer
    # n'est actif que dans la region de Spargus.
    'port': {'continue': 'ctyport-start', 'arrival': (193.0, 1754.0), 'viewpoint': (193.0, 17.3, 1754.0),
             'label': 'au port de Haven, point de reprise ctyport-start (eau native)'},
    # Desert : debut de l'histoire (Jak abandonne dans le desert), porte du desert de Spargus, grand desert.
    'intro': {'continue': 'wasintro-start', 'arrival': (2.5, -13.1), 'viewpoint': (2.5, 2.0, -13.1),
              'label': "dans le desert de l'intro (point de depart de l'histoire)"},
    'wasdoors': {'continue': 'wasdoors-desert', 'arrival': (2266.8, 167.0), 'viewpoint': (2266.8, 33.0, 167.0),
                 'label': 'a la porte du desert de Spargus (garage des vehicules)'},
    'desert': {'continue': 'desert-start', 'arrival': (2266.4, 258.1), 'viewpoint': (2266.4, 33.0, 258.1),
               'label': 'dans le grand desert, devant la porte de Spargus'},
}
route_scene = 'palace' if args.scene in CITY_SCENES else args.scene

lock = (ROOT / 'prototype.lock').open('a+b')
lock.seek(0)
for attempt in range(40):
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        break
    except OSError:
        if not args.replace:
            sys.exit('Le prototype est deja ouvert. Fermez sa fenetre avant de changer de version.')
        if attempt == 0:
            import subprocess
            subprocess.run(['taskkill', '/IM', 'gk.exe', '/F'], capture_output=True)   # --replace : on ferme la partie en cours
        time.sleep(.5)
else:
    sys.exit('Le prototype est deja ouvert et ne se ferme pas.')

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
# (--textures : choix retire le 26/09, textures Genshin retenues ; niveaux construits par remaster-build/build.py)
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


def attach_repl(game, game_log, say):
    """Demarre goalc, le relie au jeu et verifie la liaison. Retourne (goalc, sock, position, tag) ;
    sock vaut None si la liaison a echoue (le jeu continue sans pilotage)."""
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
    if args.variant != 'remaster':
        time.sleep(22)          # le moteur officiel n'ecrit pas le marqueur du prototype : delai fixe
    while args.variant == 'remaster' and 'SPARGUS-PROTOTYPE:' not in log_text(game_log):
        if game.poll() is not None or time.monotonic() > deadline:
            say("le jeu n'a pas signale son demarrage. Jak reste au palais.")
            return goalc, None, None, 0
        time.sleep(1)
    say('jeu demarre')

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
        return goalc, None, None, tag
    say(f'liaison etablie, Jak est a {position}')
    return goalc, sock, position, tag


def run_stops(sock, game, game_log, tag, say):
    """Arrets supplementaires --stops : "X,Y,Z/FX,FZ" (position en m, puis point vise facultatif), rafale a chacun."""
    for index, stop in enumerate(s for s in (args.stops or '').split(';') if s.strip()):
        where, _, toward = stop.partition('/')
        sx, sy, sz = (float(v) for v in where.split(','))
        move_jak(sock, sx, sy, sz)
        time.sleep(3)
        tag += 1
        position = probe_position(sock, game, game_log, tag, 10) or (sx, sy, sz)
        if toward.strip():
            fx, fz = (float(v) for v in toward.split(','))
            face_jak(sock, position, (fx, fz))
        say(f'arret {index + 1} : Jak en {tuple(round(v, 1) for v in position)}' + (f', tourne vers ({toward})' if toward.strip() else ''))
        time.sleep(4 if position[1] > 1.5 or args.scene != 'port' else 9)   # dans l'eau, la camera met plus longtemps a redescendre derriere Jak
        burst(sock, profile, args.burst or 1, f'burst-{args.scene}-{index + 1}', say)
    return tag


def capture_in_scene(game, game_log):
    """Scenes arene / palais : pas de teleportation par defaut ; --viewpoint, --face, --burst et --stops comme en ville."""
    started = time.monotonic()

    def say(message):
        print(f'{args.scene.upper()} [+{time.monotonic() - started:3.0f}s] : {message}', flush=True)

    goalc, sock, position, tag = attach_repl(game, game_log, say)
    if sock is None: return goalc
    time.sleep(3)
    if args.viewpoint:
        move_jak(sock, *(float(v) for v in args.viewpoint.split(',')))
        time.sleep(3)
        tag += 1
        position = probe_position(sock, game, game_log, tag, 10) or position
        say(f'Jak est place en {position}')
    if args.face and position:
        face_jak(sock, position, tuple(float(v) for v in args.face.split(',')))
        time.sleep(4)
    apply_time_options(sock, say)
    if args.burst:
        burst(sock, profile, args.burst, f'burst-{args.scene}', say)
    run_stops(sock, game, game_log, tag, say)
    run_hours(sock, say)
    run_eval_end(sock, say)
    if args.quit: game.kill()
    return goalc


def place_jak_in_city(game, game_log, capture):
    scene = CITY_SCENES[args.scene]
    started = time.monotonic()

    def say(message):
        print(f'VILLE [+{time.monotonic() - started:3.0f}s] : {message}', flush=True)

    goalc, sock, position, tag = attach_repl(game, game_log, say)
    if sock is None: return goalc

    # 3. Aller en ville par le point de reprise natif de la scene.
    nrepl_send(sock, f'(start \'play (get-continue-by-name *game-info* "{scene["continue"]}"))')
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        time.sleep(3)
        tag += 1
        position = probe_position(sock, game, game_log, tag, 8)
        if position and abs(position[0] - scene['arrival'][0]) < 60 and abs(position[2] - scene['arrival'][1]) < 60:
            break
    else:
        say("le point de reprise de la ville n'a pas repondu. Verifier le journal runtime.")
        return goalc
    say(f'arrivee en ville a {position}')
    time.sleep(3)

    # 4. Placer Jak dans la rue devant les maisons pilotes (meme logique que le lot herbe,
    #    ecrite sans macros pour rester lisible par un compilateur neuf : 1 m = 4096 unites).
    viewpoint = tuple(float(v) for v in args.viewpoint.split(',')) if args.viewpoint else scene['viewpoint']
    x, y, z = (value * 4096.0 for value in viewpoint)
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
    say(f'Jak est place {scene["label"]}, position {position}')
    face = tuple(float(v) for v in args.face.split(',')) if args.face else scene.get('face')
    if face and position:
        face_jak(sock, position, face)
        say(f'Jak se tourne vers {face} (la camera suit en quelques secondes)')
        time.sleep(4)
    apply_time_options(sock, say)
    if capture:
        time.sleep(4)
        nrepl_send(sock, '(pc-screen-shot)')
        say('capture demandee (dossier screenshots du profil).')
    if args.burst:
        burst(sock, profile, args.burst, f'burst-{args.scene}', say)
    run_stops(sock, game, game_log, tag, say)
    run_hours(sock, say)
    run_eval_end(sock, say)
    if args.tour:
        tour(sock, game, game_log, tag, say)
    if args.quit: game.kill()
    return goalc


def face_jak(sock, position, face):
    """Tourne Jak (et donc la camera, qui suit) vers le point (x, z) en metres."""
    import math
    dx, dz = face[0] - position[0], face[1] - position[2]
    length = math.hypot(dx, dz) or 1.0
    yaw = math.atan2(dx, dz) + math.pi   # l'avant de Jak est -Z a rotation nulle (verifie au port)
    nrepl_send(sock, '(when (and *target* (-> *target* control)) '
                     f'(quaternion-axis-angle! (-> *target* control quat) 0.0 1.0 0.0 {yaw!r}) '
                     f'(quaternion-axis-angle! (-> *target* root quat) 0.0 1.0 0.0 {yaw!r}))')
    # Camera replacee 7 m derriere Jak (a l'oppose du point vise), 2,5 m plus haut : elle regarde Jak,
    # donc dans la direction visee, puis reprend son suivi normal depuis la.
    cx = (position[0] - dx / length * 7.0) * 4096.0
    cy = (position[1] + 2.5) * 4096.0
    cz = (position[2] - dz / length * 7.0) * 4096.0
    time.sleep(0.5)
    nrepl_send(sock, "(let ((cam (new 'stack-no-clear 'vector))) "
                     f'(set! (-> cam x) {cx!r}) (set! (-> cam y) {cy!r}) (set! (-> cam z) {cz!r}) (set! (-> cam w) 1.0) '
                     + goal_event('*camera*', "'teleport-to-vector-start-string", 'cam') + ')')


def goal_event(target, message, *params):
    """Forme GOAL explicite equivalente a (send-event target message params...) : les macros ne sont pas
    disponibles dans le compilateur neuf du lanceur. Les parametres sont des textes GOAL deja formes."""
    sets = ' '.join(f'(set! (-> event-data param {i}) (the-as uint {value}))' for i, value in enumerate(params))
    return ("(let ((event-data (new 'stack-no-clear 'event-message-block))) "
            f"(set! (-> event-data from) (-> (the-as process {target}) ppointer)) "   # send-event-function ignore les messages sans expediteur
            f"(set! (-> event-data num-params) {len(params)}) "
            f"(set! (-> event-data message) {message}) {sets} "
            f"(send-event-function {target} event-data))")


TIME_OF_DAY = '(-> *time-of-day* 0)'


def set_time(sock, hour=None, ratio=None):
    """Impose l'heure et/ou la vitesse du temps du jeu (evenements natifs du processus *time-of-day*)."""
    if ratio is not None:
        nrepl_send(sock, goal_event(TIME_OF_DAY, "'change", "'ratio", f'{float(ratio)!r}'))
    if hour is not None:
        h = int(hour) % 24; m = int(round((hour - int(hour)) * 60)) % 60
        nrepl_send(sock, goal_event(TIME_OF_DAY, "'change", "'hour", str(h)))
        nrepl_send(sock, goal_event(TIME_OF_DAY, "'change", "'minutes", str(m)))
        nrepl_send(sock, goal_event(TIME_OF_DAY, "'change", "'seconds", '0'))


def apply_time_options(sock, say):
    if args.weather:
        kind = -1 if args.weather == 'hasard' else WEATHERS.index(args.weather)
        nrepl_send(sock, '(define-extern pc-remaster-weather-force (function int none))'); time.sleep(.5)
        nrepl_send(sock, f'(pc-remaster-weather-force {kind})'); say(f'meteo : {args.weather}')
    for form in [f.strip() for f in (args.eval or '').split(';;') if f.strip()]:
        nrepl_send(sock, form); say(f'eval : {form[:70]}'); time.sleep(1.5)
    if args.hour is not None or args.time_ratio is not None:
        set_time(sock, args.hour, args.time_ratio)
        say(f"heure {args.hour if args.hour is not None else 'inchangee'}, vitesse {args.time_ratio if args.time_ratio is not None else 'inchangee'}")
        time.sleep(3)


def run_eval_end(sock, say):
    for form in [f.strip() for f in (args.eval_end or '').split(';;') if f.strip()]:
        nrepl_send(sock, form); say(f'eval-end : {form[:70]}'); time.sleep(1.5)


def run_hours(sock, say):
    """--hours : pour chaque heure, l'impose, laisse le ciel se mettre a jour et prend une rafale."""
    for h in [float(v) for v in (args.hours or '').split(',') if v.strip()]:
        set_time(sock, h, 0.0)
        say(f'heure {h:g}')
        time.sleep(5)
        burst(sock, profile, args.burst or 1, f'burst-{args.scene}-h{int(h):02d}', say)


def burst(sock, profile, count, prefix, say):
    """count captures a 3 s d'intervalle, copiees dans qa/<prefix>-NN.png."""
    shot = profile / 'OpenGOAL/jak3/screenshots/screenshot.png'; out = ROOT / 'qa'; out.mkdir(exist_ok=True)
    for k in range(count):
        time.sleep(3)
        before = shot.stat().st_mtime if shot.exists() else 0
        nrepl_send(sock, '(pc-screen-shot)')
        for _ in range(30):
            time.sleep(.3)
            if shot.exists() and shot.stat().st_mtime > before: break
        time.sleep(.4)
        if shot.exists(): shutil.copy2(shot, out / f'{prefix}-{k:02d}.png')
    say(f'rafale : {count} captures {prefix}-NN.png dans {out}')


def move_jak(sock, x, y, z):
    x, y, z = (v * 4096.0 for v in (x, y, z))
    nrepl_send(sock, '(when (and *target* (-> *target* control)) '
                     "(let ((destination (new 'stack-no-clear 'vector))) "
                     f'(set! (-> destination x) {x!r}) (set! (-> destination y) {y!r}) (set! (-> destination z) {z!r}) (set! (-> destination w) 1.0) '
                     '(move-to-point! (-> *target* control) destination) '
                     '(vector-copy! (-> *target* root trans) destination) '
                     '(vector-copy! (-> *target* control transv) *zero-vector*)))')


def aim_camera(sock, eye, target):
    """Pose la camera du jeu en un point, tournee vers une cible (metres). Meme methode que les captures de Codex."""
    import math
    f = [target[i] - eye[i] for i in range(3)]; L = math.sqrt(sum(c * c for c in f)); f = [c / L for c in f]
    up = (0.0, 1.0, 0.0)
    r = [up[1] * f[2] - up[2] * f[1], up[2] * f[0] - up[0] * f[2], up[0] * f[1] - up[1] * f[0]]; L = math.sqrt(sum(c * c for c in r)); r = [c / L for c in r]
    u = [f[1] * r[2] - f[2] * r[1], f[2] * r[0] - f[0] * r[2], f[0] * r[1] - f[1] * r[0]]
    p = [v * 4096.0 for v in eye]
    sets = ' '.join(f'(set! (-> m {vec} {axis}) {val!r})' for vec, vals in (('rvec', r), ('uvec', u), ('fvec', f)) for axis, val in zip('xyz', vals))
    nrepl_send(sock, "(let ((p (new 'stack-no-clear 'vector)) (m (new 'stack-no-clear 'matrix))) "
                     f'(set! (-> p x) {p[0]!r}) (set! (-> p y) {p[1]!r}) (set! (-> p z) {p[2]!r}) (set! (-> p w) 1.0) '
                     f'{sets} (set! (-> m rvec w) 0.0) (set! (-> m uvec w) 0.0) (set! (-> m fvec w) 0.0) '
                     '(set! (-> m trans x) 0.0) (set! (-> m trans y) 0.0) (set! (-> m trans z) 0.0) (set! (-> m trans w) 1.0) '
                     '(vector-copy! (-> *camera* slave 0 saved-pt) p) (vector-copy! (-> *camera* slave 0 trans) p) '
                     '(matrix-copy! (-> *camera* slave 0 tracking inv-mat) m) (none))')


def tour(sock, game, game_log, tag, say):
    """Controle qualite : pour chaque fenetre habitee, place Jak dans la rue, vise la fenetre, capture."""
    anchors = json.loads((ROOT / 'city-remaster/city-block-v3/interiors/window-anchors-final.json').read_text(encoding='utf-8'))
    out = ROOT / 'qa'; out.mkdir(exist_ok=True)
    shot = profile / 'OpenGOAL/jak3/screenshots/screenshot.png'
    current_level = None
    for w in anchors:
        continue_point = {'wascitya': ('wascitya-seem', (2240.3, -40.8)), 'wascityb': ('wascityb-start', (1776.4, -375.5))}[w['level']]
        if w['level'] != current_level:
            nrepl_send(sock, f'(start \'play (get-continue-by-name *game-info* "{continue_point[0]}"))')
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                time.sleep(3); tag += 1
                position = probe_position(sock, game, game_log, tag, 8)
                if position and abs(position[0] - continue_point[1][0]) < 60 and abs(position[2] - continue_point[1][1]) < 60: break
            current_level = w['level']; time.sleep(2)
        cam = w['street_camera']; centre = w['center']
        move_jak(sock, cam[0], cam[1] + .3, cam[2]); time.sleep(4)
        eye = (cam[0], cam[1] + 1.4, cam[2])
        aim_camera(sock, eye, (centre[0], centre[1], centre[2])); time.sleep(.4)
        before = shot.stat().st_mtime if shot.exists() else 0
        nrepl_send(sock, '(pc-screen-shot)')
        for _ in range(30):
            time.sleep(.3)
            if shot.exists() and shot.stat().st_mtime > before: break
        time.sleep(.5)
        if shot.exists(): shutil.copy2(shot, out / f'tour-{w["id"]}.png')
        say(f'capture {w["id"]}')
    say(f'tour termine : {len(anchors)} captures dans {out}')


profile = ROOT / 'profiles' / (args.variant if args.scene == 'arena' else f'{args.variant}-{args.scene}')
profile.mkdir(parents=True, exist_ok=True)
settings = profile / 'OpenGOAL/jak3/settings'
if not settings.exists():
    shutil.copytree(ROOT / 'profiles/original/OpenGOAL/jak3/settings', settings)
pc_settings = settings / 'pc-settings.gc'
if pc_settings.exists():
    content = pc_settings.read_text(encoding='utf-8')
    if args.sound:
        # son du jeu : volumes d'origine (effets .50, musique .40, dialogues .75)
        volumes = {'sfx': '0.5000', 'music': '0.4000', 'dialog': '0.7500'}
        audible = re.sub(r'(\(memcard-volume-(sfx|music|dialog)\s+)[^)]*',
                         lambda m: m.group(1) + volumes[m.group(2)], content)
        if audible != content:
            pc_settings.write_text(audible, encoding='utf-8')
    else:
        muted = re.sub(r'(\(memcard-volume-(?:sfx|music|dialog)\s+)[^)]*', r'\g<1>0.0000', content)
        if muted != content:
            backup = pc_settings.with_name('pc-settings-before-mute.gc')
            if not backup.exists():
                shutil.copy2(pc_settings, backup)
            pc_settings.write_text(muted, encoding='utf-8')
# Clavier toujours actif, en plus de la manette : OpenGOAL coupe le clavier des qu'il detecte une manette
# (l'utilisateur ne pouvait plus deplacer Jak au clavier). Touches d'origine W A S D (clavier suisse QWERTZ).
input_settings = settings / 'input-settings.json'
if input_settings.exists():
    try:
        inputs = json.loads(input_settings.read_text(encoding='utf-8'))
        changed = not inputs.get('keyboard_enabled')
        inputs['keyboard_enabled'] = True
        if changed:
            input_settings.write_text(json.dumps(inputs, indent=2), encoding='utf-8')
    except ValueError:
        pass
environment = os.environ.copy()
if args.weather and args.weather != 'hasard':
    environment['REMASTER_WEATHER_START'] = args.weather   # meteo installee des la premiere image (tests)
if not args.sound:
    environment['OPENGOAL_TEST_MUTE'] = '1'
game_log = ROOT / f'{args.variant}-runtime.log'
goalc = None
with game_log.open('w', encoding='utf-8') as log:
    process = subprocess.Popen([str(runtime), '--game', 'jak3', '--proj-path', str(ROOT / 'data'),
                                '--config-path', str(profile), '--disable-ansi', '--',
                                '-fakeiso', '-boot', '-debug'] + ([] if args.sound else ['-nosound']), cwd=ROOT, stdout=log,
                                stderr=subprocess.STDOUT, env=environment,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    (ROOT / f'{args.variant}.pid').write_text(str(process.pid), encoding='utf-8')
    try:
        if args.scene in CITY_SCENES:
            goalc = place_jak_in_city(process, game_log, args.capture)
        elif args.burst or args.stops or args.viewpoint or args.hours or args.eval or args.weather or args.hour is not None or args.time_ratio is not None:
            goalc = capture_in_scene(process, game_log)
        result = process.wait()
    finally:
        # goalc reste ouvert pendant la partie ; on le coupe net a la fin, sans passer par (e)
        # qui redemarrerait le jeu.
        if goalc is not None and goalc.poll() is None:
            goalc.kill()
if result and not args.quit:
    sys.exit(f'Le jeu a quitte avec le code {result}. Voir {args.variant}-runtime.log.')
