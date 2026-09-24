"""Evalue des formes GOAL dans la partie ouverte et affiche la sortie (lue dans city-goalc.log).

  python qa_query.py "(format #t \"rain ~f~%\" (-> *setting-control* user-current rain))" [...]
"""
from pathlib import Path
import socket, struct, sys, time
ROOT = Path(__file__).resolve().parent
LOG = ROOT / 'city-goalc.log'


def main():
    start = LOG.stat().st_size if LOG.exists() else 0
    s = socket.create_connection(('127.0.0.1', 8189), timeout=5); s.settimeout(1)
    try: s.recv(1024)
    except socket.timeout: pass
    for form in sys.argv[1:]:
        d = form.encode('utf-8'); s.sendall(struct.pack('<II', len(d), 10) + d); time.sleep(.4)
    time.sleep(1.2); s.close()
    with open(LOG, 'rb') as f:
        f.seek(start); print(f.read().decode('utf-8', 'replace')[-4000:])


if __name__ == '__main__': main()
