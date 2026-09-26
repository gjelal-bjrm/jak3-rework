# Journal du remaster — travail pendant ton absence

Ce fichier liste tout ce que je fais, dans l'ordre, avec ce qui a été vérifié et comment. À ton retour :
lance **LANCEUR-DE-TESTS.cmd** et regarde les lieux indiqués. Les captures de contrôle sont dans `qa/`.

Règles suivies (tes consignes du 26/09) : histoire dans l'ordre, le plus voyant d'abord, textures Codex
intégrées au fur et à mesure et **vérifiées à l'affichage**, chaque changement testé en jeu avant de passer
à la suite, rien d'éteint.

---

## 26/09 — avant ton départ (déjà vu avec toi)

- **Arène, falaises** : grès sculpté en couches sur toutes les falaises (2,5 millions de triangles).
- **Arène, textures** : les 76 textures Codex en version « Genshin » ; plaquage refait sans étirement
  (plus d'effet « tordu ») sur 140 000 faces ; roches plaquées selon le monde.
- **Éclairage moderne** : occlusion ambiante + ombres portées du soleil (décor et personnages), partout.
- **Feu** : refait de zéro, remplacé partout (palais, ville, arène, et automatiquement ailleurs).
- **Eau du palais** : claire au lieu de laiteuse.
- **Arène, brume** : fumée et chaleur de la lave, permanente.

## 26/09 — après ton départ

### 1. Braseros de l'arène (tes deux signalements)
- **Feu qui dépassait sous la vasque** : ma vasque remodelée avait la hauteur et le rayon inversés (cône
  étroit au lieu de la coupe large d'origine). Corrigé ; profil comparé point par point à l'original.
- **Braseros des tribunes** : ce sont des copies réduites (×0,66). Mon remodelage les avait faits en grand
  (vasque trop large, rebord qui cachait le feu). Chaque brasero a maintenant sa taille d'origine.
- **Feu effacé devant le ciel** : le ciel, la mer, les spectateurs et la brume étaient dessinés après le
  feu. Le feu est maintenant dessiné en dernier.
- **Contrôle** : nouvel outil `qa_fires.py` qui photographie **chacun** des 18 braseros avec une caméra libre
  (`qa_live.py --freecam`), + vues de dessous. Planche : `qa/fires-arena.png`. Tous corrects.

### 2. Chaîne générale des textures (pour intégrer Codex au fur et à mesure)
- Codex avance dans l'ordre de l'histoire (désert de l'intro, train aérien, ville de Spargus…).
- Découverte : une même texture existe souvent **en copie dans plusieurs niveaux** (les textures de l'arène
  sont aussi dans GAME, les cinématiques de l'arène et les niveaux du temple). C'est ce qui s'était passé
  dans l'arène. La nouvelle chaîne (`remaster-build/build.py`) pose chaque texture dans **tous** les niveaux
  qui la contiennent et vérifie le nombre remplacé.
- Contrôle d'affichage : le moteur peut noter chaque texture réellement liée sur la carte graphique
  (variable `REMASTER_TEXTURE_AUDIT=1`), dans tous les lieux.
- Le choix « Textures de l'arène » a été retiré du lanceur : la version Genshin est retenue partout.
- **Construction du 26/09 (44 textures Codex + 76 de l'arène)** : 30 niveaux reconstruits (arène, ville,
  palais, désert de l'intro et ses cinématiques, désert, temple, hangars…), chacun avec exactement le nombre
  de textures attendu.
- **Vérifié en jeu** (`qa_textures.py`, contrôle d'affichage) : arène — 45 + 18 textures HD affichées,
  aucune restée en basse définition ; ville — 13 HD affichées, aucune manquante. Captures : `qa/tx-city-sheet.png`.

### 3. Ville de Spargus — les montagnes (le plus voyant)
- Mesure des surfaces : les montagnes de roche autour de la ville (niveau waswide) font **1,18 million de m²**,
  dix fois plus que tout le reste ; puis le sol (270 000 m²) et les rochers du rivage (168 000 m²).
- Sculpture en couches de grès, comme l'arène, mais avec des couches **deux fois plus épaisses et plus
  profondes** (à cette échelle, les couches fines de l'arène ressemblaient à du bois). Aperçus Blender :
  `arena-remaster/rocks/preview/city-cmp2.png`.
- **Installé et vérifié en jeu** : 179 blocs, 3,6 millions de triangles ; **60 images/s** constantes dans la
  ville (mesure `REMASTER_PERF=1`). Comparaison jeu d'origine / remaster aux mêmes cadrages :
  `qa/mt-compare.png` et `qa/mt-compare2.png`.
- **Réglage de l'éclairage** : la roche devenait trop sombre (ombre des faces dos au soleil, en plus de
  l'ombrage déjà peint dans les couleurs du jeu). Ombre propre modérée : l'ocre chaud d'origine revient, les
  ombres portées restent nettes. Vaut pour tout le jeu (arène comprise).

### ⚠️ Réparé : le mode « Jeu d'origine » du lanceur ne démarrait plus
Chaque nouveau fichier du remaster (shaders d'éclairage, du feu…) était ajouté à la liste vérifiée par le
lanceur, mais pas à la version d'origine : le lanceur refusait de la démarrer. Corrigé, et `sync_variant.py`
complète désormais automatiquement les autres versions. Les deux modes démarrent (vérifié).

### 4. Ville de Spargus — textures Codex et rivage
- **Textures** : 143 textures Codex intégrées (désert de l'intro, train aérien, ville, palais…). Dans la
  ville : 75 + 62 textures HD posées. **Vérifié en jeu** : 109 textures HD affichées, aucune restée en basse
  définition (le contrôle en avait trouvé 2 dans waswide lors d'un premier passage — cause : deux
  constructions lancées en même temps ; corrigé et verrou ajouté pour que ça n'arrive plus).
- **Rochers du rivage** (168 000 m²) : sculptés en couches (couches ×1,4). 6 448 → 847 000 triangles.
  60 images/s. Comparaison : `qa/sh-compare.png`.

### 5. Ville de Spargus — plaquage sans étirement (effet « tordu »)
- Même méthode que l'arène : chaque surface est « dépliée » à plat, puis la texture y est reposée à sa taille
  réelle. Les motifs réguliers (panneaux, tôles, toits) gardent leur alignement.
- 10 matériaux, 203 000 faces (murs de tôle extérieurs, toits, route, pièces de métal…). Étirement typique :
  tôle des remparts **2,6 → 1,1**, pièces de métal **7,1 → 1,2**, route **1,8 → 1,0** (1,0 = parfait).
- Essayé puis retiré : les bidons de feu (le résultat était pire qu'avant).
- Rochers du rivage plaqués selon le monde, comme les montagnes.
- **Vérifié en jeu** : textures HD toutes affichées (contrôle d'affichage : 54 + 6 + 3, aucune manquante).
  Captures : `qa/uv-city-compare.png`, éclairage moderne coupé / actif : `qa/wall-shadow.png`.

### 6. Textures Codex — 2ᵉ série (palais, train aérien, désert) et contrôle de chaque texture
- 104 nouvelles textures Codex intégrées (palais de Damas, toits et intérieurs du train aérien, désert, vaisseau
  des KG). Avant d'installer, chaque texture est comparée à son original (planches `qa/codex-new-*.png`,
  `qa/codex-pairs-a.png`, tri automatique des plus grands changements de couleur `qa/codex-colorshift.png`).
- **6 textures refusées** (le jeu garde l'original) : braises du palais devenues turquoise, feuilles de palmier
  transformées en dalle de bassin ou en aplat orange, pierre grise des totems devenue terre orange, gravier à
  paillettes sur une montagne lointaine. Liste et consigne pour les faire refaire par Codex :
  `textures-remaster/codex/TEXTURES-A-REFAIRE.md` (refus notés dans `textures-remaster/rejets.json`).
- **Vérifié en jeu** : palais — 56 textures HD affichées, aucune manquante ; désert — toutes affichées.
  Comparaison jeu d'origine / remaster du palais : `qa/palx-compare.png` (l'identité du palais est gardée).

### 7. Outils de contrôle
- `qa_compare.py` : lance le remaster puis le jeu d'origine, prend les mêmes vues avec la caméra libre, fait la
  planche côte à côte, le contrôle des textures affichées et la mesure de fluidité, en une commande.
- Nouvelles scènes de test dans le lanceur : `desert` (grand désert devant la porte de Spargus), `wasdoors`
  (porte du désert), `intro` (désert du début de l'histoire).
- **Météo des captures** : la météo de départ est tirée au hasard ; un orage au démarrage laissait le ciel gris et
  des flaques pendant les captures (faux « avant/après »). Les tests démarrent maintenant directement par beau
  temps (le jeu normal garde sa météo au hasard).

### 8. Désert — les montagnes (le plus voyant du désert)
- Mesure : les roches font **85 % de la surface** du désert. Les grandes montagnes (niveau `desert`) :
  12,8 millions de m² dessinés avec seulement 61 000 triangles, soit ~260 m² par facette : c'est ce qui donne
  l'aspect « vieux jeu » (grandes facettes plates).
- Sculpture en couches de grès adaptée à l'échelle : couches de 4 à 11 m creusées jusqu'à 4 m pour les grandes
  montagnes, couches de 2,5 à 7 m pour les rochers du désert. Les pointes restent pointues (premier essai :
  arrondi trop fort, pointes fondues en « bougies » — corrigé avant installation, aperçus
  `arena-remaster/rocks/preview/desert*-cmp*.png`) ; creusement limité selon l'épaisseur des aiguilles.
- Textures des roches plaquées selon le monde (échelle d'origine mesurée : `desert-remaster/rocks/measure_tiles.py`).
- **Installé et vérifié en jeu** : grandes montagnes 63 828 → 3,0 millions de triangles ; rochers devant la porte
  (desertb) 99 224 → 1,6 million. **60 images/s**, pire image 32 ms (comme avant). Comparaison aux mêmes
  cadrages : `qa/desm-compare.png`.

### 9. Désert — teinte des textures (sol jaune criard corrigé)
- Constat en jeu, au pied de la porte : sol jaune vif à taches orange, rien à voir avec l'original. Diagnostic
  (bascules une par une, `qa/sand-diag.png`, puis tir de rayons sur la géométrie) : ce n'est pas le sable du
  désert mais deux sols texturés (`wascity-ground-01`, `des-beach-01`). Les textures d'origine sont gris-vert ;
  le jeu les colore par l'éclairage des sommets (orangé dans le désert). Codex les avait faites orange :
  orange × orange = jaune criard.
- Mesure sur toutes les textures Codex : Codex réchauffe et éclaircit presque tout. Correction automatique
  dans la préparation : quand la teinte moyenne s'écarte franchement de l'original, elle y est ramenée à 80 %
  (dessin de Codex intact, pas de flou). 37 textures concernées (sols du désert, pierres bleues du palais, œufs,
  ruines…). La ville (déjà validée) n'est presque pas touchée.
- Vu en jeu ensuite : la 1ʳᵉ version de cette correction bleuissait les parties sombres (stries bleues sur les
  troncs de palmiers). Remplacée par une correction « balance des blancs » (chaque couleur multipliée) : plus
  aucune teinte opposée. Planche de contrôle des 37 textures : `qa/hue-back-v3.png`.
- 3ᵉ série Codex (167 textures : temple, ruines, Haven, marcheur précurseur, volcan) contrôlée ; 26 refusées de
  plus (cartes de reflets redessinées, halos devenus granuleux, lave ajoutée sur des roches du volcan qui n'en
  ont pas…). Liste à jour : `textures-remaster/codex/TEXTURES-A-REFAIRE.md` (32 textures).

### 10. Désert — toutes les zones, palmiers et herbe (végétation refaite en modèles)
- **Roches des 8 zones du désert** sculptées (mêmes réglages que devant la porte) : de 58 000 à 103 000
  triangles d'origine par zone → 0,65 à 1,66 million.
- **Palmiers** (oasis) : dans le désert, un palmier est un assemblage (tronc + dizaines de palmes posées une à
  une). Chaque palme d'origine = tige plate + deux cartes « plume » transparentes. Remplacée par une vraie palme :
  tige ronde, rachis qui s'affine, 48 folioles séparées (pliées, arquées, retombantes) qui suivent exactement la
  silhouette d'origine. Troncs : section ronde qui suit la courbe d'origine, bourrelets, relief, pied évasé.
  Construits une fois par modèle, posés sur chaque exemplaire (les couronnes gardent leur disposition).
  Aperçus : `desert-remaster/palms/preview/palms-cmp*.png`. Script : `desert-remaster/palms/author_palms.py`.
- **Herbe sèche** : touffes de cartes croisées remplacées par de vrais brins (effilés, courbés, hauteurs variées),
  couleur de l'herbe d'origine. Aperçu : `desert-remaster/plants/preview/grass-cmp.png`.
- **Occlusion ambiante** : en jeu, elle noircissait les touffes d'herbe (brins fins et serrés). Vérifié en
  coupant les effets un par un (`qa/grass-light.png`). Les plantes sont maintenant exclues de l'assombrissement
  (le sol autour garde son ombre de contact).
- Test par zone : `qa_zones.py <zone>` (scènes `desa`…`desh`, `oasis` ajoutées au lanceur) → `qa/zone-*.png`.
