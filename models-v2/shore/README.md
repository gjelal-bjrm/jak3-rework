# Côte de Spargus : vagues de bord et lames sur les rochers

Remplace les effets natifs de la côte (sprites `wave-foam` / `water-froth` : nappes fumeuses au ras
de l'eau ; `splash` : éclaboussures une fois par minute) par :

1. **Vagues de bord procédurales** (`shore_waves.glsl`, insérées dans `ocean_swell.glsl` par
   `apply_ocean.py`) : trains de houle qui se cambrent en approchant du sable (distance signée au
   trait de côte `shore_tables.glsl`), déferlent avec écume à 3–13 m du bord, puis une lame mince
   monte le sable sur 5,5 m et redescend (période 7,4 s). Hauteur dans le vertex shader de la mer,
   pente et écume dans le fragment.
2. **Sable mouillé** (`apply_beach.py`, patch idempotent du `tfrag3.frag` installé) : bande humide
   sombre sous la limite des lames, pellicule brillante laissée par la lame qui recule (même horloge
   `fluid_time` = `ocean_time`).
3. **Lames sur les rochers** (`CoastalBreakers::render_sites`, appelé par `ModernOceanSurface` après
   la mer) : aux 15 sites natifs `group-part-water-rocks-splash` (`CoastSplashSites.h`), une lame
   toutes les 11–19 s, orientée le long du rocher, avec nappe blanche chargée d'air, sommet déchiré
   en doigts, embruns et brume (`coast_breaker.*`, `coast_spray.*`).

## Chaîne

- `selection-beach.json` → `palace_mesh_bridge --export-selected` → `beach-native.json` (46 Mo, ignoré
  par git) : triangles natifs de la baie.
- Analyse (ligne d'eau à y = 9 m, pente du sable 1:8) → `waterline.json`, `waterline-segments.json`.
- `build_shore_tables.py` → `shore_tables.glsl` (trait de côte, 10 points) et `CoastSplashSites.h`
  (copié dans `engine-src/.../ocean/`).
- `python models-v2/apply_ocean.py` puis `python sync_variant.py <shaders>` ; `python models-v2/shore/apply_beach.py`.
- Moteur : `python liquids-v3/build_engine.py` puis `python update_runtime.py` (fermer le jeu avant).

## Tester

`python launch.py remaster --scene coast --viewpoint 1545,11,-412 --face 1520,-470 --burst 5`
(Jak sur le sable, face à la baie) ; `--stops "1650,10,-425/1636,-408"` pour les rochers.
