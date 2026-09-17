# Premier essai de feu : palais de Spargus

## État

Premier rendu intégré aux 24 foyers du palais : flammes en volume, langues de feu ascendantes, braises fines, fumée légère, distorsion de chaleur et lumière locale. `Tester-FEU.cmd` ouvre cette scène avec les nouveaux effets d'eau.

Le premier essai a été refusé comme trop petit et trop timide. La hauteur, la largeur et la luminosité du cœur ont été augmentées. Après le retour sur les débordements, le départ des neuf feux sur pied a été calé sur le sommet des faces de charbon de chaque vasque ; une limite de rayon contient la base du feu dans l'ouverture. Les supports muraux et suspendus utilisent une ouverture conservatrice autour de leur acteur. Les conteneurs conservent leur géométrie et leurs textures d'origine, dont la petite bague ocre sous certaines coupes.

## Périmètre

Les flammes murales, suspendues et sur pied sont définies dans `data/goal_src/jak3/levels/wascity/palace/waspala-part.gc` : groupes `group-waspala-wallfire`, `group-waspala-hanging-fire`, `group-waspala-crucible-fire`, particules principales 2731, 2736 et 2739. Leurs positions originales sont enregistrées dans `palace-fire.json`.

Le rendu original superposait des particules utilisant `explosion-nebula`, des halos `glow-soft` et des braises `glow-hotdot`. Ces couches sont désactivées uniquement pour les groupes de feu du palais. Le niveau module déjà certains éclairages via `update-mood-flames` dans `waspal-mood.gc` ; un éclairage local supplémentaire suit le rythme des nouvelles flammes.

## Rendu intégré

- Un pied de flamme stable dans chaque brasero, plusieurs langues de feu dont la turbulence monte et se dissipe, avec des rythmes différents selon le foyer.
- Un cœur chaud, des extrémités orangées plus transparentes et des détails lisibles, sans grande masse uniformément blanche.
- Des braises fines et peu nombreuses, une fumée légère qui se disperse et une distorsion de chaleur localisée.
- Une lumière chaude irrégulière sur les surfaces proches et dans l'eau, avec une portée limitée.
- Respect des emplacements, supports, palette et ambiance du palais, avec une ampleur adaptée après les retours en jeu.

## Vérification

Les captures natives `fire-front-*`, `fire-close-*` et `fire-side-*` montrent le rendu intégré sous plusieurs angles. `fire-v1/before.png` conserve la référence avant remplacement. `fire-v1/validation.json` documente les contrôles du conditionnement, des sources et de l'animation. La passe de feu a coûté en moyenne 3,14 ms au GPU (maximum 3,54 ms, 12 mesures en 1600 × 900 dans cette vue). Ce n'est pas une mesure de fréquence d'images pour tout le jeu.

La texture partagée `explosion-nebula` reste intacte pour les autres effets du jeu. Le nouveau rendu se déclenche uniquement lorsque le palais est utilisé. L'éclairage teste la profondeur des objets visibles ; il ne remplace pas des ombres calculées pour toute la scène. Les reflets sur l'eau sont des reflets approchés de sources étendues, déformés par les normales de l'eau.

## Sources et reconstruction

`fire-v1/fit_sources.py` mesure les ouvertures à partir des triangles indexés du décor original. `fire-v1/prepare.py` produit les positions et installe les six shaders, puis désactive les dix anciennes couches de particules. Exécuter ensuite `liquids-v3/apply_materials.py`, compiler GOAL avec `(mi)` et le moteur avec `liquids-v3/build_engine.py`. Fermer le jeu, conditionner avec `liquids-v3/package.py`, relancer, puis vérifier avec `fire-v1/validate.py`. Repasser `prepare.py` après `apply_fountains.py`, qui restaure sa référence de particules.

La suite reste l'extension du feu aux autres zones et types de foyers du désert, puis le remaster des matériaux décrit dans `DIRECTION.md`.
