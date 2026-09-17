# Palmiers complets du marché WCB

Auteur Blender local pour les troncs `tie/tree-1/486` et `487`, leurs six
composants de palmes `tie_wind/0..5` et leurs huit jupes `tie_wind/45..52`.
Les 64 groupes composant/LOD sont explicitement reconstruits. Les buissons,
les autres palmiers et leurs atlas partagés ne sont pas concernés.

## Modélisation

- Deux troncs à section arrondie suivant les neuf anneaux et la courbe natifs,
  avec renflements de racines, petites nervures et 496 cicatrices d'écorce en
  volume au total au LOD 0.
- Douze rachis arqués suivant l'enveloppe des six composants natifs, avec
  **600 folioles distinctes** galbées et plissées. Les bases des palmes se
  prolongent sous leur ancre pour rejoindre le tronc, y compris au repos.
- **184 frondes sèches distinctes** remplacent les rideaux de barbe. Leur
  texture native est conservée dans de petites fenêtres UV ; aucun atlas
  partagé n'est remplacé par une image opaque.
- Quatre niveaux de détail : 24 520 / 15 568 / 7 176 / 2 996 triangles pour
  l'ensemble des deux palmiers, contre 1 088 triangles natifs au LOD 0.

## Fichiers

- `author.py` : source de modélisation reproductible.
- `market-palms.blend` : toutes les pièces et tous les LOD, LOD 0 visible.
- `palms-complete.png`, `palms-crowns.png` : inspections Blender. Ce sont des
  rendus de travail, **pas des captures du jeu** ; ils n'utilisent pas encore
  la palette d'éclairage dynamique native ni le shader du jeu.
- `palms-patch.json` : retrait des 3 136 triangles natifs sélectionnés et ajout
  des nouvelles faces ; positions/normales **monde Y vers le haut, en mètres**.
- `palms-report.json` : compte des pièces, matrices, ancrages, indices et
  paramètres du vent ; hash de l'export natif utilisé.
- `validate.py`, `validation.json` : contrôle indépendant des références,
  positions de retrait, LOD, textures, normales et poids de couleurs.

Les records `tie_wind` contiennent `instance` en plus de `tree_type`, `geom`,
`tree`, `draw` et `group`. Le bridge doit conserver les matrices, `wind_index`,
`stiffness` et la visibilité natifs. Il convertit les positions par l'inverse
de la matrice et les normales par sa transposée (échelles non uniformes).
Aucune animation `palace_foliage` ne doit être ajoutée : seul le vent natif
anime les couronnes.

## Textures dédiées et provenance

`new_textures` ajoute deux matériaux seulement aux faces reconstruites :

- `market-palm-leaf-v1`, page `remaster-market-plants`, 1024² : réutilisation
  exacte de `models-v2/leaf-tissue-1024.png` / `leaf-tissue.rgba`, déjà créé
  pour la végétation du palais.
- `market-palm-trunk-v1`, même page, 887 × 1774 : réutilisation exacte des
  pixels RGB de `terrain-v1/masters/waspala-palmtree-trunk-01.png`. Le fichier
  `trunk-tissue.rgba` ajoute seulement un canal opaque pour l'encodage natif ;
  aucune retouche, recoloration ou génération d'image supplémentaire.

Le matériau de barbe reste `wascity-palm-beard`. Il ne reçoit aucune mutation
globale. Les UV et normales des nouvelles surfaces sont réellement calculés ;
les couleurs d'éclairage sont interpolées dans la palette du composant natif.

## Régénération et limite

Depuis la racine du prototype :

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python 'city-remaster/palms/author.py'
python 'city-remaster/palms/validate.py'
```

Aucun FR3, DGO, runtime ou fichier de variante n'est modifié par ces scripts.
L'import sur une copie de WCB, le retour d'export, la vérification du vent,
du rendu des deux faces des folioles et de la visibilité à distance doivent
encore être vérifiés dans le moteur avant livraison au joueur.
