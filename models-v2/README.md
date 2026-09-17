# Palais V2 et mer de Spargus

La deuxième passe du palais est intégrée au niveau natif `waspala.fr3`. L'utilisateur juge désormais la salle « plutôt pas mal ». Cette étape conserve l'identité et les couleurs de Jak 3 ; elle ne termine pas le remaster du désert.

## Objets intégrés

- Trône : trois moulures en volume, quinze rayons de bronze en relief, dossier capitonné, assise rembourrée, six attaches d'accoudoirs et pieds reconstruits. Source : `throne-v2.blend`.
- Végétation : 4 992 folioles de palmier, 180 pétioles, 46 couronnes, 51 plantes suspendues, 28 buissons et 12 628 feuilles de plantes suspendues/buissons. Sources : `palm-v2.blend`, `hanging-v2.blend`, `author.py` et `foliage-patch.json`.
- Les 46 troncs arrondis, 21 pots et neuf vasques de braseros de la première passe sont conservés. Les 288 faces de combustible gardent exactement leurs coordonnées pour préserver l'ancrage des flammes.
- Le tissu foliaire est une texture 1 024 × 1 024 ; la géométrie fournit la silhouette des feuilles. Son origine et son prompt sont consignés dans `generation.json`.

Le rapport `../models-v1/native-model-validation.json` compte 84 206 triangles remplacés et 1 867 056 triangles ajoutés, **en additionnant tous les niveaux de détail**. Ces chiffres ne sont pas le nombre de triangles affichés à chaque image. Aucun remplacement ne se chevauche. Les captures natives `objects-v2-throne.png`, `objects-v2-palms.png` et `objects-v2-hanging.png` sont dans `../profiles/remaster-palace/OpenGOAL/jak3/screenshots/`.

## Mer : V12, dynamique de déferlement corrigée

La mer de Spargus utilise une surface géométrique animée, avec une hauteur et des normales dérivées de la même houle. Le filtrage selon la distance et la déformation des trains de vagues réduisent les lignes régulières. La teinte reste un vert grisé propre à Spargus ; les autres régions doivent conserver leurs couleurs locales.

Le prototype ajoute réfraction, reflets utilisant l'image de la scène, traitement sous l'eau et embruns côtiers. Les contacts du corps produisent un sillage quand Jak avance. Les mains utilisent désormais deux historiques de mouvement indépendants : leurs remous continuent quand Jak nage sur place, sans exiger un déplacement du corps. L'horodatage des mains est séparé de celui du corps pour préserver les sillages et les effets d'entrée dans l'eau.

Les captures V6 `ocean-v6-idle-a.png` et `ocean-v6-idle-b.png`, prises à X = 1 678,8383 m, Z = −421,9312 m, montraient des anneaux, mais cette position était trop peu profonde : ce premier test ne suffisait pas à établir le comportement de la nage sur place. Le contrôle natif suivant utilise le point profond (1 647, 6,9717, −430) m ; l'état GOAL `target-swim-stance` y est confirmé et des anneaux sont visibles autour de Jak. Cette observation ne constitue pas une approbation finale de l'utilisateur. `ocean-v6-underwater.png` contrôle l'atténuation verte sous la surface ; le fond marin et l'ensemble de l'environnement sous-marin ne sont pas remasterisés.

Les vagues qui déferlent ponctuellement sur les rochers doivent conserver le rythme et le caractère de celles du jeu original. Leur modernisation est en cours : ne pas les remplacer par une brume permanente ou un quadrillage d'écume. Les reflets actuels dépendent de ce qui est visible à l'écran ; ce ne sont pas des réflexions complètes de toute la scène.

## Feu vu à travers l'eau du palais

Le feu est désormais dessiné après les surfaces opaques et avant les passes d'eau. Il figure ainsi dans l'image utilisée pour la réfraction, et le bassin ne masque plus le volume comme un objet opaque. La capture native `palace-fire-clear-under-v7.png` montre la flamme entière depuis le bassin. Le premier angle de contrôle était masqué par une marche ; la caméra dégagée (2 056,348, 241,1, −439,520) m vise (2 068,348, 246,795, −439,520) m.

