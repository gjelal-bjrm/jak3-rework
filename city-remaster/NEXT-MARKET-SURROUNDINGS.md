# Suite du marché : terrain central, puis façades voisines

Repérage en lecture seule du 16 septembre 2026. Aucun modèle, texture, mesh,
FR3 ou fichier de variante modifié. Seul ce document est créé.

## Décision proposée : finir le terrain autour de l'étal 42091

Le prochain petit lot cohérent est le **sol, la rocaille et les bordures autour
des deux palmiers**, derrière l'étal **AID 42091**, placé à
`(1759.816, 30.225, -328.562)` m. Rectangle de recherche :
**X 1752–1785, Z −349 à −314**, `wascityb`/WCB. Les objets qui croisent ce
rectangle doivent être sélectionnés en entier ; certaines extrémités dépassent
jusqu'à Z −352,8 et −311,2. Ce lot donne un environnement cohérent aux objets
du marché déjà reconstruits avant de commencer le reste de la ville.

Il ne contient pas de porte animée identifiée. Les premiers bâtiments documentés
se trouvent plus loin, sur la bordure nord-est de la place. Cela évite de lancer
une façade isolée pendant que la majeure partie du sol visible reste ancienne.

## 1. Lot terrain central : identifiants directement utilisables

Tous les TIE ci-dessous : **arbre 1**, instances entières, géométries/LOD
`0,1,2,3`. Le numéro de prototype seul n'identifie jamais un objet.
Les coordonnées sont celles des sommets indexés dans l'export source, en mètres.

| Ensemble | Instance / prototype | Triangles LOD 0/1/2/3 | Matériaux et dessins LOD 0 | Emprise proche X / Z |
|---|---|---|---|---|
| Bordure/muret près du pied des palmiers | **212 / 7** | 32 / 32 / 32 / 8 | `wascity-ditch-wall-top-to-ground`, draw20/group72 ; `wascity-ground-2-ditch-05`, draw28/group59 | 1766,54–1775,26 / −340,71 à −328,69 |
| Roche basse vers l'avant du marché | **272 / 8** | 144 / 144 / 144 / 60 | `wascity-rock-small`, draws29 et30/group11 | 1755,83–1765,83 / −349,43 à −340,47 |
| Grand raccord terrain/rocaille central | **330 / 10** | 160 / 160 / 160 / 40 | `...ditch-wall-top-to-ground` d20/g101 ; `...ground-2-ditch-04` d22/g52 ; `...ground-01` d24/g1 ; `...ground-2-ditch-03` d27/g52 ; `...ground-2-ditch-05` d28/g88 | 1753,68–1784,74 / −352,76 à −328,21 |
| Segment de passage devant l'étal central | **581 / 22** | 120 / 120 / 120 / 50 | `wascity-cement-road`, draw41/group16 | 1752,31–1765,38 / −325,55 à −314,94 |
| Segment de passage sud-est | **624 / 23** | 64 / 64 / 64 / 30 | `wascity-cement-road`, draw41/group44 | 1773,92–1785,15 / −335,86 à −326,68 |
| Segment de passage nord-est | **626 / 23** | 64 / 64 / 64 / 30 | `wascity-cement-road`, draw41/group45 | 1765,98–1774,75 / −322,28 à −311,22 |

Ces six instances représentent **584 triangles proches** avant remodélisation.
Leurs matériaux de transition appartiennent au même objet : remplacer seulement
la surface rocheuse ou seulement le dessus laisserait des coutures visibles.

### Sol continu TFRAG

La recherche dans le rectangle ci-dessus retient **92 triangles entiers au
LOD 0**, arbre `tfrag/0`. Il faut conserver tous leurs bords avec le terrain
extérieur, puis exporter également les LOD 1 et 2. Les indices suivants sont
des repères du snapshot d'origine, à confirmer contre le FR3 courant :

