# Spargus : ressources vérifiées et premier bloc à reconstruire

Préparation du 16 septembre 2026. **Aucun modèle ni texture de ville n'est installé par cet inventaire.** Le palais V2 et les derniers correctifs d'eau/feu restent indépendants. Le mandat couvre ensuite toute la ville, ses bâtiments et portes mobiles, le marché et les fruits, les matériaux, la végétation complète, les reliefs et la reprise du feu dans toutes les cartes.

## 1. Périmètre réel des fichiers

| Niveau natif | DGO / définition | Acteurs source | Rôle vérifié |
|---|---|---:|---|
| `wascitya.fr3` | `WCA.DGO`, `engine-src/goal_src/jak3/dgos/wca.gd` | 299 | Rues orientales, accès arène, ascenseur du palais, portes, accessoires |
| `wascityb.fr3` | `WCB.DGO`, `.../wcb.gd` | 346 | Côte et sept étals de fruits, marché, végétation, maisons |
| `waswide.fr3` | `WWD.DGO`, `.../wwd.gd` | 2 | Code partagé, habitants, cactus, auvents A, ventilateurs, moulin, signal de feu du palais |
| `wasdoors.fr3` | `WSD.DGO`, `.../wsd.gd` | 19 | Grand sas vers le désert, petit sas, stationnement, quatre lampes |

Les sources non modifiées sont dans `C:/Users/Gjelal/Documents/OpenGoal/active/jak3/data/decompiler_out/jak3/`, sous `levels/`, `entities/` et `textures/`. Le prototype déployé est dans `../data/out/jak3/fr3/`. `inventory.json` contient les chemins absolus et empreintes des sources, les noms et articulations des GLB, les acteurs avec AID/position/quaternion/masque d'activation, les textures et les groupes natifs.

**516 emplacements de textures, 362 images de pixels distinctes** dans les pages de ces quatre niveaux. Les duplications sont regroupées par pixels. Les noms de modèles partagés entre WCA/WCB/WSD sont aussi enregistrés ; leurs fichiers GLB exportés n'ont pas nécessairement la même empreinte, même lorsque le contrôle et le nombre de triangles sont identiques. Conserver un modèle auteur partagé et contrôler chaque niveau qui le charge.

## 2. Premier bloc : les sept étals de WCB

Sélection concrète : **X = 1 735–1 820 m, Z = −355 à −290 m**, niveau `wascityb`, partagé avec `waswide`. Le sol se trouve autour de Y = 28–33 m. Cette place réunit les étals, leurs toiles, les caisses, paniers et sacs, le sol, les murets, du bois et la végétation immédiate. C'est un ensemble lisible à distance de jeu, avant d'étendre aux façades des rues voisines.

Les 53 acteurs de cette emprise comprennent : **7 étals, 7 auvents B, 10 caisses, 13 paniers, 8 sacs**, quatre dogats, deux chickalopes, un objet `skill` et une scène. Les éléments de jeu ne sont pas des objets à supprimer. La liste complète figure dans `first_block.actors` du JSON.

| AID étal | Position X/Y/Z (m) | Auvent associé |
|---:|---|---:|
| 42090 | 1745.179 / 29.633 / −332.267 | 41242 |
| 42091 | 1759.816 / 30.225 / −328.562 | 41247 |
| 42092 | 1749.972 / 31.343 / −312.757 | 41241 |
| 42093 | 1765.816 / 32.214 / −304.694 | 41243 |
| 42094 | 1776.916 / 30.931 / −313.957 | 41244 |
| 42095 | 1789.900 / 28.236 / −343.949 | 41245 |
| 42096 | 1808.030 / 29.699 / −337.950 | 41246 |

Premier objet auteur : **étal AID 42091**, `levels/wascityb/cty-fruit-stand-lod0.glb`. Position de caméra proposée (à vérifier en direct) : (1768, 34, −347) m. Le type GOAL est `wascity-fruit-stand`, dérivé du système `fruit-stand` de `engine-src/goal_src/jak3/levels/wascity/ctymark-obs.gc`.