Le correctif complémentaire de `../liquids-v3/fluids.glsl` oriente la normale vers la caméra uniquement sous la surface et calcule l'absorption sur le trajet immergé caméra → surface. Il conserve les expressions utilisées depuis l'extérieur. Les deux insertions sont appliquées à Generic, Merc et Tfrag par `../liquids-v3/apply_underwater.py`, sans reconstruire les autres matériaux. Leurs empreintes figurent dans `../liquids-v3/underwater-fix.json`. La capture native **`palace-fire-clear-under-v8.png` montre la flamme entière et nettement lumineuse à travers l'eau** ; `palace-fire-above-v8.png` contrôle le rendu extérieur conservé. Ce contrôle ciblé ne constitue pas un audit de tous les angles du palais ni une réfraction physique complète selon la loi de Snell.

L'activation est encore limitée par une zone de coordonnées autour de Spargus et une hauteur de mer de neuf mètres. Ce réglage local n'est pas un système d'eau universel. Le tentacule a été désactivé uniquement dans la session de test en direct, pour observer la nage ; ce changement ne fait pas partie du contenu distribué.

## Tests silencieux

`../launch.py` transmet `OPENGOAL_TEST_MUTE=1` au processus du prototype. Le moteur expérimental met son flux audio à zéro et efface les échantillons avant lecture ; les volumes du profil de test sont aussi mis à zéro. Le journal doit contenir `Prototype test audio: muted output; every stereo sample is cleared before playback`. Le réglage concerne le prototype, pas le volume général de Windows. Le moteur officiel des variantes de comparaison ne possède pas ce correctif C++ : leurs profils sont mis à zéro par le lanceur.

## Reconstruction et contrôle

`../models-v1/model-set.json` sélectionne les patches V2. `../models-v1/apply_models.py` vérifie les remplacements et produit le FR3 natif. `../terrain-v1/extract.py` réapplique ce lot après extraction. Ne pas compiler l'importeur et le moteur simultanément : ils partagent le répertoire de compilation.

`apply_ocean.py` génère les shaders de mer ; `apply_ocean_contacts.py` relie les contacts GOAL au moteur. Après compilation et conditionnement par `../liquids-v3/package.py`, lancer le prototype puis exécuter depuis sa racine :

```powershell
python models-v2/verify_package.py
```

Le vérificateur contrôle les empreintes de toutes les variantes déclarées, les fichiers déployés, le moteur, les routes de démarrage et les patches natifs. Il compare les effets du palais et les DGO à `../variants/remaster-before-objects`, en autorisant les changements du niveau et des shaders des modèles. Generic et Merc restent dans la liste protégée : seules les deux insertions documentées pour le dessous de l'eau sont admises, et leur annulation exacte doit restituer intégralement le shader de référence, après normalisation des fins de ligne CRLF/LF. Le rapport distingue les fichiers identiques des fichiers préservés sauf ce correctif borné ; il contrôle également les sept empreintes du manifeste du correctif. Les nouveaux shaders de mer sont identifiés séparément. Tout futur correctif de shader du feu devra recevoir une comparaison explicite. Le rapport `package-validation.json` signale aussi le chemin audio muet dans le journal ; il ne remplace ni une écoute instrumentée ni une validation visuelle.

Le contrôle courant, après la mer V12 et le lot de marché 004, passe : **272 vérifications, 45 fichiers pour chacune des trois variantes**. Generic et Merc sont préservés sauf les deux insertions sous-marines précisément contrôlées. Les FR3 WCA/WCB conservent intégralement leurs données statiques et les modèles non sélectionnés. Dans WWD, seul le contrôleur `ctymark-obs` des fruits change ; les 65 autres occurrences d'objets sont identiques. Voir `../city-remaster/README.md` pour les captures natives et les limites des tests du marché. L'identité des fichiers ne prouve pas à elle seule l'absence d'une régression liée à l'ordre de rendu C++.

Les collisions d'origine sont conservées. La fluidité globale, toutes les collisions et les cinématiques n'ont pas fait l'objet d'un audit complet. Les captures natives peuvent produire un avertissement OpenGL 0x502 malgré des PNG valides. L'ordre de travail autorisé demeure : palais, ville, arène, désert, véhicules. La suite en ville comprend aussi de nouveaux modèles pour les maisons, les étals et leur contenu, dont les fruits, ainsi que les cactus et les plantes complètes ; voir `../desert-remaster/DIRECTION.md`. La météo, les nouvelles armes et une extension générale de la nage ne sont pas implémentées par ce lot.
