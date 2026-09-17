# Auvent de marché reconstruit — retouches V2

Les contrôles `wascity-awning-b-lod0` et `wascity-awning-b-lod1` sont prêts pour
l’import en staging. Cette V2 reprend les retours sur la V1 vue en jeu ; elle
n’est pas encore validée dans le rendu natif. Ce lot ne l’installe pas.

| Élément | LOD 0 | LOD 1 |
| --- | ---: | ---: |
| Triangles d’origine | 40 | 8 |
| Triangles V1 | 9 792 | 3 696 |
| Triangles V2 | 11 696 | 4 504 |
| Matériaux / primitives | 2 / 2 | 2 / 2 |
| Franges en volume | 38 | 22 |

La toile garde son galbe et son épaisseur réelle de 24 mm. La grille principale
reste à 56 × 18 / 28 × 10 cellules : le relief a changé, sans subdivision ajoutée.
Des plis plus larges convergent vers les quatre attaches ; trois plis par coin
ont des amplitudes de commande de +13 / −11,5 / +10 cm, atténuées jusqu’à 2,85 m
du coin et nulles aux bords fixes. Les petites ondulations sont moins nombreuses.

L’ourlet roulé passe de 3,5 à **5,5 cm de rayon**. Quatre recouvrements de panneaux
remplacent les anciens cordons étroits : bandes en relief sur **les deux faces**,
environ 18 cm de largeur dans la partie centrale et jusqu’à 3,5 cm au-dessus de
la toile. Le dessous est ainsi travaillé pour la vue du joueur depuis la rue.
Les deux LOD ont des points de couture en volume (128 / 72), de 1 / 1,1 cm de
rayon ; le LOD 0 ajoute 136 points de blocage près des bords avant et arrière.
Des renforts aux coins, quatre anneaux forgés, des cordes et leurs nœuds
complètent les attaches. Le LOD 1 garde la même silhouette avec moins de détails.

La texture de toile fait **1 254 × 1 254 pixels**, produite par le mode intégré
d’imagegen à partir de la texture d’origine. Sa palette olive est rapprochée
de celle de la source par les couleurs de sommets. La V2 conserve le bitmap et
réduit la luminosité de base par un facteur 0,86, avec une légère correction de
la dominante rouge (multiplicateurs RVB 1,04 / 1,18 / 1,30, remplaçant
1,0755 / 1,1583 / 1,2731). Une atténuation locale modérée, plafonnée à 22 %, suit
les creux des vrais plis, les bords et les recouvrements. Le prompt exact et les
empreintes sont dans `awning-texture-provenance.json`. La vignette de bronze
est une définition de couleur de matériau ; les reliefs des anneaux sont modélisés.

## Animation et gabarit

Le squelette conserve ses 11 articulations, leurs matrices et leur ordre natif.
Blender trie certains joints à l’export : le script rétablit l’ordre attendu
dans `skin.joints`, les matrices inverse-bind et **toutes** les valeurs JOINTS_0.
Les poids personnalisés interpolent les triangles réellement dessinés de la
source, avec trois influences normalisées au maximum. Les ancrages gardent
l’influence `main` d’origine.

Le GLB LOD 1 original ne contient pas de skin. `skel-wascity-awning-b` dans
`waswide-obs.gc:723` prouve qu’il partage le groupe d’articulations du LOD 0.
Ses matrices actives restent limitées à 3–7 : `main`, `centerc`, `centerd`,
`leftb`, `rightb`. Aucun poids ne demande les articulations supplémentaires
du LOD 0. Les sommets inutilisés des accessors, qui appartiennent à d’autres
contrôles et contiennent d’autres indices de joints, sont exclus.

Le volume indexé reste proche de la source : l’ajout maximal des attaches en X
est de 17 cm ; l’épaisseur et les plis étendent la hauteur de moins de 10 cm.
Un test de déformation dans Blender déplace la toile jusqu’à 21 cm et garde
les ancrages fixes à 0 m. Ce contrôle ne remplace pas celui du bouncer en jeu.
Les limites indexées de la V2 restent celles de la V1 en X et en hauteur à
quelques millimètres près ; seul le rayon d’ourlet ajoute 2 cm sur le bord avant.
Aucune donnée de collision n’est modifiée dans ce lot.

Ce contrôle Merc est une toile suspendue ; il ne contient aucun poteau ni pied
d’origine. Les supports fixes de ville nécessitent leur propre reconstruction,
afin de ne pas les faire bouger avec l’animation de la toile.

## Sources et validation

- Auteur : `author_awning.py` ; projets `wascity-awning-b-lod0.blend` et `wascity-awning-b-lod1.blend`.
- Exports : les deux fichiers GLB portant les mêmes noms que les contrôles natifs.
- Aperçus : `wascity-awning-b-lod0-preview.png`, `wascity-awning-b-lod1-preview.png`, `wascity-awning-b-lod0-bouncer-preview.png`, et les vues `-underside-preview.png` de chaque LOD.
- Rapports : `awning-author-report.json`, `awning-import-validation.json`.

Les deux exports passent `validate_model` : attributs natifs, UV/couleurs,
images embarquées, poids, matrices, ordre du squelette, gabarit indexé et
une primitive par matériau. Les aperçus Blender ont été inspectés.

Un défaut d’export de la V1 expliquait une partie du rendu natif jaune et trop
clair : Blender exportait une couche `COLOR_0` blanche, puis la vraie teinte en
`COLOR_1`, que l’importeur Merc ne lit pas. L’auteur force maintenant
`export_vertex_color='NAME'`, `export_vertex_color_name='COLOR_0'` et
`export_all_vertex_colors=False`. Le rapport contrôle les valeurs réelles :
un seul `COLOR_0`, composantes RVB linéaires entre 0,331 et 0,610 suivant le
canal et la zone, alpha 1. L’export conserve ces valeurs en entiers 16 bits
normalisés ; aucune correction gamma supplémentaire n’est appliquée.

Les vues du dessous utilisent un éclairage de studio inférieur pour contrôler
les coutures : cet éclairage n’est ni exporté ni ajouté au jeu. Le rendu de la
V2 sous le soleil natif, son animation et sa charge restent à valider à l’intégration.
