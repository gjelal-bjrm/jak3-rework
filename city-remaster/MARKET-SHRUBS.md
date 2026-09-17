# Buissons secs du marché — reconstruction complète

Lot auteur prêt pour intégration : **69 touffes, 2 280 feuilles individuelles,
214 320 triangles**. Les 2 622 triangles natifs sont retirés exactement par leurs
identifiants de flux. Aucun autre buisson ou matériau partagé n'est remplacé.

## Formes

Chaque feuille est un volume fermé à section fine nervurée, avec une courbe
longitudinale, une torsion légère et une vraie pointe. Trois étages irréguliers
produisent un cœur plus vertical, des feuilles intermédiaires arquées et des
pointes extérieures retombantes. Les 69 variantes sont déterministes.

Les matrices natives gardent orientation, échelle, inclinaison et emplacement
du pied. L'emprise horizontale maximale augmente de **2,1 %** ; aucune collision
n'est modifiée. Les couleurs et indices d'éclairage horaire viennent des faces
natives voisines, avec une modulation douce du creux et du relief des feuilles.

## Matière dédiée et UV

- Image auteur : `market-shrub-orange-hd.png`, 1254 × 1254, RGB.
- Export technique : `market-shrub-orange-hd.rgba`, RGBA8 brut, alpha **128**.
- Nom ajouté : `market-shrub-orange-v1`, page `remaster-market-plants`.
- Le patch ajoute cette texture via `new_textures` et référence son nom dans
  chaque face ajoutée. L'atlas natif `wascity-shrub-orange-01` reste intact.
- UV natives : **0…4096**, racine **V=4096**, pointe **V=0**. Un vent léger peut
  pondérer le déplacement par `1-clamp(V/4096,0,1)` pour garder le pied immobile.
- ImageGen a produit le tissu végétal à partir de la référence native 16 × 16.
  Le prompt et la provenance sont dans les fichiers `market-shrub-orange-hd-*`.
  L'export RGBA conserve les pixels RGB de l'image générée.

## Fichiers

- `author_shrubs.py` : auteur Blender reproductible.
- `market-shrubs.blend` : les 69 touffes dans leurs positions relatives natives,
  texture HD embarquée et attributs de provenance par objet.
- `market-shrubs-patch.json` : patch natif `remove/add` pour le bridge.
- `market-shrubs-report.json` : bornes et géométrie de chaque instance.
- `validate_shrubs.py` / `market-shrubs-validation.json` : contrôle indépendant.
- `market-shrubs-source-preview.png` et `market-shrub-{2467,2491,2596}-preview.png` :
  aperçus Blender, pas des captures du jeu.

Source attendue : WCB market-block004, SHA256
`76f371e111f304863501c3ed4ddcbcbf016383a6856d09591f2a640db608115f`,
36 575 263 octets, repris dans `source_fr3` du patch.

## Contrôles effectués

Les 69 sélections complètes correspondent aux faces natives. Les triangles
restent non dégénérés après conversion des positions au format float32 natif.
Les surfaces sont fermées, orientées vers l'extérieur et leurs arêtes sont
partagées exactement deux fois. Les UV, couleurs, poids et indices sont valides.
La texture dédiée a la taille attendue et un alpha constant de 128.

Aucun build, lancement du jeu ou déploiement effectué pour ce lot auteur.
Le rendu natif et le coût GPU restent à contrôler lors de l'intégration.
