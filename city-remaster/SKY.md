# Ciel de Spargus — premier rendu de nuages

## Chemin natif vérifié

- Jak 3 crée `DirectRenderer("sky", BucketId::SKY)` dans
  `engine-src/game/graphics/opengl_renderer/OpenGLRenderer.cpp:182`.
  `SkyRenderer`/`SkyBlend` concernent ici Jak 1.
- `goal_src/jak3/engine/gfx/sky/sky-tng.gc` conserve la palette du mood,
  le déplacement UV, le soleil, la lune, les halos et deux couches éclairées
  de 81 quads. `sky-data.gc` fournit leur grille 10 × 10.
- `TextureAnimator::run_clouds` produit le masque procédural natif ; le header
  définit 128² ou **512²** en haute résolution (le commentaire 256 est ancien).
  Les identités GPU sont `PC-ANIM/clouds` et `PC-ANIM/clouds-hires`.
- La couleur est apportée par les sommets GOAL. Le masque texture utilise
  RGB = 0,5 et alpha de 0 à 0,5 ; cette convention reste respectée.

## Changement isolé

`SpargusClouds.h` substitue uniquement ces deux identités dans le bucket `sky`
de Jak 3, avec WCA, WCB ou `lwasbbv` récemment dessinés et la caméra dans les
bounds Spargus. `lwasbbv.fr3` existe dans les données. Aucun nom de texture
du soleil, des halos, du feu, de l’eau ou du reste du décor n’est accepté.

Le masque privé **1024² RGBA16F** conserve la couverture météo native et
intègre dix échantillons dans un volume de densité peu profond. Trois échelles
de volume et plusieurs échelles de contours évoluent à des vitesses différentes.
La deuxième passe réduit le poids des nappes natives saturées et échantillonne
deux points dans les lobes voisins pour calculer leur ombre dans le volume.
La première passe, testée dans `city-panorama-after-v1.png`, restait trop plate :
l’éclairage selon la profondeur seule rendait les zones denses uniformément crème.
L’absorption et cet ombrage donnent des volumes internes ; les deux
couches directionnelles et les teintes du jeu restent actives. Les fonctions
procédurales sont périodiques pour joindre les bords du dôme répété.

L’ancien masque n’est jamais remplacé dans le pool, ni modifié. Un sampler
privé évite de toucher à ses paramètres. Framebuffer lecture/écriture, viewport,
programme, VAO, texture/unité/sampler, masques couleur et états GL sont restaurés.
Le masque est produit une seule fois par image/source, avec mipmaps.

## Validation et retour arrière

- `apply_spargus_clouds.py` applique les sept fichiers source/shader et écrit
  `spargus-clouds-manifest.json`. `--undo` exige les hashes attendus avant de
  restaurer les fichiers présents ou retirer les fichiers ajoutés.
- `preview_spargus_clouds.py`, Python Blender, compile les GLSL dans un contexte
  WGL invisible. Huit contrôles passent : compilation, valeurs finies, alpha,
  neutralité RGB, évolution visible, continuité temporelle, relief préservé dans
  un masque blanc saturé et absence de nuages lorsque le masque natif est vide.
- Le test 1024² de la deuxième passe mesure environ 1,5–3,9 ms après initialisation.
  Ce résultat isolé ne mesure pas le coût total d’une scène en jeu.
- `sky-preview/*` est un **échantillon procédural synthétique**, pas une capture
  native ni une approbation visuelle. Il ne reproduit pas les deux éclairages
  GOAL, la perspective du dôme ou la position réelle du soleil.

Reste à valider en jeu : vues ville/pont, horizon marin, ciel zénithal,
transitions de mood et régions voisines, transparence des vitres, coût global.
Ce traitement de masque volumique n’ajoute pas une météo ou un ciel volumétrique
tridimensionnel parcourable ; ces étapes restent distinctes.

`cloud-mask-v2-proof.json` conserve le hash de la première passe, la preuve des
insertions réversibles et le hash du fragment remplacé seul dans le package.
La seconde passe attend sa validation native ; le test synthétique ne la remplace pas.
