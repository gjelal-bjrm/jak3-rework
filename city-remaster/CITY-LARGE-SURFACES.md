# Spargus : priorité aux grandes surfaces

Inventaire en lecture seule, calculé sur les GLB de fond originaux WCA/WCB.
La somme porte sur **les surfaces des triangles indexés en mètres carrés**, avec
les matrices de chaque nœud. Ce n'est pas un classement par nombre de triangles
ou par pixels visibles : les faces cachées et les surfaces superposées comptent.
Les 15 premiers matériaux représentent **77,6 %** de cette surface exportée.
Le JSON `city-large-surfaces-inventory.json` contient tous les résultats,
empreintes des sources, dimensions, alpha, moyennes RGB et usages natifs.

Références PNG originales :
`C:/Users/Gjelal/Documents/OpenGoal/active/jak3/data/decompiler_out/jak3/textures/<page>/<nom>.png`.
Dans le tableau, **A** = `wascitya`, **B** = `wascityb`, **T** = `-vis-tfrag`,
**S** = `-vis-shrub`, **P** = `-vis-pris`. Les pages sont des emplacements de
ressources : elles ne déterminent pas seules le type géométrique ou l'usage.

## Les 15 plus grandes surfaces

| Rang | Nom exact | Surface A+B, m² | Pages source | Taille | Usage et contrainte de fidélité |
|---:|---|---:|---|---|---|
| 1 | `wascity-ground-01` | 272 667 | A-T, B-T | 128×128 | Sol principal, 97 % horizontal. Terre/sable compact gris beige, petits agrégats. Conserver l'aspect continu ; pas de grandes dalles ni de dunes photographiques. |
| 2 | `wascity-ocean-shore-rocks` | 167 631 | B-T | 128×128 | Grandes parois rocheuses du littoral, 73 % vertical. Grès brun doré, grandes fractures verticales et lits horizontaux irréguliers. **Roche naturelle**, pas maçonnerie. |
| 3 | `wascity-stucco-wall-bleached-01` | 158 624 | A-T, B-T | 128×128 | Façades, 82 % vertical. Enduit clair gris légèrement verdâtre, écailles et usure. Garder le clair, la distribution des plaques et le contraste doux. |
| 4 | `city-slum-burning-can` | 101 959 | A-T, B-T | 64×64 | Nom trompeur : grandes pièces métalliques plates, 88 % horizontal, prototypes TIE arbre1 A/28 et B/42. Une instance A couvre environ35×46m pour1,56m de haut. Ne pas traiter cette texture comme un petit accessoire de feu. Conserver les bandes de tôle gris olive et les nervures. |
| 5 | `wascitya-stone-top` | 72 307 | A-S, A-T, B-S, B-T | 128×128 | Hauts de murs en enduit/pierre gris olive clair, 66 % vertical malgré le nom «top». Motif irrégulier continu ; ne pas remplacer par du pavage. |
| 6 | `wascity-ditch-wall-top-to-ground` | 70 225 | A-S, A-T, B-S, B-T | 256×128 | Murets et parois de rigole. Bande de grès ocre stratifiée entre transitions grises supérieure/inférieure. **Préserver les deux bordures et le ratio2:1** pour les raccords UV. |
| 7 | `wascity-stain-window-01` | 50 311 | A-S, B-S | 64×64 | Surimpression brune sombre sur façades, 84 % vertical, alpha0–101. La grande aire du quad ne correspond pas à une surface opaque. Préserver son masque ; ce n'est pas une vitre à rendre opaque. Priorité après les matériaux de base. |
| 8 | `wascity-stone-plain-wall-3` | 49 842 | A-T, B-T | 128×128 | Mur/enduit pierre beige olive, 75 % vertical. Craquelures et plages mates discrètes, sans nouveaux joints réguliers. |
| 9 | `wascity-ground2ocean-shore-rocks` | 43 429 | B-T | 128×64 | Transition sol→falaise côtière. Roche ocre sous une **bande claire supérieure**. Garder ce bord, la palette de la roche2 et le ratio2:1. |
| 10 | `wascity-outerwall-metal` | 37 782 | A-T, B-P | 128×128 | Grands panneaux du mur d'enceinte, 99 % vertical dans A. Tôle brun olive avec renforts diagonaux en X. Conserver emplacement, nombre et épaisseur visuelle des renforts. |
| 11 | `wascity-metal-dirty` | 35 523 | A-S, A-T, B-T | 64×32 | Métal structurel partagé, ferrures/plans verticaux et horizontaux. Gris olive usé, ratio2:1. Les supports remaster ont leur matériau dédié et ne dépendent plus de cette texture. |
| 12 | `wascity-outerwall-metal-b` | 34 454 | A-S, A-T, B-P, B-T | 64×128 | Pièces verticales/obliques du mur d'enceinte. Métal brun olive, ratio1:2 et placement des éléments structuraux à conserver. |
| 13 | `wascity-ground-2-ditch-04` | 31 250 | A-T, B-T | 128×128 | Sol de transition vers rigoles, 99,7 % horizontal. Doit être conçu avec `ground-01`, sans saut de teinte ou de taille du grain. |
| 14 | `wascitya-stone-bottom` | 27 870 | A-T, B-T | 128×128 | Bases de murs, 99 % vertical. Enduit olive supérieur avec **pierres de soubassement dans la partie basse** ; garder cette composition et les raccords au «top». |
| 15 | `wascity-roof-1` | 26 611 | A-S, A-T, B-T | 128×128 | Toits, 91 % horizontal. Tôle ondulée brun/vert sombre ; préserver les longues nervures et leur direction. |

