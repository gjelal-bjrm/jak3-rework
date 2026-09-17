# Premier étal de marché — voie Merc

## Périmètre et état

Auteur : `city-remaster/cty-fruit-stand-lod0.glb`. Contrôle natif exact :
`cty-fruit-stand-lod0`, dans `WCB.DGO` / `wascityb`. Ce premier étal n'existe pas
dans WCA ; sa modernisation seule ne justifie pas de remplacer WCA.

Le script `import_market.py` vérifie les GLB explicites par défaut. L'option `--apply` réalise
une extraction ciblée **dans un projet de staging neuf**. Elle ne déploie pas,
ne compile aucun code, ne lance pas le jeu et ne modifie pas le palais.

Au contrôle du premier export, le GLB auteur contient 8 748 triangles contre 78 d'origine,
une primitive et les quatre articulations natives. Les formats d'attributs,
l'ordre des articulations, leurs matrices et l'alpha sont compatibles. Le
contrôle du gabarit a conduit à corriger les pieds jusqu'au minimum natif de
-0,256 m. Le bois HD 1774×887 est maintenant embarqué. Les extractions ciblées
`market-stand-001` et `market-stand-002` ont réussi ; le second run inclut
automatiquement la préservation exacte du décor courant. `market-import-validation.json`
et les rapports de staging donnent les versions et hashes contrôlés. L'auteur
continue d'évoluer ; ces résultats ne valident pas un export ultérieur ni son
rendu en jeu.

`market-stand-003` valide ensuite l'étal renforcé de 19:16, **14 460 triangles**,
avec la même emprise : pieds galbés, trois casiers, ligatures et bois HD. Son
candidat conservant le décor courant est dans `market-stand-003/candidates/`.
Le lot complet avec auvent et accessoires fait l'objet d'un staging ultérieur.

**Lot complet validé : `market-block-002`**, huit GLB finaux, 11 contrôles de
préservation réussis par niveau. WCA conserve ses 254 textures et ajoute 4 images
HD partagées ; WCB conserve ses 289 textures et ajoute 6 images HD. Les candidats
ne touchent pas WASPALA, WWD, GAME, les shaders ou les scripts GOAL. Les hashes et
la liste exacte des huit GLB figurent dans `staging/market-block-002/import-report.json`.

## Commandes

Depuis la racine du prototype :

```powershell
python city-remaster/import_market.py
python city-remaster/import_market.py --model city-remaster/cty-fruit-stand-lod0.glb --model city-remaster/market-crate-lod0.glb
python city-remaster/import_market.py --apply --stage-name market-stand-003
```

L'appel `--apply` refuse un répertoire existant. Il prépare :

```text
city-remaster/staging/<nom-neuf>/
  project/decompiler/config/                copie indépendante des configs
  project/custom_assets/jak3/merc_replacements/cty-fruit-stand-lod0.glb
  project/custom_assets/jak3/texture_replacements/  pack courant copié
  project/out/jak3/fr3/                      extraction brute, jamais déployée
  candidates/                              FR3 avec décor courant préservé
  backup/                                  anciens FR3 ville + ancien GLB si présent
  command.json, config-override.json, extractor.log
  protected-before.json, protected-after.json, copied-input-hashes.json
  import-report.json, <niveau>-preservation.json
```

L'extracteur officiel est
`versions/official/v0.3.6/extractor.exe` ; le script conserve son SHA-256.
Les options sont explicitement `--folder --decompile`, sans `--extract`,
`--compile` ni `--play`. Sans option de phase, cet exécutable lance toutes les
étapes ; le script ne laisse jamais ce choix implicite.

Répéter `--model` pour chaque contrôle souhaité ; aucune collecte implicite de
tous les GLB du dossier. Les sources natives sont retrouvées par nom exact dans
WCA/WCB/WWD. Les niveaux à extraire sont l'union des niveaux contenant ces
contrôles. L'étal seul cible WCB ; une caisse commune à WCA/WCB cible les deux.
L'auvent couvre les noms `wascity-awning-b-lod0` et `wascity-awning-b-lod1`.

Entrées ISO en lecture : `CGO/GAME.CGO`, `DGO/WASALL.DGO`, `DGO/WWD.DGO`,
`DGO/WCA.DGO`, `DGO/WCB.DGO`. Les fichiers STR et audio sont exclus de cette
extraction. Un fichier d'entrées distinct borne `levels_to_extract` aux seuls
niveaux requis (WCA, WCB, WWD). **Cette liste se trouve dans inputs_file, pas dans une
clé d'override supérieure.** GAME reste généré par `extract_common` même avec
cette sélection ; son FR3 partiel n'est jamais un candidat au déploiement.

Les dépendances bornées ont suffi pour le premier étal avec v0.3.6. Une sortie
réussie exige chaque FR3 attendu, chaque confirmation textuelle de remplacement
dans chaque niveau et la comparaison de préservation. Le log conserve aussi
les avertissements : le premier run a signalé la texture0 de `blocking-plane-lod0`
dans GAME, qui n'est jamais livré. Cela confirme le passage dans l'importeur,
pas son rendu visuel.

## Contrat géométrique vérifié

