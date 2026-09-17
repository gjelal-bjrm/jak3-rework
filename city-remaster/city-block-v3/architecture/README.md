# Maisons de Spargus — première reconstruction avec ouvertures

Ce lot auteur reprend deux ensembles de maisons WCA, arbre TIE 1, prototype 0,
instances natives 1 et 2. Il importe leurs faces d'origine dans Blender, remodèle
les étages supérieurs, ouvre réellement cinq fenêtres et construit leurs tableaux,
appuis, petits balcons et volumes de toiture. Une toiture reçoit un dôme bas en
enduit ; l'autre conserve une terrasse. Les rehausses sont de 2,4 m et 0,9 m.

Les formes principales, soubassements, passages et portes restent reconnaissables.
Les couleurs, UV des parties conservées et palettes natives sont repris. Les
anciennes bordures du lot geometry-002 sur ces deux ensembles sont remplacées avec
des clés de faces exactes, sans toucher le reste de la ville.

## Intégration

- Base immuable : `environment/geometry-002/wascitya.fr3`, SHA256
  `7895a084e2ec26ccf7ff5ad220f884a089350e090e43e637f91435bb3d28f0f0`.
- Export exact : `block-native.json`, manifeste `block-selection.json`.
- Projet éditable : `spargus-houses-v3.blend`. Les deux modèles sont placés dans
  le repère monde Blender `(X, -Z, Y)` ; seuls leurs LOD0 sont affichés.
- Auteur : `author_buildings.py`, à lancer avec Blender en arrière-plan.
- Patch : `wascitya-patch.json`. `preserve_bvh=false` demande au bridge de
  recalculer les volumes de visibilité pour les parties rehaussées.
- Retrait de 4 608 faces et ajout de 28 404 faces, tous les quatre LOD inclus.
- Les pièces, meubles, occupants et vitrages sont intégrés par le lot intérieur
  séparé, sur les ancres exactes de `window-anchors.json`.

Les deux fenêtres basses de la maison 1 sont destinées aux intérieurs habités.
Elles se voient depuis une position piéton à `(2270, 19,75, 3)`, avec le regard
vers `(2277, 22,3, 10)`. Le sol visuel natif a été mesuré ; le déplacement et
l'observation avec une caméra jouable restent à confirmer dans le moteur.

La fenêtre basse de maison 2 initialement envisagée aurait remplacé des éléments
de portail et buté sur le terrain. Elle a été déplacée au-dessus du portail,
à Y=20,5 m, et reste une fenêtre secondaire sans occupant. Aucune barre ni porte
n'est retirée pour faire artificiellement de la place à une pièce.

## Vérification auteur

`validate_openings.py` lance de vrais rayons contre l'ensemble des triangles
natifs du bloc après application virtuelle des suppressions et ajouts. Les cinq
ouvertures sont testées sur une grille de neuf rayons dans chacun des quatre
LOD. Les contrôles incluent les anciens objets métalliques et panneaux opaques
séparés des murs. La preuve est dans `opening-validation.json` (24 contrôles).

`geometry-validation.json` confirme l'absence de triangles dégénérés après
conversion float32, de normales retournées ou non unitaires et de poids de
palettes invalides. Les aperçus Blender avant/après ont été inspectés par l'auteur.

Ce dossier n'installe rien. La validation d'import, la conservation des données
natives et la revue visuelle en jeu appartiennent au lot global `city-block-v3`.
Ce n'est pas une reconstruction terminée de tous les bâtiments de la ville.

## Stage v�rifi�

`staging.py` produit uniquement `staging/wascitya.fr3` et `candidate.json`.
L�audit natif strict `staging/preservation.json` passe ses 163 contr�les :
1 982 238 triangles non s�lectionn�s restent identiques, comme les collisions,
Merc, TFRAG, textures, matrices, palettes et BVH. Aucune r�gle de conservation
n�a �t� d�sactiv�e. Le parent du projet r�alise ensuite l�installation et
la revue native avec les int�rieurs s�par�s.
