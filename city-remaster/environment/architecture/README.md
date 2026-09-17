# Spargus — modèles de façades et fenêtres

Import des instances TIE originales dans Blender, puis reconstruction des
arêtes d'enduit et ajout de couronnements épais, légèrement usés. Les formes
générales, les couleurs et les raccords UV restent reconnaissables. Cette passe
travaille 155 modules WCA et 208 modules WCB, avec quatre niveaux de détail.
Ce sont des modules de construction, pas 363 bâtiments entiers indépendants.

Les 278 cadres de fenêtres sont suivis dans `windows/`. Les vitres séparées et
les ouvertures restent intactes ; aucun intérieur habité n'est encore ajouté.
Les portes mobiles, collisions, maisons hors familles sélectionnées et détails
de bois restent à traiter dans les passes suivantes.

## Fichiers d'auteur et import

- `export_selection.py` : export natif entier des instances portant les enduits.
- `author_facades.py` : import et édition Blender ; scènes `*-architecture.blend`.
- `*-patch.json` : géométrie, UV, normales et provenance des palettes natives.
- `independent_validate.py` : contrôle indépendant des véritables triangles
  exportés, de leur orientation et des attributs de couleur.
- `../geometry-001/build.py` : fusion avec fenêtres et végétation, audit natif
  avant/après et installation explicite du candidat complet.

Les premiers candidats n'ont pas été livrés : la projection UV globale après
dissolution des diagonales étirait les textures ; le recalcul automatique de
l'extérieur sur des coques ouvertes inversait certains murs. La méthode garde
maintenant les coutures UV, le sens des faces natives et traite les volumes
ajoutés séparément. Les petits coins concaves issus du chanfrein sont orientés
contre leur surface source. Chaque normale exportée correspond au triangle
réel arrondi dans les coordonnées du jeu.

Un aperçu Blender sert au contrôle de création. L'installation n'est validée
visuellement qu'après comparaison dans le jeu natif, à distance de jeu.
