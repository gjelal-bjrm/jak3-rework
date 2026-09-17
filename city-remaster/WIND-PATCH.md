# Import natif des plantes et textures isolées

Le bridge applique maintenant `tie`, `tie_wind` et `shrub` sans changer le
runtime. Les faces `tie_wind` restent dans les draws animés natifs ; elles ne
sont jamais converties en TIE statique. Ce document décrit un patch hors ligne.

## Contrat JSON

```json
{
  "level": "wascityb",
  "source_fr3": {"sha256": "HASH_DU_FR3_COMPRESSE", "bytes": 36575263},
  "preserve_bvh": true,
  "new_textures": [{
    "name": "market-palm-leaf-v1",
    "page": "remaster-market-plants",
    "width": 1024,
    "height": 1024,
    "rgba_file": "C:/chemin/leaf-tissue.rgba"
  }],
  "remove": [{
    "tree_type": "tie_wind", "geom": 0, "tree": 1,
    "draw": 0, "group": 0, "instance": 0, "stream_index": 2,
    "original_positions": [[0,0,0], [1,0,0], [0,1,0]]
  }],
  "add": [{
    "tree_type": "tie_wind", "geom": 0, "tree": 1,
    "draw": 0, "group": 0, "instance": 0,
    "texture": "market-palm-leaf-v1",
    "vertices": [
      {"p":[0,0,0], "normal":[0,0,1], "uv":[0,0], "color_indices":[1,2,3], "color_weights":[1,0,0]},
      {"p":[1,0,0], "normal":[0,0,1], "uv":[1,0], "color_indices":[1,2,3], "color_weights":[0,1,0]},
      {"p":[0,1,0], "normal":[0,0,1], "uv":[0,1], "color_indices":[1,2,3], "color_weights":[0,0,1]}
    ]
  }]
}
```

Les valeurs d’exemple doivent être remplacées par les clés et coordonnées de
l’export natif exact. Le hash est obligatoire pour un patch de vent. Les clés
`draw/group/instance` appartiennent au niveau **avant** patch, avec des espaces
distincts pour `tie` et `tie_wind`.

- `p` et `normal` sont en espace monde ; les positions sont en mètres et les
  normales unitaires. Le bridge utilise `inverse(M)` pour la position et
  `transpose(M)` pour la normale vers l’espace local de l’instance animée.
  Les normales locales sont quantifiées en signed 8 bits, comme les TIE natifs.
- `uv` garde les unités natives : TIE/TIE_WIND inchangées, SHRUB généralement
  0–4096. Le bridge n’effectue aucune conversion UV liée à la nouvelle texture.
- `color_indices` réfère à la table de l’arbre, pas seulement au draw. Les trois
  poids interpolent les huit palettes horaires. Au plafond natif de 8 192
  couleurs, le coin source le plus proche est réutilisé ; aucune ancienne
  couleur active n’est réécrite. Le chemin SHRUB garde le coin de poids maximal.
- `rgba` facultatif des sommets SHRUB conserve les couleurs natives (défaut 128).
- `texture` facultatif d’une face `add` nomme une texture du niveau ou de
  `new_textures`. Sans lui, la face hérite du matériau source.
- Les pixels sont du RGBA8 brut, sans conversion gamma ou alpha. Une texture
  de même nom déjà présente doit avoir exactement les mêmes dimensions/pixels.
  Les nouvelles textures restent locales au niveau (`load_to_pool=false`).
- Ne pas utiliser l’ancien champ `textures` pour isoler une instance : ce champ
  remplace les atlas existants globalement et garde son sens historique.

## Conservation des instances

Pour le vent, le segment d’indices ciblé est rempli de codes de redémarrage,
à longueur constante. Le bridge ajoute des draws contenant les faces retenues
et ajoutées, avec les mêmes `instance_idx`, `vis_idx`, mode et matrice native.
Les segments, offsets, groupes et données des autres instances restent intacts.
La position de repos et l’animation utilisent donc le même repère local.

Pour les TIE statiques, les nouveaux draws de texture sont insérés dans la
catégorie du draw source. Les débuts des catégories suivantes sont mis à jour.
Les vis_groups/prototypes sont conservés ; les nouvelles positions sont stockées
en monde comme dans le bridge palace. Les identifiants de draw peuvent changer
après import. Pour les SHRUB, les draws dédiés sont ajoutés à la fin.

`preserve_bvh:true` conserve les bornes natives à l’octet près. Les modèles
doivent rester dans l’empreinte sélectionnée ; aucun agrandissement automatique
du BVH n’est effectué dans ce mode.

## Commandes hors ligne

```text
palace_mesh_bridge source.fr3 patch.json candidate.fr3
python city-remaster/audit_native_patch.py --before source.fr3 --after candidate.fr3 --patch patch.json --report preservation.json
```

L’audit exige que les anciens pixels, Merc complet, collision, hfrag, TFRAG,
matrices, vent, palettes et préfixes de buffers restent identiques. Il compare
aussi **chaque triangle non sélectionné** avec son winding, matériau, groupe de
visibilité, prototype/catégorie et instance de vent. Les triangles ajoutés et
supprimés doivent correspondre exactement aux nombres du patch.

Le rapport fournit `status`, `checks`, `before_sha256`, `after_sha256`,
`patch_sha256` et l’identité du rapport natif détaillé. Il ne valide pas la
beauté, les performances, le raccord des collisions ni l’animation en jeu.

`verify_wind_bridge.py`, exécuté avec le Python de Blender (module zstandard),
passe **187 contrôles** : noop identique octet par octet, refus d’un hash/instance/
triangle source erroné, textures isolées des trois types, géométrie et normales
après matrice anisotrope, données des voisins conservées.

Le lot technique `staging/market-static-001` passe 163 vérifications : 17 014
faces retirées, 424 292 ajoutées et 584 320 faces non sélectionnées conservées.
Ce lot est historique et **n’est pas à déployer** : les pieds des supports font
l’objet d’un lot suivant. L’audit doit être relancé sur ce nouveau candidat.

## Repère d’éclairage des nouvelles palmes

`market-palm-leaf-v1` active seul `market_wind_material`. `Tie3` conserve la
matrice native après `do_wind_math` et la fournit par instance au vertex shader.
Les sorties d’éclairage utilisent cette matrice en monde et son inverse-transposée
pour les normales ; la projection, le vent et les anciens matériaux sont inchangés.
Les textures privées `market-palm-trunk-v1`, `market-support-wood-v1` et
`market-support-metal-v1` utilisent `GL_REPEAT`, conformément aux UV répétées
de leur auteur. Les feuilles, buissons et atlas natifs gardent leur mode initial.

`apply_market_wind_frame.py` conserve les hashes avant/après ; `--undo` refuse
tout fichier modifié depuis l’application. `verify_market_wind_frame.py` vérifie
l’inverse en mémoire, la projection identique et le repère de 7 392 sommets dans
56 instances/LOD (écart maximal 0,063 mm), ainsi que les normales sous échelle
anisotrope et cisaillement. Rapport : `wind-material-frame-validation.json`.
Cette vérification ne remplace pas l’examen visuel dans le moteur.
