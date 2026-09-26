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
