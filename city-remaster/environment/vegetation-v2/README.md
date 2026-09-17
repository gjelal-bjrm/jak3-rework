# Végétation de rue — modèles complets V2

Ce lot reconstruit toutes les touffes d'origine et tous les petits cactus fleuris des deux quartiers. Les palmiers déjà acceptés et les 69 touffes du marché restent exclus par sélection exacte des anciennes matières. Aucun fichier du jeu installé n'est modifié par les scripts de ce dossier.

## Périmètre

| Quartier | Touffes | Cactus | Triangles d'origine retirés | Nouveaux triangles |
|---|---:|---:|---:|---:|
| Wascitya | 789 | 18 | 34 086 | 1 177 722 |
| Wascityb | 693 | 7 | 27 930 | 960 792 |
| Total | 1 482 | 25 | 62 016 | 2 138 514 |

Chaque touffe possède 21 brins fermés, courbés, d'épaisseur réelle, en trois groupes de hauteur irrégulière. Les directions et proportions varient selon l'instance. Chaque cactus devient une composition de sept coussins arrondis et nervurés, avec épines et fleurs aux pétales incurvés en volume. Il ne s'agit pas d'une subdivision du maillage ancien.

Les matrices et racines natives sont conservées. Un ajustement doux de la seule partie basse maintient exactement le point de contact inférieur d'origine, y compris pour les instances inclinées. Les collisions et structures spatiales ne sont pas remplacées (`preserve_bvh=true`).

## Animation et contact avec Jak

- Matière de toutes les herbes souples : `market-shrub-orange-v1`, identique à celle des 69 touffes du marché.
- UV natives : **V=4096 à la racine ; V=0 à la pointe**. Cette progression monotone fournit la pondération de flexion. Les pieds doivent rester immobiles ; le sommet s'écarte puis revient doucement après le passage. La mise en œuvre shader est le lot séparé de l'agent `fire_through_water`.
- Les rapports conservent `origin_m` et `matrix_columns` de chaque instance.
- Les cactus utilisent `city-cactus-green-v2` et la texture de fleurs native ; ils sont exclus de cette flexion souple.

## Sources et intégration

Les patches `wascitya-patch.json` et `wascityb-patch.json` partent du même état immuable ENV que les façades et fenêtres : `city-remaster/environment/staging/city-environment-001/{level}.fr3`. Les SHA et tailles exacts sont dans `source_fr3` du patch et du rapport. Ne pas les appliquer successivement à un état devenu différent : les fusionner par niveau avec les deux autres lots, vérifier l'unicité des identités de retrait, puis appliquer une seule fois au niveau ENV correspondant.

Les nouvelles textures sont déclarées dans `new_textures`. Le nom `market-shrub-orange-v1` doit être réutilisé si déjà présent avec les mêmes octets, notamment dans WCB. `city-cactus-green-v2` est dédié à ces seuls nouveaux cactus. Les pixels source/global atlas restent intacts. RGBA8, alpha natif 128 constant. `texture-provenance.json` documente la génération et la correction de palette ; aucune retouche raster par script n'est effectuée.

Les JSON sont volumineux : l'auteur et le validateur lisent/écrivent les additions en flux. `validate.patch_rows(path)` livre d'abord le petit en-tête puis les triangles, sans charger le lot entier en mémoire.

## Reproduction et vérification

```
blender --background --python city-remaster/environment/vegetation-v2/author.py
<BlenderPython> city-remaster/environment/vegetation-v2/validate.py
```

Le validateur compare les retraits exacts, racines, matrices, indices de palette, positions/UV, volumes fermés et orientation, y compris après conversion float32 native. Il vérifie aussi dimensions, alpha et empreintes des textures. Les rapports détaillés portent le suffixe `-validation.json`.

Les `.blend` et les aperçus sont des fichiers d'auteur. **Ils ne constituent pas une validation du rendu natif ni des performances.** L'intégration doit encore passer l'audit FR3 de préservation des géométries étrangères/Merc et une observation en jeu des quartiers chargés.
