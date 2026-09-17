# Fenêtres habitées autour du marché (WCB) — lot R5

Quatre vraies fenêtres découpées dans quatre bâtiments distincts du quartier du
marché de Spargus (niveau `wascityb`), chacune donnant sur une pièce meublée et
habitée. C'est le premier lot d'intérieurs hors de la ville basse (WCA), pour
répartir les habitants dans toute la ville.

| Fenêtre | Bâtiment natif | Position (m) | Côté de la place |
|---|---|---|---|
| `wcb-market-south-room` | TIE arbre 0, instance 271 | 1833 / 30,8 / −367 | sud-est, petite maison |
| `wcb-market-southeast-room` | TIE arbre 0, instance 2218 | 1842 / 30,5 / −361 | sud-est, grand bâtiment |
| `wcb-market-northeast-room` | TIE arbre 0, instance 1 | 1823 / 40,9 / −277 | nord-est, grand édifice |
| `wcb-market-west-room` | TIE arbre 1, instance 700 | 1698 / 42,4 / −284 | ouest |

Ouvertures de 3,2 × 2,8 m, appui à 1,7 ou 2,3 m au-dessus de la rue, pièces de
3,5 m de profondeur. L'encadrement en volume (tableaux épais, appui, linteau,
corniche, deux consoles) reprend la pierre du bâtiment concerné.

## Chaîne rejouée

1. `selection-market.json` puis `palace_mesh_bridge --export-selected` → `native-market.json`
   (zone X 1690–1870, Z −400 à −250, 268 436 triangles, 382 objets).
2. `survey.py` (dans Blender) : bâtiments à façades en pierre ou enduit, puis points de façade
   où l'ouverture tient dans un mur plan, avec 3,5 m libres derrière et le sol devant → `survey.json`.
   Les grands objets qui bordent directement la place sont des murets et rigoles de terrain,
   pas des maisons : les façades utilisables sont à 75–100 m du centre de la place.
3. `new-window-specs.json` : choix de quatre points, un par bâtiment, tournés vers la place.
   `frame_material` doit être un matériau des faces réellement découpées (exigence de l'audit).
4. `author.py` (dans Blender) → `wascityb-patch.json`, `window-anchors.json`, `market-houses.blend`.
5. `staging.py` : géométrie, ouvertures (`validate_openings.py`), couverture BVH, application,
   audit de préservation (163 contrôles) → `candidate.json`, `staging/wascityb.fr3`.
6. `install.py` : FR3 dans `data/` et `variants/remaster/`, ancres fusionnées avec les 9 de WCA
   (`window-anchors-all.json`), `runtime.json` régénéré (13 fenêtres, 12 pièces, 9 habitées),
   empreintes mises à jour → `installed.json`.

## Moteur

`CityInteriors.h` ne dessinait les pièces que si le niveau `wascitya` était chargé. Au marché,
seul `wascityb` l'est : la condition accepte maintenant les deux niveaux. Moteur recompilé
(`liquids-v3/build_engine.py`) et installé dans le lanceur par `update_runtime.py`.

## Tester

`Tester-MARCHE.cmd` place Jak devant la maison sud du marché. Les trois autres fenêtres sont à
quelques dizaines de mètres : grand bâtiment juste à droite, édifice nord-est de l'autre côté de
la place, maison de l'ouest en face.
