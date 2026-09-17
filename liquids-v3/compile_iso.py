"""Recompile le code GOAL modifie et reconstruit les archives (equivalent de (mi) dans goalc).

Demarre goalc officiel v0.3.6 sur data/, envoie (mi) par nREPL, attend que l'archive visee soit
reecrite, puis arrete goalc. Usage : python liquids-v3/compile_iso.py [out/jak3/iso/WASSTADA.DGO]
Le jeu ne doit pas tourner (port nREPL 8189 partage avec le lanceur).
"""
from pathlib import Path
import socket, struct, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[1]
GOALC = ROOT.parents[1] / 'versions/official/v0.3.6/goalc.exe'
PORT = 8189


def send(sock, form):
    data = form.encode('utf-8'); sock.sendall(struct.pack('<II', len(data), 10) + data)


def main(target):
    target = ROOT / 'data' / target
    before = target.stat().st_mtime if target.exists() else 0
    log = (ROOT / 'liquids-v3/compile-iso.log').open('w', encoding='utf-8')
    goalc = subprocess.Popen([str(GOALC), '--game', 'jak3', '--proj-path', str(ROOT / 'data'), '--port', str(PORT)],
                             cwd=ROOT, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 90; sock = None
        while sock is None and time.monotonic() < deadline:
            try:
                sock = socket.create_connection(('127.0.0.1', PORT), timeout=2); sock.settimeout(5)
                try: sock.recv(1024)
                except socket.timeout: pass
            except OSError: time.sleep(1)
        if sock is None: sys.exit('goalc injoignable')
        send(sock, '(mi)'); print('(mi) envoye, compilation...', flush=True)
        deadline = time.monotonic() + 1500
        while time.monotonic() < deadline:
            time.sleep(5)
            if goalc.poll() is not None: sys.exit(f'goalc s est arrete (code {goalc.returncode}), voir compile-iso.log')
            if target.exists() and target.stat().st_mtime > before:
                time.sleep(25)          # laisser finir les autres archives
                print('archive reconstruite :', target.relative_to(ROOT)); return
            text = (ROOT / 'liquids-v3/compile-iso.log').read_text(encoding='utf-8', errors='replace')
            if 'Compilation Error' in text:
                sys.exit('erreur de compilation GOAL : voir liquids-v3/compile-iso.log')
        sys.exit('delai depasse : archive non reecrite ; voir compile-iso.log')
    finally:
        if goalc.poll() is None: goalc.kill()


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/jak3/iso/WASSTADA.DGO')
