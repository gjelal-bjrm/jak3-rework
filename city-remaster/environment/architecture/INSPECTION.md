# Architecture WCA/WCB — sélection native

## Résultat utile pour la reconstruction

Les grandes façades blanches de la vue `city-architecture-before-v1.png` sont
principalement des **instances TIE statiques**. En LOD0, les matériaux stucco
représentent 9 034 triangles TIE dans WCA, 11 196 dans WCB ; TFRAG en contient
respectivement 0 et 274. Le premier lot peut donc employer le chemin TIE déjà
audité sans attendre une extension TFRAG.

Les exports `wascitya-native.json` et `wascityb-native.json` sont fondés sur les
FR3 ENV installés (hashes complets dans `inventory.json`) ; aucun indice d’un
ancien FR3 n’est réutilisé. Chaque instance portant du stucco en LOD0 est exportée
entière, tous matériaux et tous LOD. Aucune sélection spatiale ne coupe le bâtiment.

| Niveau | Instances | Triangles LOD0/1/2/3 |
|---|---:|---|
| WCA | 207 | 9 686 / 9 686 / 9 686 / 5 296 |
| WCB | 270 | 12 000 / 12 000 / 12 000 / 7 518 |

Les origines et matrices d’une même instance sont identiques sur les quatre LOD.
Les bornes proviennent seulement des triangles dessinés. La qualification
`major_house_candidate` est un filtre dimensionnel, pas une identification
artistique : elle inclut certains grands murs isolés et étages empilés.

## Modules à traiter en premier

Coordonnées monde en mètres ; clé complète = niveau / TIE / LOD / arbre / instance.

| Niveau | Arbre / prototype / instance | Origine XYZ | Faces LOD0 | Lecture du module |
|---|---|---|---:|---|
| WCA | 0 / 39 / 2894 | 2189,48 ; 19,61 ; −18,83 | 112 | Grande coque, ~13 × 32 × 42 m |
| WCA | 0 / 39 / 2895 | 2185,78 ; 17,36 ; −96,60 | 112 | Même famille, autre façade de rue |
| WCA | 1 / 0 / 1 | 2286,66 ; 18,82 ; 13,58 | 134 | Coque, bande de briques et découpes |
| WCA | 1 / 0 / 2 | 2344,61 ; 9,39 ; −17,90 | 134 | Même famille près du centre |
| WCA | 0 / 14 / 2073 | 2286,35 ; 23,24 ; −147,73 | 216 | Plus riche en bordures/retours natifs |
| WCB | 0 / 15 / 1615 | 1813,78 ; 48,91 ; −234,29 | 134 | Famille analogue WCA arbre1/proto0 |
| WCB | 0 / 15 / 1617 | 1868,31 ; 26,67 ; −346,40 | 134 | Façade au-dessus du marché |
| WCB | 0 / 43 / 2471 | 1839,78 ; 26,42 ; −407,24 | 146 | Coque avec découpe et soubassement |
| WCB | 0 / 43 / 2472 | 1656,84 ; 26,41 ; −324,75 | 146 | Même famille côté littoral |
| WCB | 1 / 27 / 702 | 1692,49 ; 72,07 ; −290,75 | 176 | Grande masse haute, ~22 × 45 × 22 m |

Les draws sont partagés entre plusieurs instances : par exemple WCA arbre0/
proto39 utilise draws13/15. **Ne jamais remplacer un draw entier** pour traiter
un bâtiment. Utiliser les clés `draw/stream_index`, `instance` et
`original_positions` des faces exportées.

## Modifications qui changent réellement la lecture

- Arrondir les coins et retours de plâtre depuis leurs profils natifs, avec des
  chanfreins orientés vers l’intérieur de l’enveloppe pour conserver les passages.
- Construire une couronne supérieure et des retours épais à partir des bords
  existants, sans déplacer la ligne de toiture ni les poutres déjà implantées.
- Donner une vraie épaisseur aux bandes de plâtre/brèches, avec surfaces de
  transition vers la brique ; conserver la répartition actuelle des matériaux.
- Ajouter des embrasures autour des ouvertures uniquement après association
  avec leurs pièces voisines. La coque complète d’une instance n’inclut pas
  forcément la fenêtre ou porte, qui peut être une instance distincte.

`protected-details.json` repère ces instances voisines à texture de porte/vitre,
avec leurs bornes et les bâtiments proches. Ce sont des pièces statiques, pas
des portes mobiles déduites de leur texture. Les vrais acteurs mobiles WCA sont
également listés : airlock (2265,65 ; 30,19 ; 131,22), porte arène
(2325,93 ; 58,40 ; −340,96), porte ascenseur (1990,97 ; 41,43 ; −439,65),
ascenseur palais (1989,38 ; 242,86 ; −461,18). WCB n’a pas d’acteur de ce type
dans l’inventaire. Les collisions restent natives : tout ajout saillant doit
rester hors de leurs couloirs et volumes animés.

## Chemin d’import

Le bridge existant accepte TIE + `remove/add`, normales monde, UV et couleurs
interpolées sur les huit palettes horaires. Conserver chaque groupe de visibilité,
les matrices/ancres, et `preserve_bvh: true` en restant dans les volumes natifs.
Réutiliser les textures ENV déjà améliorées et les UV natifs évite de changer la
palette. Les LOD3 possèdent moins de faces : les régénérer depuis leur propre export.

Un patch d’addition seul est ignoré si aucune face n’est retirée dans l’arbre ;
prévoir un remplacement explicite du support. Le chemin TFRAG sait remplacer des
faces mais ne sait pas encore ajouter une texture dédiée ; son audit historique
exigeait l’identité de l’arbre entier. Il n’est pas nécessaire pour ce premier lot.

Ces repérages ne sont pas une validation de collisions ou de rendu du futur modèle.
Les exports et l’inventaire n’ont modifié aucun fichier de jeu.
