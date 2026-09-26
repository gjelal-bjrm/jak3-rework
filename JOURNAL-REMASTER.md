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
- **Vérifié en jeu (zones D et E)** : 60 images/s constantes, textures toutes affichées. Herbe : paille dorée
  comme l'original mais en vrais brins ; troncs sans stries bleues ; roches en couches. `qa/zone-dese-compare.png`,
  `qa/zone-desd-compare.png`.
- **Sable du désert** (rendu « hfrag », tout le sol des grandes étendues) : vérifié actif (mode test magenta).
  Les rides étaient trop discrètes sous un soleil haut ; relief stylisé renforcé : fines rides de vent visibles
  de près, qui s'effacent au loin, teinte légèrement variée. Effet réel mais modeste (`qa/sand-zoom2.png`).
  Les ombres des roches tombent maintenant aussi sur ce sable.
- **Dalles plates du désert** : ressortaient en « biscuits » orange vif sur le sable pâle. Leur texture
  (`des-rock-01`) reprend la teinte d'origine (sable kaki) ; les montagnes gardent leur grès chaud.

### 11. Temple précurseur — falaises extérieures
- Mesure : l'extérieur du temple (`temple_sandstone_out_01`) = 4,6 millions de m², le reste est de
  l'architecture en blocs (textures Codex déjà posées). Falaises sculptées en couches : 52 000 → 792 000
  triangles. Scènes de test `temple` (ravin d'entrée) et `templea` (entrée intérieure).
- Correction : l'empaquetage des sommets du moteur refusait les nouveaux sommets au-delà de x = 4 096 m
  (contrôle de précision fait en flottants simples) ; calcul passé en double. Temple reconstruit sans erreur.

### 12. Volcan — entrée
- Roches volcaniques sculptées dans un style propre (bosses et fissures, pas de couches de grès) :
  13 854 → 191 876 triangles.
- **Trop sombre en jeu** (luminosité moyenne 16 contre 30 pour l'original). Mesuré en coupant les effets un par
  un : l'ombre du soleil s'ajoutait à l'ombre déjà peinte dans l'éclairage du jeu (canyon encaissé = double
  ombre). L'ombre du soleil n'agit maintenant pleinement que sur les surfaces que le jeu éclaire au soleil :
  volcan revenu à 25 (original 30), ombres du désert intactes (`qa/volcano-fix.png`, `qa/shadow-check.png`).
- Outil de test : les coordonnées négatives (volcan) étaient lues comme des options ; corrigé.

### 13. Contrôle de luminosité par zone (nouveau réflexe) et corrections
- Mesure systématique de la luminosité remaster / original aux mêmes cadrages. Désert et ville : 1,0 (identique).
  **Lieux encaissés trop sombres** : temple 0,76, intérieur du volcan 0,77 (ombre du soleil + occlusion
  ambiante qui s'ajoutent à l'ombre déjà peinte par le jeu).
- Corrections (valables partout) : ombre du soleil un peu plus claire ; occlusion ambiante plafonnée à -40 %
  et sa petite échelle allégée (elle faisait des **traits noirs « en épines »** là où des plaques de roche se
  croisent, vus au volcan) ; au volcan, éclairé surtout par la lave dans le jeu, l'ombre du soleil est discrète.
  Résultat : temple 1,01, volcan 0,84 à 0,95 ; désert et ville inchangés (vérifié `qa/cityl-compare.png`).
- **Sol de mousse du volcan** : la texture Codex l'avait changé en pavés bruns ; teinte verte d'origine
  remise (le dessin de Codex reste).
- Outil : les captures attendent maintenant 30 s le chargement complet du lieu (au volcan, la 1ʳᵉ vue était
  prise avant l'affichage).

## 26/09 (soir) — tes retours en direct

### 14. Désert — sable « façon Genshin » (ton retour : « catastrophique, on ne voit rien de loin »)
- Mes premières retouches (rides fines, sable HD posé en léger détail) ne se voyaient que de près. Refait sur
  un autre principe : ce qui fait un désert à la Genshin, c'est la **lumière et la forme**, pas la texture.
- Relief des dunes éclairé au pixel (pente tirée de la carte des hauteurs du terrain) avec une rampe douce façon
  dessin animé : flanc au soleil doré et lumineux, flanc à l'ombre orangé-violet ; **grandes rides de vent**
  (1,2 m) visibles à moyenne distance et fines rides tout près ; bandes de vent et traces claires / rousses
  visibles de loin ; sable chaud et saturé ; **paillettes** qui scintillent ; sable HD peint en détail.
- **Brume chaude du désert** : les lointains se fondent dans une lumière dorée (profondeur).
- Ton verdict : « c'est mieux, là on voit clairement une différence ». Planche : `qa/gs1-compare.png`.
- Le vrai sable du désert n'était pas dans le kit Codex (le sol du désert est un atlas de petits carreaux) :
  entrée prioritaire ajoutée en tête du kit (`des-sand-hd-v1`, voir `codex/PRIORITE-SABLE.md`). En attendant,
  c'est le sable de la plage de Spargus qui sert de détail peint.

### 15. Désert — l'eau (ton retour : mer, rivière et cascades pas refaites)
- **Mer et rivière du désert** : la nouvelle eau (celle de Spargus, un peu plus turquoise) couvre maintenant
  toute la carte d'eau du désert (mer autour, lac de l'oasis de la zone E, rivière qui traverse le désert) —
  masque de côte généré depuis les tables d'origine (`models-v2/build_ocean_coast_mask_desert.py`, aperçu
  `models-v2/ocean-coast-mask-desert.png`).
- **Grande cascade** (zone D) : ce n'était pas un objet mais la pente du terrain peinte en vert sombre. Cette
  peinture est maintenant rendue comme de l'eau vive : filets blanc-turquoise qui tombent vite, écume au pied.
  Planches `qa/casc10-compare.png`. Scène de test « Désert : grande cascade et rivière » dans le lanceur.

### 16. Ville de Spargus — ton retour : « très peu de différence au sol, aux maisons, aux textures »
- Mesuré : dans la ville, le remaster était même **plus sombre** que l'original (0,87 à 1,0). Deux causes :
  1. ma correction de teinte des textures (faite pour le sable du désert) avait ramené une partie de la ville
     (sol, bas des murs, supports) au gris-vert d'origine alors que Codex l'avait faite en grès chaud ;
  2. aucun éclairage moderne sur les murs et le sol de la ville, seulement l'ombre et l'occlusion (qui assombrissent).
- Corrections : couleurs de Codex rétablies pour toute la ville (sans correction de teinte) ; **nouveau rendu du
  décor « façon Genshin »** : la lumière précalculée du jeu garde sa force mais perd sa teinte orangée (plus de
  « jaune criard »), soleil stylisé (faces au soleil chaudes et lumineuses, faces à l'ombre bleu-violet clair),
  couleurs plus vives, plantes comprises. Suite de cette entrée après contrôle en jeu.
- Codex : 202 nouvelles textures (Haven, port, fermes) contrôlées et intégrées ; 2 refusées (la photo de l'équipe
  de Naughty Dog cachée dans une fenêtre du port, un halo devenu granuleux).
- **Contrôlé en jeu** (4 cadrages, près et loin, `qa/cityD-cmp.png`) : ville nettement plus claire que l'original
  (1,04 à 1,21), grès chaud au lieu du gris-bleu, ombres claires lavande, roches vives, brume de profondeur vue
  de loin. Premier essai trop jaune (« sable jaune citron ») : jaunes et oranges moins poussés, soleil plus blanc.
- Le même rendu s'applique aux roches du désert (plus chaudes, cohérentes avec le sable) : `qa/gs2-3way.png`.
  Corrigé au passage : de fausses taches d'eau turquoise au pied des rochers (ombres bleutées prises pour la
  cascade peinte) — `qa/water-threshold.png`.
- Pour comparer toi-même : le rendu se coupe en test avec `pc-remaster-lighting 263` (256 = rendu Genshin coupé).

### 17. Désert — les lointains et l'air (ton retour : « de loin il redevient moche », « il manque une ambiance aérienne »)
- **Pourquoi le sable redevenait « l'ancien » au loin** : le carreau de sable d'origine (8 m, sans version réduite
  pour la distance) donnait au loin un texel au hasard par pixel. Ce grésillement, c'est exactement l'aspect de
  l'ancien sol. Au loin, le carreau est remplacé par sa couleur moyenne (calculée au chargement).
- **Taches sombres sur le sable au loin** : ce n'étaient ni les ombres du soleil ni les couleurs d'origine
  (vérifié en les coupant une à une). C'était mon éclairage des bosses moyennes du terrain (15 à 40 m), qui
  basculaient d'un coup dans l'ombre. Maintenant, l'ombre franche est réservée aux grandes dunes et aux rides, et
  les bosses moyennes ont un modelé doux. Les ombres à l'ombre sont aussi plus claires et plus fraîches (plus
  d'aspect « sale »).
- **Le sable garde son dessin plus loin** :
  - les grandes ondulations de 47 m restent visibles jusqu'à ~400 m au ras du sol ;
  - des paillettes lointaines, d'un pixel, restent des points même en vue rasante ;
  - un éclat du soleil sur le sable face au soleil ;
  - du sable qui court au ras du sol avec le vent, par bouffées, autour du joueur.
- **L'air du désert** :
  - **ciel dégagé** : moitié moins de nuages au-dessus du désert, azur franc en haut, blanc-bleuté lumineux à
    l'horizon. La bande gris-brun d'origine au-dessus de l'horizon a disparu. La fumée du volcan reste intacte,
    avec une frange grise et non un halo bleu. Tout cela uniquement en plein jour : l'aube et le couchant gardent
    leurs couleurs ;
  - **air chaud** : au ras de l'horizon, les lointains ondulent comme au-dessus du sable brûlant (discret sur une
    image fixe, visible en jeu). Le haut des montagnes et les objets proches restent nets ;
  - **brume** : poussière chaude et lumineuse jusqu'à ~1 km, qui dérive avec le vent. Très loin, elle rejoint le
    blanc-bleuté du bas du ciel, sans bande à l'horizon.
- **Ombres des nuages** : grandes taches douces (plusieurs centaines de mètres), plus légères. Les petites taches
  nettes ressemblaient à des salissures.
- **Corrigé au passage** : au couchant, le sable à l'ombre bleuissait et devenait de l'« eau » par taches (repérage
  de la cascade peinte fait sur la couleur du moment). L'eau est maintenant repérée une fois pour toutes, avec
  l'éclairage de 13 h relevé en jeu. La cascade est intacte de jour, et il n'y a plus d'eau parasite au couchant.
- Contrôlé :
  - 6 cadrages près et loin, jeu d'origine / version testée / maintenant (`qa/desert-air-3way.png`) ;
  - aube, matinée et couchant (`qa/gs-hours.png`, `qa/casc14-dusk.png`) ;
  - cascade (`qa/casc15.png`) ;
  - 60 images/s.