### Modèles mobiles de cette place

| Contrôle / fichier GLB | Triangles source LOD0 | Articulations exportées | Reconstruction ciblée |
|---|---:|---:|---|
| `cty-fruit-stand-lod0` | 78 | 4 | Plateau épais, assemblages de bois, pieds travaillés, rebords et casiers ; garder le squelette et le comportement de l'étal |
| `wascity-awning-b-lod0` | 40 | 11 | Toile avec courbure, épaisseur de bord, coutures et franges ; conserver l'animation du tissu |
| `market-basket-a-lod0` | 132 | 3 | Volume de terre cuite et maillage/cordage lisible |
| `market-basket-b-lod0` | 128 | 3 | Tressage en volume, rebord, contenu de riz plus détaillé |
| `market-crate-lod0` | 132 | 3 | Planches séparées, chanfreins, traverses, assemblages |
| `market-sack-a-lod0` | 144 | 3 | Couture, plis et fermeture cohérents |
| `market-sack-b-lod0` | 192 | 3 | Corps du sac et ligature réellement en volume |

`wascity-awning-b-lod1.glb` ne compte que 8 triangles. Prévoir son remplacement en même temps que LOD0 pour éviter le retour abrupt à l'ancien auvent. **L'auvent B est un `bouncer`**, défini dans `waswide-obs.gc:728` avec `tarp-bounce` et `bounce-whoosh` : conserver aussi le rebond de Jak, sa collision et la déformation associée. Les modèles de marché existent également dans WCA ; leur changement sera partagé lors de l'extraction.

**Les fruits ne font pas partie des 78 triangles de l'étal.** `ctymark-obs.gc` utilise `group-ctywide-fruit`, la texture `fruit1` de `waswide-sprite`, `fruit-sparticle-next-on-mode-1` et `fruit-check-ground-bounce`. Une nouvelle géométrie d'étal seule laisserait les anciens fruits. Pour de vrais fruits en volume, reprendre leur affichage à partir des positions de particules conservées par `fruit-stand`, et préserver leur chute, rebond et disparition. Ne pas poser des fruits statiques permanents au-dessus des anciennes particules.

### Sol, murets et végétation dans l'emprise

Les triangles du GLB de fond qui croisent l'emprise utilisent réellement :

- `wascity-ground-01`, `wascity-cement-road` ;
- `wascity-ditch-wall-top-to-ground`, `...-edging`, `wascity-ground-2-ditch-03/04/05` ;
- `wascity-rock-small`, `wascity-ground2ocean-shore-rocks` ;
- `wascity-wood-plain`, `wascity-metal-dirty`, `city-port-bigpipe-ring-side` ;
- `wascity-palm-trunk`, `wascity-shrub-orange-01`.

Les palmes complètes nécessitent aussi `wascity-palm-leaf-worn` et `wascity-palm-beard`, au lieu de reprendre seulement les troncs. Le cactus **AID 41968**, (1805.043, 35.125, −284.342) m, est juste au nord du bloc et constitue le premier objet de végétation mobile voisin. Son modèle partagé `levels/waswide/wascity-cactus-lod0.glb` compte 650 triangles et 8 articulations ; LOD1/LOD2 comptent 355/256 triangles. Son état détruit est un autre contrôle, `wascity-cactus-explode-lod0` (378 triangles). Reconstruire branches, base, fleurs et débris ensemble.

### Textures précises à travailler

