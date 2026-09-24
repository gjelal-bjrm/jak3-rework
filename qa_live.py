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


def send(sock, form):
    data = form.encode('utf-8')
    sock.sendall(struct.pack('<II', len(data), 10) + data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scene'); ap.add_argument('name')
    ap.add_argument('--hour', type=float); ap.add_argument('--weather'); ap.add_argument('--eval', default='')
    ap.add_argument('--wait', type=float, default=2.5); ap.add_argument('--count', type=int, default=1)
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
    if a.weather:
        kind = -1 if a.weather == 'hasard' else WEATHERS.index(a.weather)
        send(sock, '(define-extern pc-remaster-weather-force (function int none))'); time.sleep(.3)
        send(sock, f'(pc-remaster-weather-force {kind})')
    for form in [f.strip() for f in a.eval.split(';;') if f.strip()]:
        send(sock, form); time.sleep(.3)
    time.sleep(a.wait)
    profile = ROOT / 'profiles' / f'remaster-{a.scene}' if a.scene != 'arena' else ROOT / 'profiles/remaster'
    shot = profile / 'OpenGOAL/jak3/screenshots/screenshot.png'
    out = ROOT / 'qa'; out.mkdir(exist_ok=True)
    for k in range(a.count):
        before = shot.stat().st_mtime if shot.exists() else 0
        send(sock, '(pc-screen-shot)')
        for _ in range(40):
            time.sleep(.25)
            if shot.exists() and shot.stat().st_mtime > before: break
        time.sleep(.4)
        target = out / f'live-{a.name}-{k:02d}.png'
        shutil.copy2(shot, target); print(target)
        if k + 1 < a.count: time.sleep(2.)
    sock.close()


if __name__ == '__main__': main()
