# Supports du marché

Ce lot remodèle les 14 poteaux, 14 bras de support et 28 anneaux des sept
étals sélectionnés dans WCB. Les toiles animées restent des acteurs séparés.

Le bois est reconstruit en sections arrondies irrégulières, avec une courbe
continue, une légère conicité et des extrémités adoucies. Les longues ferrures
suivent le bois ; elles comportent des lèvres roulées et des rivets. Une fourche
à deux joues, une douille et une goupille rejoignent chaque bras d'auvent à son
ancrage déporté d'origine. Les anneaux
ont une section forgée en volume. Les quatre niveaux de détail sont exportés.

Les nouvelles textures dédiées conservent le brun du bois de ces supports et
le gris bleuté du métal. Elles ne remplacent aucun atlas partagé de la ville.
Les couleurs d’éclairage natives sont interpolées sur les nouvelles surfaces.
Les collisions et les points d’attache des acteurs restent ceux du jeu.

`../author_supports.py` produit `market-supports.blend`, `patch.json` et le
rapport auteur. Les images du dossier sont des inspections Blender ; la preuve
du chargement et du rendu en jeu est enregistrée séparément après intégration.

Le lot représente 168 448 triangles tous niveaux de détail confondus. La base
des poteaux conserve exactement sa hauteur minimale native ; l'arrondi et les
chanfreins ne doivent pas relever leurs pieds.
Les scripts d’intégration conservent une copie du niveau avant modification
et refusent les suppressions qui ne correspondent pas aux faces natives.