| Matériau | Draw / group | Faces retenues | `stream_index` LOD 0 |
|---|---|---:|---|
| `wascity-ground-01` | 13 / 14 | 4 | 2114, 2115, 2121, 2122 |
| même matériau | 13 / 15 | 16 | 2212–2215, 2219–2222, 2254–2257, 2261–2264 |
| même matériau | 13 / 28 | 60 | 3612–3615, 3619–3622, 3626–3629, 3633–3636, 3640–3643, 3647–3650, 3654–3657, 3661–3664, 3668–3671, 3675–3678, 3682–3685, 3689–3692, 3696–3699, 3703–3706, 3717–3720 |
| même matériau | 13 / 29 | 4 | 3829–3832 |
| `wascity-ditch-wall-top-to-ground-edging` | 21 / 22 | 8 | 11663–11666, 11670–11673 |

Le bridge sélectionne des triangles dont l'AABB croise le rectangle. Il ne
découpe pas les triangles. Garder une couronne de sommets de raccord inchangés
pendant le remodelage ; ne pas déplacer toute la surface marchable en hauteur
sans traiter sa collision.

### Petits reliefs supplémentaires, à ne pas confondre avec des plantes

Le format `shrub` contient aussi du décor minéral. Arbre **0**, prototype **8**,
draw **8**, group **0**, matériau `wascity-ditch-wall-top-to-ground` :

| Instance | Triangles source | Emprise X / Y / Z |
|---:|---:|---|
| **1621** | 50 | 1765,15–1768,40 / 30,35–31,37 / −339,15 à −336,22 |
| **1622** | 50 | 1770,09–1773,60 / 30,68–31,50 / −341,06 à −338,36 |
| **1812** | 50 | 1753,01–1756,80 / 29,65–29,99 / −343,60 à −340,82 |

Les exporter par instance complète et les inspecter avec le terrain avant de
les reconstruire. Leur matériau et leur forme basse indiquent des reliefs
minéraux ; le mot `shrub` décrit le format de rendu, pas leur nature.

## 2. Direction artistique et textures du premier lot

**Améliorer les silhouettes et la matière sans changer leur catégorie.** Les
rochers restent des rochers irréguliers ocre, les zones de passage restent du
ciment usé, le sol sableux reste distinct. Ne pas transformer la rocaille en
dalles régulières ni repeindre toutes les pierres avec la couleur d'un seul atlas.

| Texture source, page `wascityb-vis-tfrag` | Taille | RGB moyen source, avant éclairage | Travail proposé |
|---|---:|---|---|
| `wascity-ground-01` | 128² | 138,9 / 128,3 / 108,6 | Sable tassé et grain fin, relief sobre, petites zones d'accumulation aux pieds des objets |
| `wascity-cement-road` | 64² | 102,3 / 98,8 / 91,5 | Chants usés arrondis, raccords irréguliers et fissures localisées ; garder les bandes de passage |
| `wascity-rock-small` | 128² | 141,6 / 105,9 / 83,0 | Silhouette rocheuse asymétrique, cassures larges et arêtes adoucies ; texture HD de même famille ocre |
| `wascity-ditch-wall-top-to-ground` | 256×128 | 151,1 / 118,4 / 84,7 | Raccord terre/roche et couronnement du muret ; préserver l'organisation de transition |
| `...-edging` | 256×128 | à mesurer avec l'image retenue | Bord raccordé au sol, sans ligne peinte trop régulière |
| `wascity-ground-2-ditch-03/04/05` | 128² chacun | palettes distinctes à garder | Trois raccords qui doivent être traités ensemble avec l'instance330 |

Ces moyennes sont des références de palette, pas des valeurs à imposer au pixel
près. Les sources sont opaques selon la convention PS2, alpha128. Utiliser des
textures **dédiées aux faces de ce lot** au premier passage, puis étendre après
comparaison visuelle ; un remplacement global toucherait d'autres sols de WCA,
WCB, WSD ou WWD.

## 3. Première façade voisine documentée : bordure nord-est

Après le terrain central puis le reste du sol de la place, préparer un lot
façade dans **X 1808–1844, Z −288 à −251**, avec la verticale Y environ 43–80.
Il comprend plusieurs pans superposés et des fenêtres. Identifiants attestés
dans `wascityb-native.json`, **TIE arbre0, LOD0** :

