# Jak 3 — prototype visuel Spargus, liquides V3

Deux scènes jouables : l’arène du début et les bassins/fontaines du palais. Le prototype utilise une copie isolée du jeu et un moteur OpenGOAL v0.3.6 modifié. Les profils de sauvegarde sont séparés de l’installation habituelle.

## Lancer

- **Tester-EAU.cmd** : bassins et fontaines, matériau d’eau V3 et interactions de Jak.
- **Tester-FEU.cmd** : même palais, avec les 24 foyers du prototype de feu.
- **Jouer-REMASTER.cmd** : arène, décor remaster V1 et lave V3.
- **Comparer-EAU-ORIGINALE.cmd** : palais avec le moteur et les graphismes originaux.
- **Comparer-ORIGINAL.cmd** : arène originale.
- **Comparer-PREMIER-REMASTER.cmd** : décor V1 avec les liquides d’origine.
- **Tester-VILLE.cmd** : ville de Spargus. Jak est placé automatiquement dans la rue devant les deux maisons pilotes (fenêtres habitées, plaques de bronze, herbe réactive à quelques mètres).
- **Comparer-VILLE-ORIGINALE.cmd** : même endroit avec le moteur et les graphismes originaux.

Les fichiers de lancement se trouvent dans le dossier principal du prototype. Fermer la fenêtre du jeu avant de changer de variante. Les scènes démarrent à leur point de test, à 09:00. Aucune compilation n’est nécessaire pour jouer. Le lanceur habituel OpenGOAL ouvre toujours l’installation habituelle.

La scène ville n’a pas de route de démarrage propre : `launch.py` démarre par la route du palais, lance le compilateur officiel `goalc` (v0.3.6) sur un port dédié, le connecte au jeu, envoie Jak au point de reprise `wascitya-seem` puis le déplace devant la maison pilote 1. Le journal `city-goalc.log` garde la trace du compilateur ; les lignes `VILLE :` du lanceur indiquent chaque étape. Compter une trentaine de secondes avant d’arriver en ville.

La mention **Prototype liquides V3** en bas de l’écran confirme le moteur modifié. `launch.py` vérifie les empreintes des 28 fichiers de chaque variante, du moteur V3 et de son code de démarrage. Les comparaisons originale/V1 emploient le moteur officiel et leurs routes préservées. La passe V2 refusée est archivée dans `variants/remaster-liquids-v2`.

## Eau du palais

- Les bassins animés sont rendus par **Merc2**. Le nouveau matériau est raccordé à leur texture `waspala-water-dest` ; c’était la cause de l’absence de différence lors des premiers essais.
- Ondulations par pixel, réfraction, absorption selon la profondeur, reflets des éléments visibles à l’écran, scintillements et caustiques animées sur le fond.
- Les contacts réels détectés par le contrôle d’eau de Jak alimentent des vagues circulaires, une trace de remous pendant le déplacement et des gouttelettes avec trajectoire balistique. Les effets s’arrêtent quand Jak quitte l’eau. La file est limitée à 32 contacts et expire au bout de 4 secondes.
- Dans les volumes du palais, les anciennes éclaboussures de Jak, leurs anneaux et leur traînée sont désactivés. Les nouveaux contacts déforment le maillage de l’eau et les normales utilisées par les reflets et la réfraction. L’amplitude augmente avec la vitesse de déplacement et de chute ; les variations de hauteur des pieds permettent de conserver un impact même lorsque le fond arrête Jak dès son entrée dans l’eau.
- Quatre jets de fontaine en volume, placés à partir des acteurs du niveau ; leurs contours et leur surface s’animent pendant l’écoulement.
- Quatorze points d’impact alimentent l’agitation, des fragments d’écume qui s’éloignent du jet et de nouvelles gouttelettes émises en continu. Les anciennes plaques de mousse et les grosses projections de particules au pied des cascades sont retirées. Les anciens plans verticaux des quatre jets centraux sont masqués au profit des jets en volume.
- Les vrais contours des pierres et des murs, extraits aux quatre hauteurs de bassin, localisent une agitation légère et irrégulière des reflets près des berges. La mousse permanente et l'oscillation régulière du maillage, refusées lors du premier essai, sont retirées. L'écume est réservée aux impacts et aux contacts en mouvement. Le traitement des berges ne masque plus les cascades aux hauteurs des bassins : leur continuité a été revérifiée sur les captures natives.

Le périmètre est le palais de Spargus. Le comportement de nage et la profondeur des bassins restent ceux du jeu : l’essai d’interaction réalisé ici porte sur les pieds dans l’eau et le déplacement dans une zone peu profonde. **La nage en eau profonde reste à vérifier dans une zone adaptée.** Les reflets montrent les objets disponibles dans l’image, avec une couleur d’environnement de secours pour le reste.

