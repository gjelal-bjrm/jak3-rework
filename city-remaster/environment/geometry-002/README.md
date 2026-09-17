# Spargus — géométrie urbaine, deuxième candidat natif

Cette passe combine les modèles Blender de fenêtres et de végétation avec des
couronnements arrondis ajoutés aux façades. Elle part de l'ancêtre ENV commun,
comme le lot 001, et remplace explicitement ce dernier après comparaison native.
Les empreintes de la version remplacée sont enregistrées ; les variantes de
comparaison restent protégées.

## Périmètre exact

- 278 encadrements de fenêtres : profils, appuis et fixations en volume. Les
  vitrages existants et leurs ouvertures restent conservés.
- 1 482 touffes : brins courbés en volume, répartis sur les emplacements natifs.
- 25 petits cactus fleuris : coussins arrondis, épines et pétales en volume.
  Les grands cactus arborescents restent à reconstruire.
- Les 155 modules WCA et 208 modules WCB de façades sélectionnés gardent leurs
  panneaux continus ; les contours de toiture admissibles reçoivent un rebord
  épais et arrondi. Ces nombres ne désignent pas des bâtiments entiers refaits.
- La flexion locale de l'herbe par Jak est le lot séparé `../../grass-contact`.
  Les 69 touffes du marché et les palmiers déjà acceptés restent conservés.

## Défaut refusé dans le candidat 001

Les contrôles de triangles et de palettes du lot 001 passaient, mais le jeu
montrait des bandes sombres le long de plusieurs angles après leur arrondi
vers l'intérieur. `city-facade-seam-diagnostic.png` documente ce défaut. Les
panneaux natifs sont ouverts et se raccordent à d'autres composants ; cette
technique ne convient pas à un remodelage partiel. Le lot 002 garde leur
continuité et ajoute les couronnements séparément. Les fichiers du candidat
001 et ses sources restent disponibles pour comparaison ; ils ne sont pas
présentés comme une validation visuelle réussie.

## Limites

Il s'agit d'une première passe de géométrie urbaine, pas du remodelage complet
des bâtiments. Les portes mobiles, grands cactus, intérieurs visibles et
éclairages de toute la ville restent à traiter. La capture du jeu et les
contrôles de conservation sont deux validations distinctes. Le rapport
`native-review.json` consigne les vues effectivement inspectées et leurs limites.