- GLB en mètres, Y vertical. `gltf_vertices` applique la matrice monde de la
  node, puis multiplie les positions par 4096. Ne pas exporter en unités GOAL
  ni appliquer une seconde multiplication par 4096.
- Une mesh, transform monde identité, scène unique. L'importeur parcourt
  **toutes** les scènes. Des scènes dupliquées produiraient des doublons.
- Faces triangulées et indexées ; POSITION et NORMAL = float VEC3,
  TEXCOORD_0 = float VEC2 ; COLOR_0 requis et format natif vérifié.
- Une primitive par matériau. L'importeur Merc actuel regroupe par matériau,
  mais réécrit `first_index` et `index_count` à chaque primitive : plusieurs
  primitives du même matériau feraient perdre des parties au rendu.
- Squelette dans cet ordre : `align`, `prejoint`, `main`, `fruit`. Les matrices
  monde et inverse-bind sont vérifiées contre le GLB source. Blender ajoute
  une node Armature sans modifier l'ordre des joints exportés ; c'est valide.
- JOINTS_0 doit être **UNSIGNED_BYTE**, même si GLTF autorise d'autres formats.
  WEIGHTS_0 doit être **FLOAT**. Le code conserve trois influences sur quatre,
  ajoute 1 aux indices puis renormalise ; des poids tous nuls sont invalides.
- La source utilise uniquement `main` pour les sommets visibles du stand.
  Le script exige le même ensemble d'articulations influentes dans l'auteur.

Le premier étal garde `enable_custom_weights` absent/faux :
`merc_convert_replacement` reprend les poids et indices de matrices du sommet
natif le plus proche. C'est cohérent pour cet étal rigide, où tous les sommets
visibles sont pondérés sur `main`. Les animations de jeu et le contrôle restent
dans le DGO ; les animations exportées dans le GLB ne sont pas importées dans
le jeu par cette voie. Cette règle ne suffit pas pour une porte articulée ou un
auvent qui rebondit : ils nécessitent un contrôle d'influences par pièce.
Le validateur accepte `enable_custom_weights=1` après preuve de conservation du
rig ; il indique alors explicitement l'utilisation des poids auteur. Les agents
auteurs doivent vérifier l'association des pièces aux articulations.

Cas vérifié de l'auvent : le `defskelgroup` dans `waswide-obs.gc:723-724` emploie
`wascity-awning-b-lod0-jg` pour ses deux contrôles. Le GLB source LOD1 omet la skin,
donc sa validation référence explicitement le rig du LOD0, enregistré avec hash.
Le LOD1 natif utilise uniquement les matrices 3..7 (main, centerc, centerd,
leftb, rightb) ; le LOD0 utilise 3..11. Le contrôle d'influences empêche d'ajouter
au LOD1 des joints non utilisés par son contrôle natif. Blender peut trier les
enfants du rig à l'export : réordonner seulement `skin.joints` sans remapper
JOINTS_0 et inverseBindMatrices est incorrect.

Les buffers des GLB natifs sont partagés entre contrôles. Pour mesurer un objet,
il faut utiliser les sommets référencés par ses indices, et pas tous les sommets
du POSITION accessor. Le contrôle source de l'étal donne ces limites Y-up :

| Axe | Minimum | Maximum |
| --- | ---: | ---: |
| X | -4,688804 | 4,652173 |
| Y | -0,256419 | 2,051352 |
| Z | -1,575145 | 1,575145 |

Les fruits du marché sont des particules natives distinctes. La pente, les
compartiments et le gabarit de présentation doivent donc rester compatibles.
Le remplacement du Merc ne modifie ni leurs groupes, ni leur collision.

## Matériaux et alpha

Le matériau source est `city-slum-wood-plain`. Son image embarquée fait 64×32,
RGBA, alpha constant 128. La source utilise MASK, seuil 0,1490196. L'importeur
divise l'alpha de l'image par deux et convertit le seuil en `alphaCutoff*127` :
64 dépasse le seuil d'environ 18,9, donc aucune découpe du bois. MASK conserve
l'écriture dans la profondeur ; BLEND la désactive et est refusé pour cet étal.

Les facteurs PBR de couleur/métal/rugosité et une normal map ne donnent pas
automatiquement un matériau moderne dans ce chemin. Le rendu natif reprend
principalement texture de base, UV, normales, RGBA et mode alpha. En particulier,
le `baseColorFactor` [2,2,2,2] de la source GLB n'est pas appliqué par cette voie.

**La texture du remplacement Merc vient directement du PNG du GLB**, ajouté par
`texture_pool_add_texture`. Elle ne repasse pas dans les remplacements du
TextureDB. Pour obtenir un bois HD sur cet objet, intégrer l'image HD dans le
matériau Blender puis réexporter le GLB. Copier le pack de textures de terrain
dans le staging ne suffit pas. L'import valide image RGB/RGBA8 PNG embarquée,
sampler présent, filtre compatible et wrap REPEAT ou CLAMP_TO_EDGE. Les URI
externes et le wrap miroir sont refusés. TinyGLTF développe les PNG RGB en
RGBA255, puis l'importeur réduit l'alpha à 127. La limite initiale est 4096 pixels par
axe et 15 000 triangles pour cet étal.

