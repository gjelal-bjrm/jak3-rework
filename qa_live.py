"""Capture rapide sur la partie deja ouverte par le lanceur (sans relancer le jeu).

  python qa_live.py <scene> <nom> [--hour H] [--weather orage] [--eval "FORME;;FORME"] [--wait S] [--count N]

Se connecte au compilateur goalc du lanceur (nREPL, port 8189), envoie les formes demandees, attend,
prend N captures et les copie dans qa/live-<nom>-NN.png. Avec les shaders du ciel recharges a chaud,
on peut modifier data/.../modern_clouds.frag et reprendre une capture en quelques secondes.
"""
from pathlib import Path
import argparse, shutil, socket, struct, sys, time

ROOT = Path(__file__).resolve().parent
PORT = 8189
WEATHERS = ['beau-temps', 'voile', 'couvert', 'pluie', 'orage', 'neige', 'tempete-de-sable', 'brouillard']


def goal_event(target, message, *params):
    sets = ' '.join(f'(set! (-> event-data param {i}) (the-as uint {v}))' for i, v in enumerate(params))
    return ("(let ((event-data (new 'stack-no-clear 'event-message-block))) "
            f"(set! (-> event-data from) (-> (the-as process {target}) ppointer)) "
            f"(set! (-> event-data num-params) {len(params)}) (set! (-> event-data message) {message}) {sets} "
            f"(send-event-function {target} event-data))")


def aim_form(eye, target):
    import math
    f = [target[i] - eye[i] for i in range(3)]; L = math.sqrt(sum(c * c for c in f)); f = [c / L for c in f]
    r = [f[2], 0.0, -f[0]]; L = math.sqrt(sum(c * c for c in r)); r = [c / L for c in r]
    u = [f[1] * r[2] - f[2] * r[1], f[2] * r[0] - f[0] * r[2], f[0] * r[1] - f[1] * r[0]]
    p = [v * 4096.0 for v in eye]
    sets = ' '.join(f'(set! (-> m {vec} {axis}) {val!r})' for vec, vals in (('rvec', r), ('uvec', u), ('fvec', f)) for axis, val in zip('xyz', vals))
    return ("(let ((p (new 'stack-no-clear 'vector)) (m (new 'stack-no-clear 'matrix))) "
            f'(set! (-> p x) {p[0]!r}) (set! (-> p y) {p[1]!r}) (set! (-> p z) {p[2]!r}) (set! (-> p w) 1.0) '
            f'{sets} (set! (-> m rvec w) 0.0) (set! (-> m uvec w) 0.0) (set! (-> m fvec w) 0.0) '
            '(set! (-> m trans x) 0.0) (set! (-> m trans y) 0.0) (set! (-> m trans z) 0.0) (set! (-> m trans w) 1.0) '
            '(vector-copy! (-> *camera* slave 0 saved-pt) p) (vector-copy! (-> *camera* slave 0 trans) p) '
            '(matrix-copy! (-> *camera* slave 0 tracking inv-mat) m) (none))')


