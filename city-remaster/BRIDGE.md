# Export natif d’un bloc de ville

`python city-remaster/export_block.py` exporte le bloc du marché WCB dans
`city-remaster/market-block-native.json`. Il ne modifie aucun fichier du jeu.
Le bridge doit être compilé au préalable avec `models-v1/build_bridge.py` ;
ne pas le compiler en parallèle du moteur dans le même dossier de build.

L’appel natif est :

```text
palace_mesh_bridge --export-selected input.fr3 selection.json export.json
```

Les anciens appels d’export palace et d’application de patch restent disponibles.
Le nouveau mode accepte ces filtres optionnels, combinés par intersection :

- `level` : nom exact du niveau attendu.
- `source_fr3.sha256` et `source_fr3.bytes` : identité du FR3 compressé.
  Une différence bloque l’export avant toute écriture. `source_fr3.path` est
  utilisé par le script Python ; le bridge reçoit son entrée sur la commande.
- `materials` : liste de noms exacts ; aucune sélection par numéro de texture.
- `tree_types` : parmi `tfrag`, `tie`, `shrub`, `tie_wind`.
- `geoms` : indices de géométrie/LOD ; les shrubs utilisent `0`.
- `trees` : liste d’objets avec `tree_type`, `tree` et éventuellement `geom`.
  Un `geom` omis accepte les LOD de cet arbre. Les numéros d’arbres sont locaux
  à leur type et à leur LOD ; un numéro de prototype seul n’identifie pas un objet.
- `instances` : liste d’objets avec `tree_type`, `tree`, `instance` et
  éventuellement `geom`. Retirer les bornes spatiales et sélectionner les
  instances permet d’exporter les objets entiers.
- `bounds_xz_m` : `[xmin,xmax,zmin,zmax]`, en mètres dans le monde.

Un filtre absent accepte toutes ses valeurs ; une liste vide n’en accepte aucune.
Les bornes retiennent les triangles entiers dont la boîte XZ croise le rectangle,
y compris ceux dont les trois sommets sont dehors. Cette sélection conservative
peut inclure un triangle passant près d’un coin ; elle ne découpe aucun triangle.

Les faces conservent les indices natifs `tree_type/geom/tree/draw/stream_index`,
le groupe, le prototype, l’instance, les positions, UV et couleurs. Les indices
ne sont jamais compactés après filtrage. `draw_inventory` indique les groupes
retenus et leurs nombres de triangles d’origine et de triangles sélectionnés.

Le premier manifeste couvre X 1735–1820, Z −355–−290 et conserve tous les LOD.
Il sélectionne sols, murs, rochers et végétation statique. Les étals, paniers,
fruits et autres acteurs Merc nécessitent leur propre remplacement de modèle :
ils ne sont pas contenus dans cet export de géométrie statique.

## Vérification

`python city-remaster/verify_bridge.py` : 35 contrôles réussis, dont les trois
exports palace identiques octet par octet, la conservation des clés et attributs
natifs, les sélections TFRAG/TIE/SHRUB et le refus d’un niveau ou hash incorrect.
Le rapport est dans `bridge-validation/validation.json`.
Le bloc exporté contient 26 750 triangles, tous LOD confondus.

## Palmes et vent

Les palmes et les barbes sont dans `TieTree::instanced_wind_draws`, un flux
distinct des troncs statiques. Leur absence du premier export ne prouve donc
pas qu’elles sont hors du rectangle. Le type explicite `tie_wind` exporte ces
faces avec des clés distinctes, leurs positions monde `p`, leurs positions
locales `local_p` et une `instance_inventory` donnant matrice, origine et vent.
`matrix_columns` utilise une translation en mètres ; le reste de la matrice
garde ses coefficients natifs. Le prototype de vent est `-1` car le FR3 ne
stocke pas cette correspondance ; aucun numéro de prototype n’est inventé.

Le patcher traite désormais explicitement `tie_wind` et conserve les matrices,
paramètres de vent et groupes de visibilité natifs. L’export fournit aussi les
normales locales et monde. Le schéma d’import et de textures dédiées ainsi que
l’audit avant/après sont décrits dans `WIND-PATCH.md`. Les anciens exports palace
gardent exactement leur comportement ; `tie` et `tie_wind` restent distincts.
