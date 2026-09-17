# Galerie native — six maisons, intérieurs et feux

Ouvrir `index.html`. La page fonctionne sans dépendance réseau. Elle présente treize comparaisons, avec les images entières : avant, après, curseur ou côte à côte. Elle ne déclare aucun résultat de validation native.

## Contrat des captures

Chaque nom ci-dessous attend exactement deux fichiers dans `images/`, suffixés `-before.png` et `-after.png` :

| Paire | Référence avant |
| --- | --- |
| `house1-overview` | geometry-002 |
| `house1-front` | geometry-002 |
| `house1-side` | geometry-002 |
| `house1-roof` | geometry-002 |
| `house2-front` | geometry-002 |
| `house2-roof` | geometry-002 |
| `house-east` | geometry-002 |
| `house-west` | geometry-002 |
| `house-low` | geometry-002 |
| `house-north` | geometry-002 |
| `interior-contact` | même pièce partagée, ombres de contact désactivées |
| `fire-wca` | ancien generic-obs sur la géométrie actuelle |
| `fire-wcb` | ancien generic-obs sur la géométrie actuelle |

Les dix paires de géométrie comparent geometry-002 au lot R4 avec les nouveaux intérieurs. Les textures et modifications précédentes sont déjà présentes dans geometry-002 : ce n’est pas le jeu PS2 original. La paire de contact conserve géométrie, mobilier et caméra ; seul l’effet d’ombres de contact change. Les deux paires de feu conservent la géométrie actuelle et le point de vue.

`window-correction`, `house2-overview` et les anciennes captures isolées `city-fire-*` ne font plus partie de la galerie. Leurs fichiers ne sont ni supprimés ni utilisés comme remplacement.

## Disponibilité et provenance

- Une paire n’affiche des images que lorsque ses deux fichiers exacts existent et sont des PNG lisibles par leur en-tête. Sinon, elle indique « Capture en attente » et précise le côté manquant.
- Les empreintes connues des six anciennes prises « après » R3 figurent dans `gallery-data.json`, sous `obsolete_capture_sha256`. Elles ne peuvent pas être présentées comme des prises du nouveau lot tant qu’elles ne sont pas remplacées. Aucun autre fichier n’est substitué.
- Les images sont référencées avec leur empreinte dans l’URL, pour éviter qu’un navigateur affiche une ancienne capture mise en cache après remplacement.
- Si les résolutions d’une paire diffèrent, le curseur superposé est désactivé ; les modes séparés et côte à côte restent disponibles.
- Le générateur ne crée, copie, renomme ni retouche aucune image. Le registre de provenance native appartient au flux de captures du parent et n’est pas modifié ici.
- La présence de deux fichiers n’atteste pas à elle seule leur cadrage, leur version en jeu ou la qualité du résultat. Une image fixe ne valide pas les animations.

Après chaque série de nouvelles captures, reconstruire puis actualiser la page :

```powershell
C:/Python313/python.exe city-remaster/city-block-v3/review-window-fix/build_gallery.py
```

Cette commande actualise `index.html` et `capture-index.json` : 26 fichiers attendus, disponibilité, dimensions, SHA-256 et référence de chaque paire. Les noms contractuels et le décompte des références sont vérifiés par le générateur.

## Portée décrite

Six maisons comportent neuf fenêtres donnant sur huit pièces, dont cinq sont habitées. Les deux fenêtres du même étage de la maison 1 montrent une seule pièce partagée : six fenêtres ont donc une vue sur une pièce habitée, mais il n’y a que cinq pièces habitées.

Les deux maisons pilotes ont reçu des modifications de volumes, de toiture et d’ornements. Les quatre autres maisons reçoivent des ouvertures et des encadrements, avec des pièces variées ; elles ne sont pas annoncées comme intégralement reconstruites. Le reste de la ville n’est pas déclaré terminé par cette galerie.

Le schéma des six repères utilise les centres des ouvertures, avec la même échelle en X et Z. Ce n’est ni une capture du jeu ni un plan des rues.

`gallery-data.json` conserve les légendes, le protocole des trois références et les coordonnées. Le dossier `baseline/`, les fichiers image et les registres de capture restent sous la responsabilité du flux de captures du parent.
