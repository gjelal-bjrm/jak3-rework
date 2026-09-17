# Mer moderne : régions

Le rendu de mer (`modern_ocean_surface.*`, `ModernOcean.h`) est actif par **région**. Une région définit :

- le niveau de la mer (y du `start-corner` de la carte d'océan native) ;
- la carte de côte native (cellules de 3 m, en-tête généré) ;
- la palette : eau claire, eau profonde, lointain, absorption par canal, teinte des reflets ;
- les bornes de caméra où le rendu s'active.

| Région | Niveaux | Niveau de mer | Masque | Palette |
|---|---|---|---|---|
| Spargus | `was*` | 9 m | `OceanCoastMask.h` (`wascity-ocean.gc`, origine −256 / −2762) | vert d'eau |
| Haven | `cty*` | 0 m | `OceanCoastMaskCity.h` (`*ocean-map-city*`, origine −864 / −1728) | bleu sombre |

Le choix se fait d'abord par les niveaux chargés (les deux cartes natives se recouvrent en coordonnées
monde), puis par la position de la caméra. Les effets propres à Spargus (vagues de bord de la plage,
lames sur les rochers, remplacement des sprites de vagues) ne s'appliquent qu'à Spargus.

## Ajouter une région

1. Générer son masque : copier `build_ocean_coast_mask_city.py`, pointer les tables `*ocean-*-<nom>*`
   de `ocean-tables.gc` (ou du fichier de niveau) et le `start-corner` de la carte.
2. Ajouter un `OceanRegion` dans `ModernOcean.h` (préfixe des niveaux, niveau, palette).
3. `python liquids-v3/build_engine.py` puis `python update_runtime.py`.

Les shaders lisent `ocean_level`, `ocean_shallow`, `ocean_deep`, `ocean_far`, `ocean_absorb`,
`ocean_reflection_tint` : aucune constante de région ne doit y rester.