| Partie | Instance / prototype | Dessins / matériaux | Repères spatiaux |
|---|---|---|---|
| Couronnement pierre et tube vert | **1613 / 14** | d1/g25 `wascity-stone-plain-wall-3` : 40tris ; d8/g0 `wascity-greenmetal-tube` : 20tris | X1821,61–1842,73 ; Y66,28–80,22 ; Z−277,03 à−255,50 |
| Pan d'enduit haut | **2006 / 26** | d18/g1 `wascity-stucco-wall-bleached-01` : 16tris | X1818,81–1835,18 ; Y67,65–79,89 ; Z−257,61 à−253,20 |
| Pan d'enduit milieu | **2007 / 26** | d18/g1, même matériau : 16tris | X1818,80–1835,17 ; Y58,24–70,48 ; Z−257,83 à−252,74 |
| Pan d'enduit bas | **2009 / 26** | d18/g3, même matériau : 16tris | X1818,78–1835,16 ; Y48,50–60,75 ; Z−258,10 à−252,31 |
| Fenêtre basse | **1172 / 11** | d47/g37 verre + d49/g37 reflet | X1821,27–1821,91 ; Y43,72–47,93 ; Z−276,48 à−275,76 |
| Fenêtres voisines | **1167,1168,1169,1170,1171,1173 / 11** | d47 verre + d49 reflet ; groupes34,35,36,37,38 | X1811,42–1834,18 ; Y58,37–74,67 ; Z−283,22 à−270,96 |

Ce tableau ne prétend pas décrire un bâtiment complet. L'ancien export natif
filtrait certains prototypes : les pans principaux `tie/tree0/proto15`, les
éléments de façade `proto20`, les toitures `tie/tree1/proto43` et des TFRAG
doivent être recherchés lors d'un **nouvel export spatial sans filtre de
matériau**. Ensuite seulement, choisir les instances entières du bâtiment et
tous leurs LOD. Ne pas rebâtir seulement les seize triangles d'un pan en laissant
son encadrement, son dos et ses raccords de toit anciens.

Enduit source : RGB moyen 161,3/163,0/150,3 ; pierre de façade : 138,4/122,5/87,7.
Garder ces différences. Travail de forme : enduit ébréché autour des ouvertures,
chanfreins et corniches, épaisseur des encadrements, pièces métalliques réelles
aux jointures. La volumétrie penchée et les proportions exagérées de Jak restent.

### Verre et fausse association à l'océan

Chaque fenêtre identifiée contient deux triangles `wascity-window-glass-01` et
deux triangles `environment-ocean`. Cette seconde passe est un reflet de vitre,
pas une surface de mer à remplacer par le shader océan. Le verre source est
**8×32**, alpha **8–110**, page `wascityb-vis-water`. Conserver la transparence,
la scène extérieure visible et la future météo derrière la vitre ; reconstruire
les encadrements séparément.

## 4. Portes : décor statique et acteurs animés sont distincts

L'inventaire des **346 acteurs WCB ne contient aucun acteur de porte, sas ou
ascenseur** ; les 53 acteurs dans le rectangle initial du marché n'en contiennent
donc pas non plus. Les ouvertures décoratives de façade ne doivent pas être
promues arbitrairement en nouvelles portes de gameplay.

Le matériau `wascity-metal-door-01` est attesté dans le décor **TIE arbre0,
prototype2**, avec `war-armor-weathered`. Les 74 lignes d'inventaire de ce
matériau au LOD0 sont des draws, **pas 74 portes ni 74 acteurs**. L'ancien export
filtré ne fournit pas leurs identifiants d'instance.

Une lecture indépendante du GLB source `wascityb-background.glb` situe les
triangles de porte métallique les plus proches du centre `(1770,-330)` vers
**(1703,6 ; 58,6 ; −282,0)**, à **81,9 m en XZ**. C'est un repère pour un futur
export au nord-ouest, pas un ID natif de remplacement. Leur image128×32 possède
un alpha0–98 : préserver les ouvertures/découpes et la passe de reflet métallique.
Un cadre reconstruit ne doit pas devenir une plaque opaque bouchant l'ouverture.

