# Révision des ornements de la maison 2

Révision incrémentale du FR3 installé `a1ee034f…71e9ec`. Les dossiers et preuves
de la première reconstruction restent intacts. Ce dossier n'installe rien.

## Diagnostic

La capture native `city-house2-native-v3.png` montrait un motif ancien en V
tronqué par une nouvelle fenêtre, et plusieurs ornements donnant une impression
de filigranes. Les rendus comparatifs `geometry002-ornaments.png` et
`installed-ornaments.png` confirment que les V très minces existaient déjà dans
la base geometry-002. Le motif tronqué était, lui, une conséquence du découpage
rectangulaire de l'ancien ornement lors de l'ouverture de la fenêtre.

Sur demande, cette maison reçoit sept plaques métalliques fermées. Elles gardent
la silhouette pointue de Spargus et la texture bronze native ; leur volume
fermé, leurs biseaux et leur arête centrale prennent la lumière. Les deux
ornements immédiatement voisins sont remplacés ensemble pour ne pas conserver
une paire avec un seul ancien filigrane. Le motif coupé par la fenêtre et les
petits restes associés sont retirés entièrement.

## Périmètre natif

- TIE arbre 0 uniquement, quatre LOD.
- Remplacement draw 40, groupes 4/5/6/7/9 ; en LOD3 le draw est 38.
- Suppression entière draw 40 groupe 10 et draw 41 groupes 4/5/6 ; en LOD3,
  les draws sont 38 et 39.
- Les groupes 6 et 9 contiennent chacun deux objets : les composantes connexes
  sont identifiées indépendamment avant reconstruction.
- 862 triangles supprimés, 3 612 ajoutés.
- Aucune façade, fenêtre, pièce, ancre d'intérieur, texture ou collision déplacée.

## Preuves

- `ornament-validation.json` : sept composantes fermées dans chaque LOD,
  toutes les arêtes reliées à exactement deux faces, volumes positifs,
  aucun sommet enfoui dans les murs. Garde minimale mesurée : environ 3 mm.
- `geometry-validation.json` : géométrie float32, normales et poids de palettes.
- `bvh-coverage.json` : chaque nouveau sommet est couvert par les sphères
  natives existantes. Les BVH sont conservés octet pour octet.
- `opening-validation.json` : les cinq fenêtres restent dégagées sur neuf
  rayons dans chacun des quatre LOD. Les ancres du parent sont inchangées.
- `staging/preservation.json` : 163 contrôles réussis et 2 009 780 triangles
  non sélectionnés identiques ; conservation stricte des autres sections.
- `revised-ornaments.png` : rendu Blender final inspecté.

`house2-metal-ornaments.blend` contient les sept formes éditables dans le repère
monde, avec les quatre LOD. `author.py` génère le patch ; `staging.py` crée
uniquement le FR3 de stage. Le candidat est `candidate.json`. L'installation et
la validation visuelle native sont à réaliser par le parent du lot global.