def send(sock, form):
    data = form.encode('utf-8')
    sock.sendall(struct.pack('<II', len(data), 10) + data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scene'); ap.add_argument('name'); ap.add_argument('--variant', default='remaster')
    ap.add_argument('--hour', type=float); ap.add_argument('--weather'); ap.add_argument('--eval', default='')
    ap.add_argument('--place', help='Jak : X,Y,Z/FX,FZ[/RECUL,HAUTEUR] (m) ; la camera se pose derriere lui'); ap.add_argument('--aim', help='camera : EX,EY,EZ/TX,TY,TZ (m), posee juste avant chaque capture'); ap.add_argument('--wait', type=float, default=2.5); ap.add_argument('--count', type=int, default=1)
    ap.add_argument('--freecam', help='camera libre posee en EX,EY,EZ/TX,TY,TZ (m) ; rendue au jeu apres la capture')
    ap.add_argument('--keep-freecam', action='store_true', help='laisse la camera libre (captures enchainees)')
    a = ap.parse_args()
    sock = socket.create_connection(('127.0.0.1', PORT), timeout=5)
    sock.settimeout(1)
    try: sock.recv(1024)
    except socket.timeout: pass
    tod = '(-> *time-of-day* 0)'
    if a.hour is not None:
        h = int(a.hour) % 24; m = int(round((a.hour - int(a.hour)) * 60)) % 60
        send(sock, goal_event(tod, "'change", "'ratio", '0.0'))
        send(sock, goal_event(tod, "'change", "'hour", str(h)))
        send(sock, goal_event(tod, "'change", "'minutes", str(m)))
    if a.place:
        import math
        parts = a.place.split('/')
        x, y, z = (float(v) for v in parts[0].split(','))
        fx, fz = (float(v) for v in parts[1].split(','))
        back, up = (float(v) for v in parts[2].split(',')) if len(parts) > 2 else (7.0, 2.5)
        send(sock, '(when (and *target* (-> *target* control)) '
                   "(let ((destination (new 'stack-no-clear 'vector))) "
                   f'(set! (-> destination x) {x*4096.0!r}) (set! (-> destination y) {y*4096.0!r}) (set! (-> destination z) {z*4096.0!r}) (set! (-> destination w) 1.0) '
                   '(move-to-point! (-> *target* control) destination) (vector-copy! (-> *target* root trans) destination) '
                   '(vector-copy! (-> *target* control transv) *zero-vector*)))')
        time.sleep(1.5)
        dx, dz = fx - x, fz - z; length = math.hypot(dx, dz) or 1.0
        yaw = math.atan2(dx, dz) + math.pi
        send(sock, '(when (and *target* (-> *target* control)) '
                   f'(quaternion-axis-angle! (-> *target* control quat) 0.0 1.0 0.0 {yaw!r}) '
                   f'(quaternion-axis-angle! (-> *target* root quat) 0.0 1.0 0.0 {yaw!r}))')
        time.sleep(.5)
        cx, cy, cz = (x - dx / length * back) * 4096.0, (y + up) * 4096.0, (z - dz / length * back) * 4096.0
        send(sock, "(let ((cam (new 'stack-no-clear 'vector))) "
                   f'(set! (-> cam x) {cx!r}) (set! (-> cam y) {cy!r}) (set! (-> cam z) {cz!r}) (set! (-> cam w) 1.0) '
                   + goal_event('*camera*', "'teleport-to-vector-start-string", 'cam') + ')')
        time.sleep(2.5)
    if a.weather:
        kind = -1 if a.weather == 'hasard' else WEATHERS.index(a.weather)
        send(sock, '(define-extern pc-remaster-weather-force (function int none))'); time.sleep(.3)
        send(sock, f'(pc-remaster-weather-force {kind})')
    for form in [f.strip() for f in a.eval.split(';;') if f.strip()]:
        send(sock, form); time.sleep(.3)
    time.sleep(a.wait)
    profile = ROOT / 'profiles' / (f'{a.variant}-{a.scene}' if a.scene != 'arena' else a.variant)
    shot = profile / 'OpenGOAL/jak3/screenshots/screenshot.png'
    out = ROOT / 'qa'; out.mkdir(exist_ok=True)
    if a.freecam:
        # camera libre du jeu (cam-free-floating) : garde la pose qu'on lui donne tant que la manette ne bouge pas
        send(sock, "(set-setting-by-param *setting-control* 'mode-name 'cam-free-floating 0 0)"); time.sleep(1.2)
        a.aim = a.freecam
    for k in range(a.count):
        before = shot.stat().st_mtime if shot.exists() else 0
        if a.aim:
            e, t = a.aim.split('/')
            send(sock, aim_form([float(v) for v in e.split(',')], [float(v) for v in t.split(',')])); time.sleep(.35)
        if a.freecam: time.sleep(.8)
        send(sock, '(pc-screen-shot)')
        for _ in range(40):
            time.sleep(.25)
            if shot.exists() and shot.stat().st_mtime > before: break
        time.sleep(.4)
        target = out / f'live-{a.name}-{k:02d}.png'
        shutil.copy2(shot, target); print(target)
        if k + 1 < a.count: time.sleep(2.)
    if a.freecam and not a.keep_freecam:
        send(sock, "(remove-setting-by-arg0 *setting-control* 'mode-name)")
    sock.close()


if __name__ == '__main__': main()
