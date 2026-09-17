# Sacs : affaissement et plis lisibles en jeu

La seconde passe modifie uniquement les deux sacs. La caisse, la jarre et la
corbeille conservent exactement leurs GLB, `.blend` et aperçus précédents : les
neuf empreintes SHA-256 ont été comparées avant et après.

- **Sac ouvert — 12 728 triangles :** trois plis courbes convergent vers les
  coutures, l'épaulement s'affaisse de façon asymétrique, le col est incliné et
  le contenu est abaissé pour rester sous le bord. Le contenu garde une surface
  sensiblement horizontale ; il ne suit pas l'inclinaison du tissu.
- **Sac ligaturé — 11 014 triangles :** trois plis profonds convergent vers le
  col incliné, avec un flanc plus comprimé et une épaule plus pleine. Le nœud,
  les cordes et les coutures suivent exactement la déformation du sac. La queue
  de tissu retombe légèrement d'un côté.

Les plis sont des déformations de surface réelles, de 12 à 17 cm environ dans
le repère auteur avant remise au gabarit natif. Le maillage du corps est passé
de 64 × 32 à 80 × 40 pour décrire leurs courbes. Une ombre locale de creux
réduit les trois canaux RGB de façon identique, au maximum de 20 %, afin de
conserver leur lecture avec l'éclairage Merc. Les images HD et les teintes
restent inchangées.

## Fichiers

`author_accessories.py` reste le script reproductible. Exécuter uniquement :

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python city-remaster/author_accessories.py -- market-sack-a-lod0 market-sack-b-lod0
python city-remaster/validate_accessories.py
```

Les GLB, `.blend` et `*-authored.png` des deux sacs sont actualisés. Le dossier
`sack-before-drape` conserve les GLB et aperçus de la première passe pour une
comparaison directe. Le rapport d'auteur global garde les cinq accessoires.

## Vérification

Les deux nouveaux exports passent la validation de l'armature, des matrices,
des poids, des attributs, des matériaux et des textures HD. Le volume indexé
est identique au gabarit original, avec la base à Y = 0 m. Le pivot et l'axe du
contrôle sont conservés. Aucun sommet inutilisé, triangle dégénéré ou normale
invalide n'a été trouvé.

Les deux aperçus Blender ont été inspectés. `sack-drape-report.json` contient
les empreintes et la portée de cette passe. Aucun build, extraction, lancement
ou déploiement n'a été effectué ; la validation visuelle native reste à faire.