Toutes ces textures sauf le rang7 ont un alpha constant **128**, convention
opaque native. Les variantes de pages de `stone-top`, `ditch-wall-top-to-ground`,
`outerwall-metal` et `roof-1` ne sont pas strictement identiques pixel par pixel,
mais les écarts moyens RGB mesurés restent inférieurs à1 unité par canal.
Les autres occurrences listées sont identiques pixel par pixel.

### Première livraison cohérente proposée

Traiter ensemble le **sol, l'enduit des façades et les falaises**, puis leurs
transitions. Cela touche les masses dominantes dans les vues de ville. Pour ne
pas laisser le chemin sous Jak ancien au milieu du nouveau décor, ajouter :

- `wascity-cement-road` — A-T/B-T, 64×64, 15 953m² ; route gris chaud.
- `wascity-ground-2-ditch-03` et `-05` — A-T/B-T,128×128,
  respectivement10 799 et15 584m² ; mêmes teintes et grain que le sol principal.
- `wascity-stucco-wall-bleached-2-bricks-01` — A-T/B-T,256×128,
  19 650m² ; raccord enduit/briques à conserver.
- `wascity-stone-bricks-2-plain` — A-T/B-T,128×128,15 472m² ; transition pierre.

Les PNG de référence principaux ont été inspectés. Une cible de2048px pour les
trois grandes matières, et1024px pour leurs variantes, donne un point de départ.
Conserver les ratios2:1 et1:2. Il faut de nouvelles structures de matière
lisibles, pas seulement du bruit fin ou une accentuation du flou original.
Les moyennes RGB source sont consignées pour contrôler les dérives : sol
**139/128/109**, roche côtière **161/123/81**, enduit clair **161/163/150**.
Ces valeurs décrivent l'image source ; l'éclairage et la palette native changent
encore sa couleur affichée dans le jeu.

## Import de textures sans réextraction

La voie existe déjà dans
`engine-src/tools/palace_mesh_bridge.cpp`, fonction `patch_level`, vers ligne328.
Elle remplace seulement `w`, `h` et `data` des textures existantes ayant le nom
exact demandé. Elle garde leur numéro, nom, page, combo_id et load_to_pool.

