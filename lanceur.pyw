"""Lanceur de tests du remaster : une fenetre, pas de ligne de commande.

Double-clic sur LANCEUR-DE-TESTS.cmd (ou sur ce fichier). On choisit le lieu, la meteo, le moment de la
journee et la version (remaster ou jeu d'origine pour comparer), puis « Lancer ». La fenetre suit le
demarrage et peut fermer le jeu. Les derniers choix sont memorises (lanceur-choix.json).
"""
from pathlib import Path
import json, subprocess, sys, threading, time
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parent
PYTHON = Path(sys.executable).with_name('python.exe')
LOG = ROOT / 'qa' / 'lanceur.log'
CHOICES = ROOT / 'lanceur-choix.json'
NO_WINDOW = 0x08000000

PLACES = [
    ('Arène de Spargus (lave)', ['--scene', 'arena']),
    ('Palais de Spargus (bassins, chutes, brume)', ['--scene', 'palace']),
    ('Côte de Spargus (mer, Jak dans l’eau)', ['--scene', 'coast']),
    ('Plage de Spargus (vagues, sable mouillé)', ['--scene', 'coast', '--viewpoint', '1545,11,-412', '--face', '1520,-470']),
    ('Ville de Spargus (entrée)', ['--scene', 'city']),
    ('Marché de Spargus', ['--scene', 'market']),
    ('Port de Haven (mer bleue, quai)', ['--scene', 'port']),
]
WEATHERS = [
    ('Au hasard (comme en jeu)', 'hasard'), ('Beau temps', 'beau-temps'), ('Voilé', 'voile'),
    ('Couvert', 'couvert'), ('Pluie', 'pluie'), ('Orage', 'orage'), ('Neige', 'neige'),
    ('Tempête de sable (Spargus)', 'tempete-de-sable'), ('Brouillard matinal', 'brouillard'),
]
HOURS = [
    ('Comme en jeu (9 h, le jour avance)', None), ('Aube (6 h 30)', 6.5), ('Matin (9 h)', 9.0),
    ('Midi (13 h)', 13.0), ('Après-midi (16 h)', 16.0), ('Coucher du soleil (18 h 30)', 18.5), ('Nuit (22 h)', 22.0),
]
# Lignes du journal du lanceur montrees dans la fenetre (le reste est technique).
SHOWN = ('jeu demarre', 'liaison etablie', 'Jak est', 'arrivee', 'meteo', 'heure', 'Erreur', 'erreur', 'ferme')


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Jak 3 Remaster – tests')
        self.resizable(False, False)
        self.process = None
        saved = {}
        try: saved = json.loads(CHOICES.read_text(encoding='utf-8'))
        except Exception: pass
        pad = {'padx': 10, 'pady': 4}
        frame = ttk.Frame(self, padding=12); frame.grid()
        ttk.Label(frame, text='Tester le remaster', font=('Segoe UI', 14, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))

        ttk.Label(frame, text='Lieu').grid(row=1, column=0, sticky='nw', **pad)
        self.place = tk.IntVar(value=saved.get('place', 1))
        places = ttk.Frame(frame); places.grid(row=1, column=1, sticky='w')
        for i, (label, _) in enumerate(PLACES):
            ttk.Radiobutton(places, text=label, variable=self.place, value=i).grid(row=i, column=0, sticky='w')

        ttk.Label(frame, text='Météo').grid(row=2, column=0, sticky='w', **pad)
        self.weather = ttk.Combobox(frame, state='readonly', width=36, values=[w[0] for w in WEATHERS])
        self.weather.current(min(saved.get('weather', 0), len(WEATHERS) - 1)); self.weather.grid(row=2, column=1, sticky='w', **pad)

        ttk.Label(frame, text='Moment').grid(row=3, column=0, sticky='w', **pad)
        self.hour = ttk.Combobox(frame, state='readonly', width=36, values=[h[0] for h in HOURS])
        self.hour.current(min(saved.get('hour', 0), len(HOURS) - 1)); self.hour.grid(row=3, column=1, sticky='w', **pad)
        self.freeze = tk.BooleanVar(value=saved.get('freeze', False))
        ttk.Checkbutton(frame, text='Figer l’heure (le soleil ne bouge plus)', variable=self.freeze).grid(row=4, column=1, sticky='w', padx=10)

        ttk.Label(frame, text='Version').grid(row=5, column=0, sticky='nw', **pad)
        self.variant = tk.StringVar(value=saved.get('variant', 'remaster'))
        versions = ttk.Frame(frame); versions.grid(row=5, column=1, sticky='w', **pad)
        ttk.Radiobutton(versions, text='Remaster (nouvelle version)', variable=self.variant, value='remaster', command=self.refresh).grid(row=0, column=0, sticky='w')
        ttk.Radiobutton(versions, text='Jeu d’origine (pour comparer)', variable=self.variant, value='original', command=self.refresh).grid(row=1, column=0, sticky='w')

        buttons = ttk.Frame(frame); buttons.grid(row=6, column=0, columnspan=2, pady=(10, 4))
        self.start_button = ttk.Button(buttons, text='▶  Lancer', command=self.start, width=18)
        self.start_button.grid(row=0, column=0, padx=6)
        ttk.Button(buttons, text='■  Fermer le jeu', command=self.stop, width=18).grid(row=0, column=1, padx=6)

        self.status = tk.Text(frame, width=62, height=8, font=('Segoe UI', 9), state='disabled', relief='flat', background='#f3f3f3')
        self.status.grid(row=7, column=0, columnspan=2, pady=(6, 0))
        self.say('Choisis un lieu, une météo et un moment, puis clique sur « Lancer ».\n'
                 'Le jeu met environ 30 secondes à se mettre en place.')
        self.refresh()
        self.protocol('WM_DELETE_WINDOW', self.destroy)

    def refresh(self):
        original = self.variant.get() == 'original'
        self.weather.configure(state='disabled' if original else 'readonly')

    def say(self, text, replace=True):
        self.status.configure(state='normal')
        if replace: self.status.delete('1.0', 'end')
        self.status.insert('end', text + '\n'); self.status.see('end')
        self.status.configure(state='disabled')

    def start(self):
        variant = self.variant.get()
        args = [str(PYTHON), str(ROOT / 'launch.py'), variant, '--replace'] + PLACES[self.place.get()][1]
        if variant == 'remaster':
            args += ['--weather', WEATHERS[self.weather.current()][1]]
        hour = HOURS[self.hour.current()][1]
        if hour is not None: args += ['--hour', str(hour)]
        if self.freeze.get(): args += ['--time-ratio', '0']
        try:
            CHOICES.write_text(json.dumps({'place': self.place.get(), 'weather': self.weather.current(),
                                           'hour': self.hour.current(), 'freeze': self.freeze.get(),
                                           'variant': variant}), encoding='utf-8')
        except Exception: pass
        LOG.parent.mkdir(exist_ok=True)
        log = LOG.open('w', encoding='utf-8')
        self.say(f'Lancement : {PLACES[self.place.get()][0]}'
                 + (f', {WEATHERS[self.weather.current()][0].lower()}' if variant == 'remaster' else ', jeu d’origine')
                 + f', {HOURS[self.hour.current()][0].lower()}…')
        self.process = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        threading.Thread(target=self.follow, args=(self.process,), daemon=True).start()

    def follow(self, process):
        seen = 0
        while True:
            try: lines = LOG.read_text(encoding='utf-8', errors='replace').splitlines()
            except Exception: lines = []
            for line in lines[seen:]:
                if any(key in line for key in SHOWN):
                    text = line.split(': ', 1)[-1] if ' : ' in line else line
                    self.after(0, self.say, '• ' + text.strip(), False)
            seen = len(lines)
            if process.poll() is not None:
                code = process.returncode
                message = 'Le jeu est fermé.' if code in (0, 1) else f'Le lanceur s’est arrêté (code {code}). Voir qa/lanceur.log.'
                self.after(0, self.say, message, False)
                return
            time.sleep(1)

    def stop(self):
        for exe in ('gk.exe', 'goalc.exe'):
            subprocess.run(['taskkill', '/IM', exe, '/F'], capture_output=True, creationflags=NO_WINDOW)
        self.say('Jeu fermé.', False)


if __name__ == '__main__':
    Launcher().mainloop()
