# Plantes complètes du marché WCB

Préparation native terminée : **2 palmiers entiers et 69 buissons**, soit
5 758 triangles tous LOD confondus. Aucun modèle n’a été remplacé dans le jeu.

L’absence des palmes dans le premier export provenait du flux de vent ignoré
par l’ancien bridge. Les feuilles et les barbes sont des instances `tie_wind`,
distinctes des troncs `tie`. Les couronnes se trouvent bien près du marché.
L’extension conserve ces deux espaces d’identifiants séparés.

## Correspondances

Tous les composants ci-dessous appartiennent à l’arbre 1 de `wascityb`.
Les troncs ont le prototype 16. Les indices de géométrie/LOD 0, 1, 2 et 3
sont exportés explicitement ; leurs matrices d’instance concordent.

| Tronc TIE | Palmes TIE_WIND | Barbes TIE_WIND | Centre géométrique XYZ, mètres | Rayon XZ |
| --- | --- | --- | --- | --- |
| 486 | 0, 4, 5 | 49, 50, 51, 52 | 1766,210 ; 47,234 ; −337,305 | 10,728 m |
| 487 | 1, 2, 3 | 45, 46, 47, 48 | 1770,444 ; 44,603 ; −331,811 | 10,900 m |

Chaque couronne comprend trois composants de palmes et quatre éléments de
barbe. Leur rattachement est déterminé par la distance entre leur point
d’attache natif et les triangles du tronc : au plus 0,780 m. Le second tronc
le plus proche est à au moins 3,712 m ; aucune association n’est ambiguë.

Les **69 buissons** utilisent `shrub`, arbre 0, prototype 9. Leurs identifiants
complets, coordonnées et rayons figurent individuellement dans
`market-plants-map.json`. Douze buissons n’étaient que partiellement compris
dans le bloc : l’export inclut désormais leurs 38 triangles complets, y compris
au-delà des bornes. Les rayons et boîtes englobantes utilisent uniquement les
sommets référencés par les triangles, jamais les sommets auxiliaires.

## Fichiers et contrôle

- `market-plants-selection.json` : sélection explicite des instances, sans découpe spatiale.
- `market-plants-native.json` : faces natives, UV, couleurs, matrices et paramètres du vent.
- `market-plants-map.json` : correspondances détaillées et identifiants complets de chaque LOD.
- `prepare_market_plants.py` : régénère les correspondances et l’export.
- `market-plants-validation.json` : comparaison indépendante avec le GLB original.

Les **6 240 triangles animés** de tous les palmiers WCB au LOD 0 correspondent
au GLB original, avec un écart maximal de position de 0,000069 m.
Les 35 contrôles du bridge passent également ; les trois anciens exports
palace restent identiques octet par octet.

Le bridge importe maintenant les couronnes dans des draws `tie_wind` natifs,
avec matrices, vent et visibilité conservés. Le contrat et l’audit sont dans
`WIND-PATCH.md`. Les convertir en faces `tie` ferait perdre leur espace d’indices
et leur comportement animé ; cette conversion n’est pas utilisée.

La sélection et l’export de référence ont été repinnés sur la base Merc
`market-block-004` : SHA256
`76f371e111f304863501c3ed4ddcbcbf016383a6856d09591f2a640db608115f`.
Les associations géométriques ci-dessus restent celles de l’inventaire initial.