| Texture | Page(s) vérifiée(s) | Taille source | Particularité |
|---|---|---|---|
| `city-slum-wood-plain` | `wascityb-vis-tfrag` | 64 × 32 | Bois de l'étal animé |
| `wascity-wood-plain` | WCA/WCB `-vis-tfrag` | 64 × 32 | Bois du décor fixe |
| `city-mark-wood-plain` | WCA/WCB `-vis-pris` | 128 × 64 | Caisses |
| `city-mark-basket2` | WCA/WCB `-vis-pris` | 64 × 64 | Panier B |
| `city-mark-cotton-wrap`, `city-mark-cotton-32x32` | WCA/WCB `-vis-pris` | 32 × 32 | Sacs |
| `city-mark-rope-01` | WCA/WCB `-vis-pris` | 64 × 32 | Ligatures |
| `wascity-awning-b` | `wascityb-vis-shrub` | 64 × 64 | Alpha 0–128 à conserver |
| `wascity-ground-01` | WCA/WCB/WSD `-vis-tfrag`, `waswide-vis-shrub` | 128 × 128 | Texture partagée ; conserver la palette |
| `wascity-shrub-orange-01` | WCA/WCB/WSD `-vis-shrub` | 16 × 16 | Géométrie végétale complète nécessaire |
| `wascity-palm-trunk` | `wascityb-vis-tfrag` | 64 × 128 | À traiter avec feuilles et barbe |
| `wascity-palm-leaf-worn` | `wascityb-vis-tfrag` | 64 × 128 | Alpha 0–126 |
| `wascity-palm-beard` | `wascityb-vis-tfrag` | 64 × 64 | Alpha 0–128 |
| `wascity-cactus-tall` | `waswide-vis-shrub` | 64 × 128 | Cactus partagé |
| `wascity-cactus-flower` | WCA/WCB/WWD `-vis-shrub` | 16 × 16 | Fleurs et état détruit |
| `fruit1` | `waswide-sprite` | 64 × 64 | Ancien affichage des fruits en particules |

Les valeurs alpha 128 correspondent à la convention du moteur PS2 ; ne pas les convertir aveuglément en semi-transparence standard. Les nouvelles textures doivent respecter l'organisation UV, les grandes formes et la couleur source. Cible initiale proposée : 1 024 px pour les matériaux proches, conservant le ratio 2:1 lorsque pertinent ; le volume, les normales et l'éclairage doivent produire l'amélioration visible.

## 3. Import natif : deux voies distinctes

### Décor fixe TFRAG / TIE / Shrub

`../engine-src/tools/palace_mesh_bridge.cpp` sait déjà appliquer des triangles aux trois familles, avec groupes de visibilité, couleurs et positions source. **Son export reste filtré pour le palais** : préfixes `waspala-*`, prototypes 5/11/14/18/23–28 et deux textures de buissons. Il faut remplacer ces filtres par une sélection explicite avant un export complet de ville.

Entrée préparée : **`first-block-selection.json`**. Elle contient le niveau, le FR3 et son empreinte, les bornes XZ, les matériaux et les types d'arbre. Son format est une proposition pour l'extension du pont, pas encore une commande existante. Exporter tous les LODs ; sélectionner les triangles entiers croisant l'emprise, sans les couper. Conserver les champs `tree_type/geom/tree/draw/group/stream_index/proto/instance/material/page/vertices` afin que le réimport vérifie les positions contre le même FR3 source.

Repères réels de WCB, **géométrie 0, TIE arbre 1** : prototype 16 = tronc de palmier ; 19 = bois et métal ; 20 = bois ; 21 = grand anneau de tuyau ; 22–24 = route. Les prototypes sont réutilisés entre arbres : **un numéro de prototype seul n'identifie pas un modèle**. Par exemple arbre 0/prototype 16 désigne un tube métallique, pas le palmier de l'arbre 1.

Les exports diagnostiques `wascitya-native.json` et `wascityb-native.json` fournissent l'inventaire des dessins à textures positives, mais leurs champs `faces` restent partiels à cause des filtres du palais. Ils ne sont pas une base de remplacement exhaustive. Le récapitulatif du JSON conserve les identifiants complets et les empreintes des FR3 correspondants.

### Acteurs articulés Merc

La voie existe dans le moteur : `decompiler/level_extractor/extract_level.cpp`, `extract_merc.cpp` et `merc_replacement.cpp` chargent **`custom_assets/jak3/merc_replacements/<nom-du-contrôle>.glb`**. Pour le projet testé, le chemin est `../data/custom_assets/jak3/merc_replacements/cty-fruit-stand-lod0.glb`, puis les autres contrôles du tableau. Les GLB exportés possèdent déjà `JOINTS_0`, `WEIGHTS_0`, squelette et animation.

