# Remaster fidèle du désert et de Spargus

## Demande retenue

Refaire l'ensemble du désert et de ses villes : sable, sols, pierres, montagnes, murs, maisons, planches, bois, plantes, marchés, places, accessoires, tempêtes et autres effets de l'environnement. Inclure le feu : torches, braseros, flammes, braises, fumée, chaleur et éclairage associé. Améliorer le réalisme des matériaux et de l'éclairage en conservant l'identité visuelle de Jak 3.

Chaque texture originale sert de référence. Conserver sa palette, ses motifs, ses grandes formes et l'organisation qui correspond au modèle 3D. Ajouter du grain, du relief, une usure cohérente et de meilleurs détails. Préserver la lisibilité et les silhouettes caractéristiques du jeu.

### Modèles et contraintes confirmées

**Consigne générale réaffirmée par l’utilisateur : chaque composant reconstruit doit être visiblement plus beau et mieux conçu que l’original.** Elle s’applique à tout le remaster, pas seulement au marché. Refaire à l’identique, ajouter seulement des polygones ou conserver les défauts n’est pas une livraison acceptable. Travailler la silhouette, la construction, les proportions secondaires, les raccords, les matériaux et les détails utiles. Corriger les défauts constatés, tout en conservant la personnalité animée, les teintes locales et les éléments reconnaissables de Jak 3. Comparer à distance de jeu et vérifier le fonctionnement avant de considérer un composant terminé.

Blender 5.2.2 LTS est installé et utilisable en ligne de commande. L'utilisateur demande explicitement de refaire les objets qui restent trop pauvres avec une simple texture : trône, récipients des flammes, vases, plantes et autres objets pertinents. Les fichiers Blender doivent être conservés, puis les modèles doivent être importés et vérifiés dans le moteur natif. Une image rendue dans Blender ne valide pas le résultat en jeu.

Conserver la teinte ocre des rochers : l'utilisateur a rejeté leur changement de couleur. Les vitres doivent rester transparentes et montrer le véritable extérieur, y compris la future météo. Les ouvertures et les surfaces de combustible des braseros doivent rester raccordées aux flammes déjà corrigées. Toute différence géométrique significative impose de revoir également les collisions et les limites de visibilité.

Conserver aussi la couleur originale de l'eau **selon chaque lieu**. À Spargus, viser le vert grisé naturel de référence, sans virer au bleu ni saturer le vert. Les vagues côtières originales qui déferlent ponctuellement sur les rochers font partie de l'identité de la ville : moderniser leur volume, leur retombée et leur écume tout en conservant leur caractère intermittent. Les quadrillages, les longues lignes régulières et la mousse permanente ont été rejetés.

## Ordre de travail

### Végétation réactive — règle demandée le 16 septembre

L'herbe et les touffes reconstruites doivent réagir au passage du personnage :
les brins s'écartent et se courbent légèrement, puis se redressent progressivement.
Garder les racines ancrées au sol et la souplesse propre à chaque plante. Ce
mouvement local complète le vent ; il ne doit ni bloquer la marche ni secouer
uniformément toutes les plantes. Prévoir la même logique pour les acteurs qui
traversent la végétation, avec un coût borné. Vérifier le passage, l'arrêt et le
retour au repos en jeu avant d'annoncer la fonctionnalité comme livrée.

L'utilisateur réaffirme la méthode pour les bâtiments : importer leur géométrie
native dans Blender, améliorer réellement les volumes et la construction, puis
réimporter et tester en jeu. Conserver les projets Blender et les ancres des
portes et collisions, en les adaptant explicitement si la nouvelle forme l'exige.

Priorité réaffirmée à la reprise du 16 septembre : avancer par grandes vues de
la ville (sols, murs, bâtiments, arbres, montagnes, rochers, ciel et nuages).
Reporter les petites finitions d'un accessoire isolé à la fin. Livrer des
changements visibles à distance de jeu et les vérifier ensemble dans le moteur.
La première passe globale WCA/WCB/WASWIDE est suivie dans
`../city-remaster/environment/README.md` : elle améliore les matières des
bâtiments mais ne constitue pas encore leur reconstruction géométrique.

Autorisation du 16 septembre : poursuivre après validation technique et visuelle de la salle vers la ville, l'arène, le désert puis ses véhicules sans redemander de feu vert. L'utilisateur rejette le premier passage de textures du palais : différence trop faible, rochers devenus trop proches de dalles, végétation toujours ancienne. L'eau et les flammes sont les acquis à conserver. La reprise doit apporter un changement net de relief, d'éclairage, de matériaux et de végétation à distance de jeu, tout en gardant l'univers animé de Jak.

