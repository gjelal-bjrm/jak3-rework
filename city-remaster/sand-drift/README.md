# Sable porté par le vent (ville de Spargus)

Les « petites vagues de poussière » de la ville sont, dans le jeu d'origine, des sprites ronds
`dirtpuff01` émis par 38 `part-spawner` (`group-waswide-topdust`, `waswide-part.gc` 1883) : une
bouffée de 1 m qui grossit à 2,7 m en 1,7 s, dérive vers +z et s'efface.

`SandDrift.h` (moteur, accroche dans `Sprite3.cpp` comme `MarketFruit`) consomme ces sprites quand la
caméra est dans la ville et les remaille en :

- une **nappe de sable au ras du sol**, allongée dans le sens du vent (3,6 × 1,4 fois l'échelle
  native), aux stries qui filent à 3–6 m/s, grain fin, fondu doux au contact du sol et des murs
  (profondeur de scène `tex_T26`) ;
- un **voile soulevé** face caméra, bas et transparent, qui s'efface en hauteur.

Cadence, positions, échelle et enveloppe d'opacité restent celles des particules natives ; la graine
de bruit est la rotation native de la bouffée (stable pendant sa vie). Couleur sable `(0,76 ; 0,66 ; 0,51)`
mêlée à 22 % de brouillard de scène. Fondu au-delà de 90–150 m.

## Installation

- `python city-remaster/sand-drift/install.py` : `sand_drift.vert/.frag` → `data/`, `engine-src/`,
  trois variantes + empreintes.
- Moteur : `python liquids-v3/build_engine.py` puis `python update_runtime.py` (jeu fermé).

## Tester

`python launch.py remaster --scene city --viewpoint 2470,24,-90 --face 2492,-58 --burst 4`
(rue de la ville basse, émetteur `waswide-part-76` à 35 m).
