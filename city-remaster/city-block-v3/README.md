# Bâtiments de Spargus — premier lot visible

Deux maisons de Wascitya, instances natives 1 et 2. État courant : révision R3,
avec quatre ouvertures réelles, dont une habitée. Modèles Blender réimportés,
toitures différenciées, tableaux épais et balconnets.
La sélection reste limitée à ces bâtiments ; ce lot n'est pas le remaster de
toute la ville et ne prétend pas avoir atteint une finition AAA.

La révision `architecture-ornaments-r1` corrige les ornements tronqués du second
bâtiment : sept plaques bronze fermées et biseautées remplacent les formes
partiellement masquées, sans déplacer les ouvertures.
La révision `architecture-ornaments-r2` réancre quatre plaques du côté de la rue.
Leur contrôle inclut les surfaces du bloc complet : le sens de certaines faces
natives plaçait auparavant les plaques à l'intérieur du mur.

La révision `architecture-single-window-r3` referme l'ouverture latérale
`wca-house1-east-room`, située au même étage que l'ouverture habitée conservée.
Elle retire son encadrement, son balconnet et son intérieur. Le mur reprend la
surface native antérieure à la découpe. L'ouverture de façade et celle de
l'étage supérieur restent sur la maison 1 ; les deux ouvertures de la maison 2
restent inchangées. Les fichiers historiques à cinq ouvertures sont conservés
pour la provenance ; ils ne décrivent plus l'état courant.

La toiture de la maison 1 comporte une coupole basse. Sur la maison 2, la
modification reste modérée : relèvement de 0,9 m et huit rebords de 0,98 m de
haut, sans coupole. Ce lot ne remplace pas les textures générales de la ville.

## Intérieurs

Une seule ouverture de la première maison donne désormais sur une pièce
habitée. Les variantes disponibles sont un salon avec habitant assis ou une
pièce avec deux habitants en conversation ; elles ne correspondent plus à deux
pièces habitées simultanément autour du même angle.
Les acteurs viennent des modèles natifs de Spargus, posés dans Blender et animés
par interpolation de quatre poses. La distribution est stable pendant la session.
Les autres ouvertures ont des pièces sans habitants. Le rendu est géométrique,
éclairé et occulté par les murs, avec limitation de distance. Les ouvertures sont
actuellement sans vitrage réfléchissant ; il ne s'agit pas d'un système de
fenêtres destructibles ou d'intérieurs visitables.

La pièce latérale supprimée n'est plus rendue et ne contient plus d'acteurs.
Des ombres de contact douces, calculées sur les pièces et leur mobilier,
améliorent les jonctions et les assises sans modifier les couleurs des matériaux.
Les pièces originales restent conservées dans `interiors/no-ao` ; la révision
et ses mesures sont dans `interiors/ao-candidate` et `interiors/ao-installed.json`.
Le test GPU isolé à 1920×1080 sur RTX 3080 Ti mesure un surcoût médian de
0,031 ms pour deux pièces et 0,104 ms pour cinq pièces avec cette densification.
Ce test exclut les personnages et le reste du jeu (`interiors/qa/gpu-cost.json`).
Les PNJ debout sont ajustés à la hauteur du tapis. L'assise est ajustée au canapé ;
le contact précis des chaussures assises reste un détail de finition.

## Feux et stabilité

Les 61 emplacements identifiés des deux secteurs de ville utilisent la recette
du palais, sous contrôle de leurs émetteurs actifs. Une première version du
raccord GOAL provoquait une erreur mémoire lors du chargement du palais : elle
lisait les modes de particules d'autres cartes. La révision filtre les cartes et
les acteurs avant d'accéder aux transformations. Le démarrage et les passages
palais → WCA → WCB → WCA ont été retestés avec cette révision.

Les essais utilisent `OPENGOAL_TEST_MUTE=1`, vérifié dans le journal audio.
Attention au REPL : `(e)` ferme le compilateur et son destructeur redémarre le
jeu connecté. Cela renvoie au palais et perd le placement de contrôle en ville.
Ne pas utiliser cette fermeture normale pour conserver une scène de démonstration.
La mesure locale du seul passage feu donne 0,33 ms en moyenne / 0,40 ms maximum
sur 12 échantillons à 1600×900, RTX 3080 Ti. Ce n'est pas un benchmark du jeu entier.

## Sources et validation

- `architecture/` : modèles, patchs, sphères de visibilité et audit de préservation.
- `architecture-single-window-r3/` : fermeture latérale, quatre ancres restantes et validations de géométrie.
- `interiors/` : pièces Blender, shaders, moteur de rendu et graphe d'assets.
- `inhabitants/` : acteurs natifs, poses, textures et validations géométriques.
- `verify_preflight.py` : contrôles de provenance et essais de rejets de mutations.
- `../../models-v2/package-validation.json` : vérification du paquet complet.

La revue courante est regroupée dans la [galerie des deux maisons](review-window-fix/index.html).
Son [registre de captures natives](review-window-fix/native-review.json) décrit
les prises et leur version ; l'[index des images](review-window-fix/capture-index.json)
recense les fichiers et leurs empreintes. Les sept comparaisons ordinaires
utilisent `geometry-002` avec les textures précédentes comme état avant, et non
le jeu PS2 original. La comparaison de correction utilise séparément la version
rejetée avec deux ouvertures proches au même étage. La vue du feu WCB provient
d'un contrôle antérieur : cet effet est inchangé dans R3. Les rapports et
captures historiques sont conservés sans être réécrits.

Les captures natives sont dans
`profiles/remaster-palace/OpenGOAL/jak3/screenshots` à la racine du prototype.
Les fichiers de QA contenant `before`, `lounge`, `conversation`, `corner` et
`silhouette` documentent différentes vues. Les captures de diagnostic de caméra
mal placée ne constituent pas une validation.

La suite reste centrée sur les bâtiments, avant l'herbe. La météo, les intérieurs
visitables, les nouvelles armes et un nouveau cycle jour/nuit ne sont pas ajoutés
par ce lot. Les arènes, le désert et ses véhicules restent au programme autorisé.
