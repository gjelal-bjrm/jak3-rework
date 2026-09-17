# Modèles Blender du palais — premier lot

Blender 5.2.2 LTS est utilisé en arrière-plan pour produire de véritables maillages, réimportés dans le niveau natif `waspala.fr3`.

## Contenu de ce lot

- 9 vasques de braseros sur pied : paroi et rebord reconstruits, ornements adaptés à la courbure. La surface de combustible qui ancre les flammes conserve exactement ses coordonnées. Les pieds gardent encore leur silhouette d'origine.
- 21 pots des palmiers : panse continue, épaulement arrondi et rebord en volume. La terre et les emplacements des plantes restent en place.
- Trône : arêtes du cadre retravaillées, coussin en volume et rivets arrondis. Motifs et proportions conservés.
- 46 troncs et 384 palmes : surfaces subdivisées et courbées. Le shader ajoute un mouvement léger aux palmes, fixé au point d'attache de leurs UV.
- Un rocher près du départ a servi au premier test d'import. Son fichier Blender est conservé, mais ce modèle est retiré du lot jouable : ses raccords de matière nécessitent encore une reprise.

Ce lot ne termine pas la salle entière. Les supports muraux et suspendus, les rochers, les buissons, les éléments architecturaux et les matériaux restant trop pauvres demandent encore du travail. L'ordre autorisé reste : salle complète, ville, arène, désert puis véhicules.

## Fichiers éditables

- `brazier-45101-remodel.blend` : vasque et ornements du brasero près des bassins.
- `planter-11-remodel.blend` : pot près des escaliers.
- `throne-remodel.blend` : cadre du trône.
- `throne-cushion-remodel.blend` : cadre et coussin, conservés comme objets séparés.
- `palm-frond-remodel.blend` : palme de référence.
- `palace-rock-test.blend` : rocher et référence originale masquée.

Les objets sont travaillés autour d'une origine locale pour éviter les erreurs de précision. Leur propriété `native_origin` indique leur position d'origine en mètres dans le jeu. Les scripts conservent les UV et les matériaux utilisés par le moteur.

## Reconstruction

1. `build_bridge.py` compile l'importeur C++ (ne pas le lancer en même temps que la compilation du jeu : ils partagent les bibliothèques du build).
2. `remodel_objects.py`, dans Blender, accepte `-- brazier`, `-- planter` et `-- throne`.
3. `remodel_foliage.py` et `remodel_rock.py` produisent les autres modèles.
4. `apply_models.py` combine les patches, refuse les remplacements qui se chevauchent, vérifie les faces de combustible et reconstruit un FR3 natif.
5. Le moteur vérifie la position des triangles d'origine avant leur remplacement. Le fichier source doit provenir d'une extraction propre, sans modèles déjà appliqués.
6. `terrain-v1/extract.py` réapplique désormais les modèles après une nouvelle extraction de textures. `liquids-v3/package.py` emballe ensuite le résultat dans le prototype.

Les patches conservent les groupes de visibilité, les matériaux et les huit palettes d'éclairage du jeu. Une marge de visibilité de 85 cm accompagne les nouvelles formes. Le format conserve sa limite de 8192 couleurs par arbre : à saturation, les nouveaux sommets utilisent la couleur de sommet source la plus proche. Les collisions d'origine restent utilisées ; elles n'ont pas été remodelées dans ce lot.

## Vérifications et retour arrière

`native-model-validation.json` contient les empreintes des fichiers réellement importés. `native-cameras.json` enregistre les angles reproductibles des comparaisons en jeu. Le premier lot est installé dans le prototype et a été contrôlé dans la salle du roi.

Les captures natives sont dans `../profiles/remaster-palace/OpenGOAL/jak3/screenshots/`, sous les noms `objects-before-*` et `objects-validated-*`. Les anciennes captures `objects-after-*`, `objects-final-*` et `objects-colour-*` documentent des étapes intermédiaires. Les images Blender servent au contrôle des modèles et ne remplacent pas ces captures du jeu.

`python models-v1/verify_package.py`, lancé depuis la racine du prototype, vérifie les empreintes des 30 fichiers déployés, le moteur et le retrait du rocher expérimental. Le résultat est enregistré dans `package-validation.json`. Les 22 fichiers de variante hors géométrie et shaders de matériaux restent identiques à la sauvegarde avant modèles, notamment les effets d'eau et de feu et les DGO. Les surfaces de combustible ont été vérifiées sur les quatre niveaux de détail.

Le contrôle visuel a porté sur les vasques, leurs ornements et le raccord aux flammes, le trône et les palmiers en pots. Le transfert des couleurs d'éclairage se fait désormais au sommet : cela corrige les plaques triangulaires qui apparaissaient sur le rebord des vasques. La caméra normale a été rétablie et le jeu reste ouvert. Les captures natives produisent un avertissement OpenGL déjà présent malgré des PNG valides ; aucun échec de compilation de shader ni assertion n'a été relevé. La fluidité globale et toutes les collisions de la salle n'ont pas encore fait l'objet d'un audit complet.

Le niveau sans ce lot se trouve dans `waspala-before-models.fr3`. Le prototype précédant les objets a été conservé dans `../variants/remaster-before-objects`, avec son moteur dans `runtime-before-objects.exe`.