## Feu du palais

Le palais comporte aussi un premier remaster du feu : 24 volumes animés, plusieurs langues de feu, braises fines, fumée légère, chaleur, lumière locale et reflets approchés sur les ondulations de l'eau. Les anciennes couches de particules des foyers du palais sont désactivées. La base du feu est limitée à l'ouverture des vasques ; les neuf foyers sur pied sont calés sur leurs faces de charbon. Voir `desert-remaster/FEU.md` et `fire-v1/validation.json`. Le feu des autres zones reste à traiter.

## Lave de l’arène

Écoulement calculé dans le shader, plis, zones incandescentes, croûte rouge, bulles et léger mouvement vertical. La vitesse a été augmentée après le retour sur l’animation trop discrète. Halo local et légère distorsion de chaleur ; teinte chaude sur le décor proche.

Les grandes flammes du geyser 1931 sont remplacées par des projections de lave. La particule 1935 qui créait les plaques noires flottantes reste retirée. Le halo jaune du tutoriel est un effet original du jeu.

Le décor V1 conserve ses huit textures agrandies ×4 sur chaque axe, treize remplacements et sa première passe d’éclairage. Une refonte complète des ombres et de l’éclairage indirect ne fait pas partie de cette version.

## Vérification et sources

Voir `liquids-v3/validation.json`, les captures natives dans `profiles/v3-arena` et `profiles/remaster-palace`, et les journaux de lancement. Compilation C++ et GOAL exécutée ; les captures montrent le rendu réel. Les fichiers `contact-motion.gif`, `landing-motion.gif`, `fountains-motion.gif` et `shore-motion.gif` assemblent les captures de déplacement, de chute, de fontaines et de berges. La capture native signale aussi une erreur de tampon sur le moteur officiel, tout en produisant les PNG.

- `liquids-v3/fluids.glsl`, `fountain.*`, `water_spray.*`, `liquid_bloom.*` : matériaux et effets.
- `liquids-v3/apply_materials.py` : installe les shaders sur la base du décor V1.
- `liquids-v3/apply_water_contacts.py`, `replace_jak_water_effects.py`, `apply_fountains.py`, `apply_particles.py` : modifications GOAL et positions des effets.
- `liquids-v3/water_displacement.glsl` : déformation du maillage des bassins par les contacts de Jak.
- `shore-v4/build_shore_field.py` et `shoreline.glsl` : distances aux contours réels des berges et agitation locale des normales ; `palace-shore.bin` contient les quatre champs de distance.
- `engine-src/` : moteur modifié ; `liquids-v3/build_engine.py` : compilation MSVC 2019.
- `runtime/liquids-v3/gk.exe` : moteur du prototype ; manifeste dans `liquids-v3/runtime-manifest.json`.
- `liquids-v3/package.py` : conditionnement, sans modifier les références originale/V1 ni les routes de démarrage.

Pour reconstruire : appliquer les quatre scripts GOAL, puis `fire-v1/fit_sources.py` et `fire-v1/prepare.py`. Compiler GOAL avec `(mi)`. Après une modification de `water.gc`, exécuter `apply_boot.py --scene arena`, compiler avec `(mi)` et copier `data/out/jak3/iso/GAME.CGO` vers `routes/remaster/arena/GAME.CGO` ; répéter pour `palace`. Conserver les routes originales dans `routes/arena` et `routes/palace`. Générer le champ des berges avec `shore-v4/build_shore_field.py` s'il manque ou si la géométrie change. Appliquer les matériaux, construire le moteur, vérifier en jeu, puis exécuter `liquids-v3/package.py`, `liquids-v3/validate.py` et `fire-v1/validate.py`. Les anciens scripts de préparation initiale des variantes ne doivent pas être réexécutés pour une mise à jour.

## Suite du remaster

Le périmètre complet demandé est conservé dans `desert-remaster/DIRECTION.md` : désert, villes, terrains, végétation, architecture, marchés, montagnes, tempêtes, feu et éclairage, avec une identité fidèle à Jak 3. Le premier inventaire compte 3 427 occurrences de textures, soit 1 590 images distinctes après regroupement des doublons ; les catégories restent à vérifier visuellement. Les 24 foyers du palais disposent du premier rendu de feu décrit dans `desert-remaster/FEU.md`. Le remaster complet du désert reste à réaliser. La météo variable, le cycle jour/nuit, les nouvelles armes et la nage en ville sont documentés comme possibilités, sans activation supplémentaire dans ce prototype.
