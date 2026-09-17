# Spargus — marché et première passe d'ensemble

Consigne artistique générale : chaque composant refait doit devenir visiblement plus beau et mieux construit ; refaire la même forme ou ajouter seulement des polygones ne suffit pas. Garder l'identité animée, les teintes locales et les caractéristiques reconnaissables de Jak 3. Cette règle s'applique à tout le remaster.

## Lot auteur

- Étal : planches individuelles, rebords et casiers amovibles, vrais assemblages, pieds évasés/galbés, contreventements et ligatures. `author_stand.py`, `market-stand.blend`, `cty-fruit-stand-lod0.glb`.
- Auvent : toile galbée, épaisseur, ourlets, coutures, franges, cordages et anneaux ; deux niveaux de détail, squelette natif de 11 articulations conservé. Voir `AWNING.md`.
- Accessoires : caisse construite de planches, jarre creuse arrondie entourée de cordes, panier tressé contenant des grains, sac ouvert plissé et sac fermé ligaturé. `author_accessories.py` et cinq contrôles `market-*`.
- Matériaux HD : bois olive-brun fidèle, argile orange, toile, cordes et grain. Les textures sont embarquées dans les GLB, car les remplacements Merc ne prennent pas automatiquement les PNG du pack de textures.

Le lot `market-block-004` est installé dans WCA/WCB. Les captures natives `market-remaster-front-v2-stable.png`, `market-fruit-contact-side-v2.png` et `market-remaster-wide-v2.png` montrent les huit contrôles reconstruits. La seconde passe utilise 15 planches plus larges et un bois plus doux sur l'étal, des sacs asymétriques avec de grands plis, et des recouvrements/coutures sur les deux faces des auvents. Les aperçus Blender restent des contrôles de création distincts du rendu en jeu.

## Fruits en volume

`MarketFruit.h` remplace uniquement les particules `fruit1` de Spargus par une petite géométrie solide avec forme légèrement irrégulière, pédoncule, grain et éclairage. Les coordonnées, dimensions, rotations, teintes de famille et durées viennent toujours des particules GOAL ; le contrôleur de l'étal garde ses chutes et rebonds. Aucun fruit statique supplémentaire n'est posé sur les particules d'origine.

Le nom de texture a deux formes natives : `fruit1` et l'alias concaténé `waswide-spritefruit1`. Le rendu conserve les sources non sélectionnées dans leurs passes natives, puis restaure l'état OpenGL. Une erreur de shader conserve les images d'origine. Deux nouveaux shaders sont enregistrés par `apply_shaders.py` ; ils sont inutilisés par les moteurs officiels des variantes de comparaison.

Les captures `market-fruit-release-v2-0..6.png` montrent les volumes, leur libération, leurs rebonds et leur disparition par couverture progressive des pixels. Le test active le mode du contrôleur déclenché par une attaque ; il ne constitue pas un test de toutes les attaques au clavier/manette. L'éclairage et le grain V3 sont installés. Le shader ne promet pas des ombres portées complètes entre chaque fruit.

`apply_fruit_contact.py` ajuste les hauteurs des couches de fruits et le rayon de sonde au sol à leurs dimensions en volume. `omega`, également utilisé pour l'impulsion, reste inchangé. Seul `ctymark-obs` change dans WWD : les 65 autres occurrences d'objets sont identiques, y compris les noms de textures répétés. `register_fruit_contact.py` conserve la version d'origine et enregistre le DGO avec les variantes.

Le test natif `market-awning-bounce-v2-0..8.png` montre Jak au contact puis en rebond (Y de 34,62 à 45,77 m, état `target-jump`). Les attaches restent en place sur les vues contrôlées. Les tests d'auteur vérifient séparément les poids, matrices et articulations des deux niveaux de détail.

L'export Blender des auvents produisait un `COLOR_0` blanc et les vraies teintes dans `COLOR_1`. L'export impose maintenant la couche nommée `COLOR_0`, sans couche supplémentaire, pour que les teintes des creux soient effectivement lues par Merc. Les sacs avaient déjà le bon canal. L'étal emploie aussi ce réglage explicite.

## Import et conservation

`import_market.py` valide les GLB et leurs véritables sommets indexés. Par défaut il n'extrait rien ; `--apply` produit un staging isolé. Il vérifie les articulations dans le bon ordre, les matrices, les types de poids et la structure des matériaux. L'auvent LOD1 utilise explicitement le squelette LOD0 et ses cinq articulations natives autorisées.

`compare_market.py` compare tous les pixels et indices des textures existantes, les modèles Merc non sélectionnés et les blocs statiques. Les candidats doivent conserver exactement le TFRAG, le TIE, le vent, les buissons et les collisions de la ville courante, puis ajouter uniquement les objets sélectionnés. Les paramètres natifs Merc utilisés par le moteur sont conservés.