### Ordre confirmé par l'utilisateur

1. **Salle du roi complète, de A à Z** : pierre, murs, sol, vitres, bois, métaux, accessoires, plantes et végétation, avec les liquides et le feu déjà modernisés. Terminer et vérifier l'ensemble de la salle avant d'étendre la passe ailleurs.
2. **Ville du désert** : même logique pour tous les matériaux, maisons, rues, marchés, places, décors et effets. Refaire aussi les modèles insuffisants : maisons, étals et leur contenu, fruits, cactus et plantes complètes.
3. **Arène et tout son contenu** : matériaux, architecture, accessoires et effets.
4. **Désert puis véhicules** : terrains, sable, montagnes, végétation, tempêtes et tout le contenu du désert ; ensuite matériaux et présentation des véhicules.

La première sélection de pierres du palais est enregistrée dans `terrain-v1/generation-manifest.json`. Elle est le début de la salle du roi, pas une passe annoncée comme complète.

### État et méthode

**Priorité utilisateur du 17 septembre : bâtiments avant herbe.** Une façade
refaite doit gagner des volumes et une finition visiblement meilleurs à distance
de jeu, en conservant l'identité et les teintes de Spargus. Ne pas présenter une
simple texture plus bruitée ou un maillage identique comme un remaster terminé.
Les hauteurs peuvent varier avec mesure ; certaines fenêtres donnent sur des
pièces meublées et habitées. La végétation et les petits détails attendent cette
étape. Le lot `city-remaster/city-block-v3` concerne deux maisons pilotes,
pas l'ensemble de la ville. Les personnages intérieurs sont des éléments de
décor animés issus des PNJ de Spargus, sans nouvelle IA d'interaction.

**État courant du lot de deux maisons : R3, quatre ouvertures dont une habitée.**
La fenêtre latérale de la première maison, son balconnet et sa pièce sont
supprimés pour conserver une seule ouverture habitée à cet étage. La façade
principale et l'ouverture supérieure restent ; les deux ouvertures de la
seconde maison ne changent pas. La toiture de cette seconde maison reçoit un
relèvement de 0,9 m et huit rebords de 0,98 m : c'est une modification modérée.
La [galerie courante](../city-remaster/city-block-v3/review-window-fix/index.html)
et son [registre natif](../city-remaster/city-block-v3/review-window-fix/native-review.json)
documentent ce périmètre. L'avant ordinaire est `geometry-002` avec les textures
précédentes, pas le jeu PS2 original ; la correction des fenêtres possède une
comparaison distincte avec la version rejetée. Les anciens rapports à cinq
ouvertures restent des traces historiques, sans être remplacés.

La deuxième passe de modèles du palais est intégrée et l'utilisateur juge maintenant la salle « plutôt pas mal ». Elle ajoute un trône avec moulures et reliefs, dossier capitonné et assise rembourrée ; 4 992 folioles, 180 pétioles, 46 couronnes, 51 plantes suspendues, 28 buissons et 12 628 feuilles de buissons/plantes suspendues. Les neuf vasques, 21 pots et 46 troncs arrondis sont conservés. Les captures natives `objects-v2-throne.png`, `objects-v2-palms.png` et `objects-v2-hanging.png` documentent le résultat. Voir `../models-v2/README.md` pour les fichiers, chiffres et limites. Le rocher d'essai Blender retiré lors du premier lot reste exclu. Cette acceptation du palais ne vaut pas audit complet de toutes les collisions, cinématiques ou performances.

La mer de Spargus possède une surface géométrique animée, une teinte régionale moins saturée et un filtrage des petites vagues. Le sillage et les remous des mains pendant la nage sur place ont été contrôlés en jeu, avec un véritable état de nage. Le fond marin reste à reprendre. L'utilisateur confirme que la séparation de l'horizon a disparu en V11. La V12 accélère l'impact des déferlantes et leur chute sous la gravité, sans palier au sommet ; les captures natives `coastal-v12-cycle` documentent ce réglage, dont le ressenti reste à confirmer. Le feu du palais est visible à travers l'eau sur les captures `palace-fire-clear-under-v8` et `palace-fire-above-v8`. Cela ne constitue pas une approbation de toutes les situations par l'utilisateur.

1. Finaliser les bassins : contacts de Jak, cascades continues, clapotis discret sur les berges. L'utilisateur a refusé la mousse permanente et l'oscillation régulière ajoutées autour des pierres.
   - Premier essai de feu intégré aux 24 torches et braseros du palais, près des bassins. Voir `FEU.md`. L'utilisateur a demandé davantage d'ampleur après l'essai initial, puis une correction du débordement à la base des vasques ; ces deux corrections sont intégrées.
