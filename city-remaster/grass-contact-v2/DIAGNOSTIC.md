# Herbe au passage — diagnostic, travail suspendu

Priorité utilisateur du 17 septembre 2026 : les bâtiments d'abord. Aucune
modification du moteur, du shader, du GOAL ou du paquet n'a été faite dans cette
investigation. La correction n'est pas implémentée et n'est pas validée en jeu.

## Cause constatée dans les données et le shader

`grass-contact/contact.glsl` annule la réponse à partir de 1,85 m au-dessus du
contact physique au sol. Or les rapports Blender `vegetation-v2/*-report.json`
décrivent des herbes bien plus hautes :

| Niveau | Touffes | Au-dessus de 1,85 m | Hauteur médiane | Maximum |
| --- | ---: | ---: | ---: | ---: |
| WCA | 789 | 432 | 1,913 m | 3,505 m |
| WCB | 693 | 233 | 1,604 m | 3,493 m |

Les pointes d'au moins 665 touffes sortent ainsi de l'enveloppe verticale du
contact. De plus, la distance horizontale est mesurée pour chaque sommet dans
un rayon de 0,78 m, tandis que les touffes occupent souvent plus de 2 m de large.
Une partie importante du mouvement éventuel reste au milieu du brin, cachée
par Jak, au lieu de déplacer la silhouette. Les anciennes fixtures GPU ne
couvraient que des pointes à 0,6 m de hauteur et ne détectaient pas ce défaut.

Ce constat explique une insuffisance réelle de l'effet. Il ne remplace pas un
test natif de marche pour exclure en plus une absence intermittente de contact.

## Correction proposée, pas encore réalisée

Préparer un catalogue des racines et dimensions à partir du rapport des modèles
finalement retenus ; utiliser ces ancrages pour étendre la réponse à toute la
touffe touchée, conserver les racines immobiles et rejeter une plante située à
un autre étage. Préserver le V natif 4096 à la racine et 0 à la pointe pour les
différentes tailles et densités de végétation. Contrôler ensuite un passage
normal de Jak, sa sortie et le redressement dans le jeu réellement empaqueté.

La géométrie pouvant encore évoluer, ne pas figer un catalogue sur les rapports
anciens avant la reprise de ce travail.