`deploy_market.py` contrôle ce rapport, les empreintes des GLB, celles des candidats et la version actuelle de chaque niveau avant d'installer WCA/WCB. Il sauvegarde les anciens fichiers, conserve les variantes original/V1, et enregistre `installed.json`. Les copies atomiques évitent de modifier une autre variante par un éventuel lien physique.

Le palais, ses vitres, l'eau, le feu et les routes GOAL restent protégés. Le vérificateur a réussi 272 contrôles sur 45 fichiers par variante après conditionnement et lancement. Les tests utilisent `OPENGOAL_TEST_MUTE=1`, confirmé par le journal du callback audio. Le journal conserve un avertissement OpenGL de capture déjà présent ; les PNG sont produits correctement.

Le staging `market-block-003` a été refusé par une hypothèse trop stricte du contrôleur, qui exigeait une texture ajoutée même lors d'une passe de géométrie réutilisant les images HD. Le lot 004 corrige cette condition ; l'égalité des pixels existants et des données de chaque dessin reste exigée. Aucun candidat refusé n'a été installé.

## Suite autorisée

Les supports fixes sont intégrés : 14 poteaux, 14 bras et 28 liaisons. Les deux
palmiers du marché et 69 touffes ont été reconstruits en entier. Les 13 instances
de palmiers restantes de WCB ont ensuite reçu leurs nouveaux troncs et couronnes,
avec quatre niveaux de détail et leur animation native par le vent. Voir
`environment/foliage/README.md`.

La priorité suivante donnée par l'utilisateur est une transformation visible
des grandes surfaces de la ville, avant les petites finitions. Le lot
`environment/staging/city-environment-001` intègre 22 matières HD dans WCA, WCB
et WASWIDE : sols et raccords, enduits, soubassements, rochers côtiers, falaises
rouges, toitures et métaux d'enceinte. Il modifie 78 entrées de textures et garde
les données géométriques et Merc intactes. Les matières ont une réponse à
l'éclairage régionale ; les bâtiments n'ont pas encore été remodelés par ce lot.
Le ciel est suivi séparément dans `SKY.md`.

Les captures natives `city-panorama-before-v1.png` et
`city-panorama-after-v1.png` emploient la même caméra. La première itération de
nuages y est rejetée pour ses aplats ; la V2 demande une nouvelle capture.
Le test de WCA a également identifié le débordement de l'ancien plan de mer
procédural sur les rues. Le masque côtier natif de 3 m est maintenant appliqué
au rendu de la mer et au traitement sous-marin : `city-center-dry-v2.png`
montre la rue sèche ; `city-coast-mask-swim-v2.png` confirme la mer et le véritable
état de nage conservés. `city-panorama-after-v2.png` montre la deuxième passe de
nuages. Voir `environment/native-review.json` pour les captures et leurs limites.

Continuer ensuite les rues, façades, portes mobiles et fenêtres, puis l'ensemble de Spargus, l'arène, le désert et les véhicules. Réutiliser le feu accepté du palais dans les autres cartes, avec les ancrages et activations propres à chaque source. Les 66 placements urbains recensés ne sont pas encore tous modernisés. Voir `INVENTORY.md` et `../desert-remaster/DIRECTION.md`.

## Géométrie urbaine et végétation — septembre 2026

Le lot `environment/geometry-002` réunit 278 cadres de fenêtres, 1 482 touffes,
25 petits cactus fleuris et de nouveaux couronnements de façades. Les scènes
Blender sont conservées dans `environment/architecture-coping`,
`environment/architecture/windows` et `environment/vegetation-v2`. Les grands
cactus arborescents, les portes mobiles et le remodelage complet des maisons
restent à traiter. Les vitrages existants gardent leurs ouvertures ; les
intérieurs habités ne sont pas encore réalisés.

La comparaison native du premier candidat a révélé des bandes sombres aux
angles retaillés des murs. Ce candidat est remplacé par une construction qui
garde les panneaux continus et ajoute les couronnements séparément. Les
rapports techniques seuls ne valent pas validation visuelle : les captures
inspectées sont répertoriées dans `environment/geometry-002/native-review.json`.

La règle « végétation réactive » est inscrite dans la direction du remaster.
`grass-contact` transmet le contact au sol de Jak aux touffes de Spargus :
racines fixes, flexion locale limitée, puis retour progressif au vent seul.
Le test GPU du shader empaqueté valide ces propriétés ; les limites des essais
natifs et l'absence actuelle de contact des PNJ sont indiquées dans
`grass-contact/NATIVE-QA.md`.