Exemple de manifeste à fabriquer **contre le FR3 courant installé**, après le
lot statique validé, et non contre un ancien extrait :

```json
{
  "level": "wascityb",
  "source_fr3": {"sha256": "SHA256_DU_FR3_COURANT", "bytes": 0},
  "preserve_bvh": true,
  "remove": [],
  "add": [],
  "textures": [
    {
      "name": "wascity-ground-01",
      "width": 2048,
      "height": 2048,
      "rgba_file": "CHEMIN_ABSOLU/ground-hd.rgba"
    }
  ]
}
```

`bytes` doit contenir la taille réelle du FR3 ; les valeurs ci-dessus sont des
repères de documentation. La commande existante est :

```text
palace_mesh_bridge.exe courant.fr3 textures.json staging-candidat.fr3
```

Les données sont des octets RGBA8 bruts. Pour ces matériaux opaques, garder
alpha128. Pour la salissure du rang7, conserver le masque original0–101, jamais
alpha128 uniforme. Les UV existantes sont normalisées pour les textures de
décor : la résolution supérieure ne demande pas de nouvelle topologie.

Avec `remove/add` vides, les arbres statiques et de vent ne sont ni dépliés ni
reconstruits par ce chemin. Aucune extraction DGO ou Merc n'est nécessaire.
Les modèles de marché et les plantes déjà remplacés restent dans le FR3.
Il faut ensuite recharger le niveau/jeu pour réuploader les nouveaux pixels.

### Contrôle concret de conservation

Réutiliser `compare_market.read_level` (Python Blender avec zstandard), sans
utiliser son CLI orienté remplacement Merc. Comparer avant/après :

1. `static_bytes` strictement identiques : TFRAG, TIE, shrub, vent, index textures,
   hfrag et collisions. `data[merc_start:]` strictement identique : tous les
   modèles, sommets, indices et paramètres Merc.
2. Même nombre et ordre de textures. Pour chaque entrée, `name/page/combo/pool`
   identiques. Les entrées hors liste autorisée restent totalement identiques.
3. Pour les entrées ciblées seulement, dimensions et hash RGBA égaux au matériau
   attendu. Vérifier les occurrences de même nom : le bridge sélectionne par
   **nom**, pas par page. Préparer un manifeste propre à chaque niveau où ce nom
   existe, sinon le bridge refuse le remplacement absent.
4. Garder les textures dédiées `market-*` ajoutées par les lots précédents
   identiques et conserver les variantes original/V1.

`audit_native_patch.py` ne peut pas être réutilisé tel quel comme verdict global :
il exige actuellement que **toutes** les anciennes textures restent identiques.
Cette règle est correcte pour les patchs de géométrie, mais rejetterait à juste
titre un changement de pixels. Utiliser les contrôles explicites ci-dessus,
puis enregistrer un descendant du FR3 courant et mettre à jour ses empreintes.
Ne pas lancer `terrain-v1/extract.py` pour cette passe : une extraction complète
risquerait de remplacer les géométries statiques déjà intégrées.

## Hors du classement

Le ciel et les nuages ne sont pas des surfaces WCA/WCB de cette liste. Les pages
sources de ces niveaux ne contiennent aucun nom sky/cloud. Il existe ailleurs
la page partagée `sky-textures`, et le code urbain utilise `*sky-work*` et
`set-cloud-and-fog-interp!` (`wasall-obs.gc`, lignes517–519). Les particules
`big-cloud`/`edge-cloud` de `level-default-sprite` servent aussi à d'autres effets :
ne pas les confondre automatiquement avec la couverture nuageuse du ciel.
Cette passe de matières ne modernisera donc pas, à elle seule, le ciel, les
silhouettes de montagnes, les formes des bâtiments ou l'éclairage.

Aucun matériau, modèle, FR3, DGO, shader ou fichier de déploiement n'a été
modifié par cet inventaire. Seuls ce document et son JSON de mesure sont créés.
