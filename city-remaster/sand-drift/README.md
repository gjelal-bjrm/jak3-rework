# Poussière de sable de la ville de Spargus

Les « petites vagues de poussière » de la ville sont, dans le jeu d'origine, des sprites ronds
`dirtpuff01` émis par 38 `part-spawner` (`group-waswide-topdust`, `waswide-part.gc` 1883) : une
bouffée de 1 m qui grossit à 2,7 m en 1,7 s, dérive vers +z et s'efface.

`SandDrift.h` (moteur, accroche dans `Sprite3.cpp` comme `MarketFruit`) consomme ces sprites quand la
caméra est dans la ville et redessine chaque bouffée **dans l'esprit de l'original** : un petit nuage
de sable rond, en deux lobes face caméra (lobe principal + lobe secondaire décalé qui se soulève),
avec :

- un contour érodé par du bruit (volutes lentes) au lieu du disque flou du sprite ;
- des volutes internes qui montent et dérivent, un grain fin ;
- un éclairage par le soleil (côté clair, côté ombre) ;
- un fondu doux au contact du sol et des murs (profondeur de scène `tex_T26`).

Cadence, positions, taille et enveloppe d'opacité restent celles des particules natives ; la graine de
bruit est la rotation native de la bouffée (stable pendant sa vie). Fondu au-delà de 90–150 m.

Première version (nappes allongées au sol) rejetée par l'utilisateur : trop éloignée de l'original.

## Installation

- `python city-remaster/sand-drift/install.py` : `sand_drift.vert/.frag` → `data/`, `engine-src/`,
  trois variantes + empreintes.
- Moteur : `python liquids-v3/build_engine.py` puis `python update_runtime.py` (jeu fermé).

## Tester

`python launch.py remaster --scene city --viewpoint 2492,27,-72 --face 2493,-58 --burst 5`
(rue de la ville basse, émetteur `waswide-part-76` à 15 m).