Les premières véritables portes animées connues relèvent de WCA/WSD et arrivent
plus tard dans la progression de la ville :

| Acteur | AID / position m | Distance XZ au centre du marché | Voie d'import |
|---|---|---:|---|
| Porte d'ascenseur du palais | **41660**, (1990,968 ; 41,427 ; −439,653) | 246,7 m | Merc `wascity-elevator-door-lod0/1/2`, pivot/rig et ouverture native |
| Porte d'arène | **41661**, (2325,931 ; 58,397 ; −340,957) | 556,0 m | Merc `wascity-stad-door-lod0`, état `com-airlock` préservé |
| Petit sas de ville | **37579**, (2265,652 ; 30,190 ; 131,218) | 677,0 m | Merc `wascity-airlock-small-lod0`, collisions transformées et transition de niveau |

Leur façade et leur cadre fixes peuvent utiliser le bridge statique. Le vantail
mobile reste dans la voie Merc avec le squelette, les animations et les passages
de collision. Les remplacer en TFRAG figerait l'ouverture/fermeture.

## 5. Procédure de sélection pour la prochaine réalisation

1. **Prendre le FR3 WCB actuellement validé**, incluant les marchés/plantes/supports
   et les matériaux installés. Relever SHA256 et taille dans une nouvelle sélection.
   Les exports utilisés ici ont pour base l'ancien FR3 de 6 592 063 octets,
   SHA `ed63aa4dd8e871111914b4d2e5d0f663e237fcc9eeac367ea5acbacf823fb20e`.
   Leurs indices sont des repères à confirmer, pas un droit d'écraser le niveau actuel.
2. Export TIE : `instances` explicites pour `tree1/212,272,330,581,624,626`, sans
   bornes spatiales et sans filtre de matériau ; tous les LOD. Export complémentaire
   SHRUB `tree0/1621,1622,1812` pour les petits reliefs minéraux.
3. Export TFRAG séparé : `bounds_xz_m=[1752,1785,-349,-314]`, arbre0, matériaux
   du sol et des bordures, LOD0/1/2. Inspecter les bords de la sélection et garder
   les raccords externes exactement en place.
4. Concevoir le terrain et ses objets ensemble. Préserver gabarit marchable,
   pieds des palmiers/étals, altitude des passages et limites de collision.
   Contrôler les rochers en silhouette, le raccord sable/ciment et les détails
   depuis la hauteur normale de Jak ; ne pas limiter la validation à une vue Blender.
5. Appliquer sur une **copie** du FR3 courant. Vérifier les préconditions de
   chaque triangle retiré et la préservation des groupes non sélectionnés,
   Merc déjà reconstruits, eau, plantes et textures dédiées. Publier ce lot
   terrain uniquement après contrôle natif depuis plusieurs angles.
6. Étendre ensuite le terrain à tout le rectangle initial du marché
   `[1735,1820,-355,-290]`, puis au bâtiment nord-est décrit ci-dessus. Les
   portes décoratives du nord-ouest et les portes animées de WCA sont des lots
   suivants, avec leurs voies d'import respectives.

Commande d'export existante, à utiliser pendant l'implémentation suivante :

```text
palace_mesh_bridge --export-selected current-wascityb.fr3 selection.json export.json
```

## Sources locales consultées

- `market-block-native.json`, `market-block-native-summary.json` : faces et clés du premier rectangle.
- `wascityb-native.json` : inventaire large, faces partielles selon les anciens filtres palace.
- `inventory.json` : acteurs, contrôles Merc, pages/taille/alpha des textures.
- `BRIDGE.md` : sélection d'instances entières et filtres du bridge.
- GLB original `active/jak3/data/decompiler_out/jak3/levels/wascityb/wascityb-background.glb` : localisation supplémentaire des portes décoratives, sans conversion en IDs natifs.
- PNG originaux `active/jak3/data/decompiler_out/jak3/textures/wascityb-vis-tfrag/` : mesures de palette RGB.

Les listes et positions de ce document ont été obtenues sans lancer le jeu,
le compilateur, une extraction ni une modification de géométrie.
