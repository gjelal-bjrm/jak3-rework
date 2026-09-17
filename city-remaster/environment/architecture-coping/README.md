# Façades continues et couronnements

Cette révision conserve les murs d'origine sans retailler leurs raccords.
Les nouveaux couronnements ont une épaisseur, des profils arrondis et une
usure légère, construits dans Blender depuis les véritables contours de toit.
Les UV et palettes natives restent la référence. Quatre niveaux de détail
sont exportés depuis leurs sources respectives.

Le chanfrein intérieur du premier candidat exposait des lignes sombres dans
le rendu natif malgré une orientation valide des triangles. Il est désactivé
ici. Le remodelage complet des volumes devra traiter ensemble les panneaux,
les raccords et leurs composants voisins.

Les scènes `*-architecture.blend` restent éditables. Les exports natifs sources
sont conservés dans `../architecture`. La validation indépendante porte sur
les triangles réellement exportés ; l'observation du jeu est documentée dans
`../geometry-002/native-review.json`.