## Préserver palais, V11 et prochaines zones

Les FR3 ville actuels sont sauvegardés avant toute extraction de staging.
Les empreintes des FR3 palais/ville/mer/GAME, DGO correspondants et shaders dans
ROOT et DATA sont comparées avant/après. Aucune sortie n'est copiée dans ces
répertoires, dans les variantes ou dans les profils utilisateur.

WASPALA n'est pas une entrée ni une sortie de l'extraction. Les modèles du
palais et les effets V11 restent donc intégralement présents. Il n'y a aucune
raison de réappliquer le palais lors d'un import ville ciblé. Si une future
extraction globale est décidée, `models-v1/apply_models.py SOURCE_PROPRE DEST`
est la voie existante de réapplication ; elle combine les patches configurés
dans `model-set.json`, préserve les faces du combustible et enregistre le hash.
Ce script écrit aussi son rapport partagé : ne pas l'appeler concurremment.

Réextraire WCA/WCB rétablit leur topologie ISO et insère les nouveaux buffers au
milieu des groupes Merc, déplaçant les indices d'autres objets. Le premier lot
brut a été bloqué par la comparaison stricte. `compare_market.py` évite ces
régressions en partant du **niveau courant complet** : il conserve sa table de
textures, son bloc statique, ses contrôles Merc hors liste et ses buffers déjà
présents. Il ajoute seulement les vertices/indices/textures utilisés par les
draws des contrôles explicitement sélectionnés, puis recalcule leurs références.
Les textures ajoutées identiques sont partagées par hash ; les textures courantes
gardent leurs indices, dimensions, flags et RGBA exacts, même si le projet
d'extraction ne contient pas un ancien pack HD.

Le bloc statique couvre index textures, tous les LOD TFRAG/TIE/SHRUB, vent,
couleurs, hfrag et collision : **12 600 126 octets WCA et 13 593 106 octets WCB**
identiques. Tous les contrôles Merc hors liste, leurs buffers existants et indices
sont aussi identiques. Après réindexation, une vérification indépendante compare
le payload réellement dessiné de chaque draw avec l'extraction : ordre des
triangles, positions, normales, UV, RGBA, matrices, poids, texture et mode de
dessin. Elle passe pour les cinq modèles WCA et les huit WCB du lot final.

Trois paramètres Merc (`st_vif_add`, `xyz_scale`, `st_magic`) sont aussi repris
octet par octet depuis le contrôle courant. L'importeur v0.3.6 laisse ces champs
non initialisés dans son nouveau modèle ; les conserver évite des valeurs
indéterminées et des hashes instables. Les données auteur utiles (draws, normals,
positions, couleurs, poids, indices, textures) restent issues du GLB. Le contrôle
refuse les remplacements avec des mod draws ou envmaps natifs non pris en charge ;
les huit contrôles du premier marché n'en utilisent aucun, vérifié dans WCA/WCB.

Si un contrôle échoue, aucun candidat validé n'est livré. Un ancien remplacement
Merc absent de la liste reste celui du niveau courant, avec ses vertices et ses
textures. Les données des autres modèles réextraits sont ignorées. Ce traitement
explicite est enregistré dans `static_preservation.method`, avec la table de
réindexation des textures et le nombre de triangles/vertices transférés par objet.

Le script de comparaison utilise le Python de Blender (module `zstandard`
installé), lit le format FR3 v43 et vérifie la lecture complète jusqu'au champ
terminal. Les octets statiques sont recopiés sans reconstruire/interpréter leur
contenu. Seuls les fichiers sous `city-remaster/staging` peuvent être écrits,
et aucun fichier existant n'est écrasé. Le mode sans `--preserve-static` reste
en lecture seule.

Pour ce premier étal, la liste de déploiement ultérieure peut se limiter au
`candidates/wascityb.fr3` après contrôle
du rendu natif, du niveau de détail, de la collision/fruits et comparaison du
reste de la ville. **Ne jamais copier le GAME.fr3 de staging.**

## Points du code audités

- `engine-src/decompiler/level_extractor/extract_level.cpp` : recherche
  `custom_assets/jak3/merc_replacements`, ciblage des niveaux, GAME commun.
- `engine-src/decompiler/level_extractor/extract_merc.cpp` : remplacement par
  nom exact du contrôle, ajout des nouveaux buffers et textures.
- `engine-src/decompiler/level_extractor/merc_replacement.cpp` : primitives,
  sélection des poids, groupes Merc conservés dans la nouvelle géométrie.
- `engine-src/common/util/gltf_util.cpp` : transform, facteur 4096, formats,
  trois influences, alpha, textures et sampler.
- `engine-src/decompiler/config.cpp` et `decompilation_process.cpp` : séparation
  inputs/override et niveaux générés.
- `engine-src/decompiler/extractor/main.cpp` : options de phase et projet isolé.

Statut : code audité, huit GLB finaux validés, extraction ciblée et préservation
binaire/payload validées en staging ; aucune installation ni validation en jeu
par ces outils. Le déploiement et les essais natifs restent une étape distincte.