Par défaut, les poids et indices d'articulation sont repris sur les anciens sommets proches. L'option de nœud GLTF `enable_custom_weights` active les poids auteurs : garder le même ordre d'articulations et vérifier les mouvements avant de l'utiliser. Cette voie remplace l'affichage, pas les états GOAL, les collisions, les effets de destruction ou les animations de gameplay. Garder les pivots, le gabarit des passages et les articulations des éléments mobiles.

`../terrain-v1/extract.py` relance actuellement l'extraction puis **réapplique uniquement les modèles du palais**. Avant de déployer des modèles de ville, ajouter un manifeste de lots par niveau et leur réapplication après extraction ; sinon une texture suivante effacera les nouveaux décors fixes. La voie Merc utilise les fichiers de remplacement à chaque extraction. Ne pas compiler le pont et le moteur simultanément.

## 4. Portes et rues suivantes

| Acteur | AID / position (m) | Contrôle à préserver |
|---|---|---|
| Petit sas WCA | 37579 — (2265.652, 30.190, 131.218) | `wascity-airlock-small-lod0`, 7 articulations |
| Porte d'arène | 41661 — (2325.931, 58.397, −340.957) | `wascity-stad-door-lod0`, 130 triangles / 3 articulations |
| Porte d'ascenseur | 41660 — (1990.968, 41.427, −439.653) | `wascity-elevator-door-lod0/1/2`, 477/250/117 triangles |

`wasall-obs.gc` et `wascitya-obs.gc` dérivent ces objets de `com-airlock` (`engine/common-obs/airlock.gc`). Le petit sas conserve trois maillages de collision associés aux indices de transformation **6, 7 et 3** ; le grand sas utilise **4 et 5** ; la porte d'arène et la porte d'ascenseur utilisent **3**. Les portes doivent donc rester des acteurs articulés, avec leurs états d'ouverture/fermeture et transitions de chargement. Une façade statique peut recevoir un nouvel encadrement, mais ne doit pas remplacer la partie mobile.

Les surfaces de bâtiments recensées incluent `wascity-stucco-wall-bleached-01`, ses variantes de briques/coupes/bords, `wascitya-stone-top/bottom`, `wascity-stonewall-bricks`, `wascity-metal-door-01`, `wascity-roof-1`. Les fenêtres `wascity-window-glass-01` se trouvent dans les pages WCA/WCB `-vis-water`, **8 × 32 px, alpha 8–110**. Conserver leur véritable transparence et l'extérieur visible, conformément au besoin de météo future ; ne pas leur appliquer un shader de mer parce que la page porte le suffixe `water`.

## 5. Étendre le feu accepté à toutes les cartes

Le système actuel ne peut pas encore être déclaré universel : `PalaceFire.h` exige `waspala` chargé, puis dessine 24 volumes et 24 × 7 braises. Les six shaders de `fire-v1/prepare.py` incorporent `positions.glsl` avec **24 sources constantes**, dimensions, empreintes et plans de combustible. `fit_sources.py` ajuste neuf vasques sur leurs huit faces de charbon ; les autres ancrages restent ceux des acteurs. Garder ce profil accepté comme recette du palais.

### Sources statiques vérifiées de Spargus

| Groupe | Définition / particules | Nombre source |
|---|---|---:|
| `group-waswide-gaslamp` | `waswide-part.gc:3888`, groupe 484, particules 1919–1923 | 33 WCA + 26 WCB = 59 |
| `group-waswide-talltorch` | `waswide-part.gc:4135`, groupe 485, particules 1924–1926 | 2 WCA |
| `group-wasdoors-gaslamp` | `wasall-part.gc:477`, groupe 393, particules 1603–1607 | 4 WSD |
| `group-wascity-palace-fire-beacon` | `waswide-part.gc:1508`, groupe 471, particules 1857–1859 | 1 WWD |