2. Inventorier les ressources du désert et de Spargus, regrouper les doublons, identifier leur usage réel. `inventory.json` contient un premier inventaire ; les catégories sont provisoires et incluent des objets/personnages à trier.
3. Produire un ensemble cohérent pour les sols, le sable et les rochers, puis vérifier leur échelle, répétition, couleur et relief dans une zone jouable.
4. Étendre aux murs, maisons, marchés, bois, tissus, métaux et accessoires, puis à la végétation. Construire de nouveaux modèles de maisons et d'étals lorsque leurs volumes restent trop pauvres ; travailler aussi leur contenu, notamment les fruits exposés. Refaire les cactus et les plantes entières, avec tiges, branches, feuilles et couronnes : une nouvelle texture ou un tronc seul ne suffit pas. Préserver les silhouettes reconnaissables, les motifs et la palette de Jak tout en apportant davantage de volume et de détail. Vérifier la transparence des feuilles, les collisions et les objets partagés entre zones.
5. Traiter les montagnes, les vues lointaines, les transitions entre terrains, le sable porté par le vent et les tempêtes. Adapter les matériaux à l'éclairage des différents moments de la journée.
6. Vérifier chaque zone et transition du désert, la cohérence jour/nuit et les performances. Le remaster complet n'est pas encore réalisé ; les prototypes des liquides et du feu du palais, les modèles V2 et le premier traitement régional de la mer sont intégrés.

### Exigence de test : aucun son

Tous les prochains essais doivent être lancés sans son. Le lanceur du prototype transmet `OPENGOAL_TEST_MUTE=1` au moteur expérimental, qui efface la sortie audio, et met les volumes du profil de test à zéro. Vérifier le message `Prototype test audio: muted output; every stereo sample is cleared before playback` dans le journal du lancement concerné ; l'ancien paramètre `-nosound` seul n'avait pas suffi. Le réglage ne doit pas couper le son général de Windows. La désactivation du tentacule utilisée pour observer la nage concerne seulement la session de test en direct.

## Extensions demandées comme questions de faisabilité

### Ville habitée proposée par l'utilisateur

Conserver les silhouettes des immeubles et maisons, mais améliorer leur géométrie, leurs encadrements, leurs épaisseurs et leurs textures. Certaines fenêtres seulement pourront donner sur de petits intérieurs réellement en volume, avec du mobilier cohérent avec Jak et des habitants assis ou discutant. Prévoir plusieurs scènes et animations choisies de façon aléatoire mais stables pendant la visite, sans changement visible sous les yeux du joueur. Éclairage compatible avec le futur cycle jour/nuit. Adapter les détails et l'animation à la distance et vérifier le coût en jeu. Le lot courant `city-remaster/city-block-v3`, révision R3, conserve quatre ouvertures sur deux maisons pilotes, avec une seule ouverture habitée sur la première maison. Les variantes de pièces et leurs animations ont été observées dans le moteur natif ; elles ne sont pas visitables et ne constituent pas un système de vie pour toute la ville. La seconde pièce habitée du lot initial est supprimée avec sa fenêtre latérale ; les preuves de cet ancien état restent conservées.

- **Météo variable :** le code dispose déjà d'effets de pluie, de neige et de tempêtes de sable. Un système cohérent demanderait une gestion des transitions, des nuages, du vent, des abris, des surfaces mouillées et des impacts sur l'eau. La grêle et l'accumulation de neige nécessiteraient du travail supplémentaire. Garder les événements compatibles avec l'ambiance des zones.
- **Jour/nuit :** le système existe déjà dans `time-of-day.gc`. Le prototype fixe volontairement l'heure à 09:00 pour les comparaisons. On peut rétablir et améliorer son évolution, puis travailler les éclairages nocturnes.
- **Nouvelles armes :** techniquement envisageable via le code des armes ; prévoir comportement, projectiles, modèle, animations, sons, interface, sauvegarde et équilibrage. Rien de nouveau n'a été ajouté à ce stade.
- **Nage en ville :** la mécanique de nage existe. La nage à la surface de la mer de Spargus a maintenant été testée avec sillage et remous des mains. Cela n'active pas la nage dans tous les bassins urbains : leurs volumes, profondeur, collisions, règles de mort et sorties doivent encore être contrôlés. L'intérieur de la mer a reçu un premier traitement visuel, sans remaster complet du fond marin.

Ces extensions restent des possibilités discutées, pas des fonctionnalités déjà livrées.