Ces **66 entrées** sont des placements source, pas un nombre garanti d'effets simultanément actifs. Deux lampes WCA, AID **60265 et 46703**, partagent la position (2432.626, 51.632, −158.863) m : tenir compte des états/masques de mission avant d'en faire deux feux. Les deux grandes torches AID **37740/37741** se trouvent à X = 2313.869 / 2338.507, Y = 55.717, Z = −276.159. Premier contrôle proche du secteur côtier : lampe WCB **46673**, (1840.852, 48.817, −387.194) m ; ajuster l'ancrage sur le récipient réel.

Le balayage de tous les fichiers d'acteurs trouve **571 candidats dans 36 groupes** dont le nom contient feu/flamme/torche/gaslamp/burn. Ils sont listés avec AID et niveau : notamment 99 petites torches du temple, 62 petits bols du désert, 33 grands bols du désert et 17 barils de l'arène. **C'est un inventaire candidat, pas une liste de particules à supprimer** : il contient aussi des flammes de geysers et des feux conditionnels ; il ne couvre pas les incendies dynamiques sans acteur placé.

### Généralisation concrète à implémenter

1. Extraire le rendu actuel en service de feu partagé, conservant la recette du palais. Remplacer les tableaux constants/compteurs 24 par une liste de sources actives et une recette explicite par famille : vasque, lampe à gaz, grande torche, baril, signal lointain, feu sur végétation. Conserver couleur, taille, axe et rythme propres au lieu ; la balise à Y = 507,394 m n'est pas une torche de trois mètres.
2. Créer un registre auteur indexé **niveau + AID + groupe**, avec quaternion, échelle, ouverture et surface de combustible. Les lampes utilisent un déplacement local Z dans leurs particules ; transformer cet axe avec le quaternion de l'acteur, au lieu de supposer une flamme verticale à chaque position brute. Ajuster les sources aux nouveaux récipients avant de retirer le rendu d'origine.
3. Relier activation/désactivation aux véritables contrôleurs GOAL de particules, puis copier un instantané vers le thread graphique, sur le modèle du pont synchronisé de `WaterContacts.h`. Un simple test « niveau chargé » dessinerait aussi des feux inactifs ou éteints. Les futurs feux mobiles doivent transmettre leur transformation courante et leur durée de vie.
4. Conserver la profondeur opaque et l'ordre **avant eau** validés dans le palais. Le moteur doit restaurer l'état OpenGL après le service ; ni feu à travers les murs, ni double composition additive. Retirer chaque ancienne couche seulement lorsque son remplacement est présent et actif, sans couper les sons de gameplay, déclencheurs ou dégâts. Les tests restent muets via le lanceur.
5. Garder des budgets et distances par famille : volumes proches, représentation simplifiée au loin, braises et lumière locales bornées. Vérifier les transitions WCA↔WCB↔WWD↔WSD, puis étendre au désert/temple et aux autres groupes recensés ; ne pas dessiner 571 volumes permanents chaque image.

## 6. Prochaine réalisation, directement exécutable

1. Étendre l'export statique avec `first-block-selection.json`, puis archiver un FR3 source propre et ses empreintes. Les coordonnées du bloc et matériaux sont déjà disponibles.
2. Construire dans Blender l'étal 42091 et son auvent 41247, nouveaux volumes et détails visibles, en conservant pivots/rig. Exporter les contrôles Merc cités et leurs LODs. Vérifier l'import dans WCB, l'animation et la destruction avant duplication aux sept emplacements.
3. Reprendre ensemble les caisses/paniers/sacs et le système de fruits, puis le sol, les murets, les palmiers entiers, buissons et cactus 41968. Des textures HD seules ne suffisent pas à cette livraison.
4. Vérifier la place depuis la côte, à hauteur de Jak et depuis les toits, avec comparaisons natives à caméra fixe, collision, passage et destruction. Ensuite étendre aux rues/maisons et portes du tableau, puis au reste de WCA/WCB/WWD/WSD.

L'inventaire et les deux exports natifs ont été générés sans modifier le jeu, ses processus, ses DGO, ses shaders ni les FR3 déployés. Le contrôle visuel du bloc et des nouvelles ressources reste à faire après leur création.
