# Feux de Spargus — recette du palais, sources actives

Cette passe branche le rendu volumétrique accepté du palais sur les **59 lampes
à gaz et 2 grandes torches** présentes dans WCA/WCB. Il s'agit de 61 placements
possibles, dont seuls les `part-spawner` activés par le jeu alimentent le rendu.
Les six shaders et les 24 sources du palais restent inchangés.

## Intégration

- `fit_sources.py` retrouve les lèvres des 61 récipients dans les triangles
  indexés d'origine. Les centres des anciens sprites étaient 10 à 60 cm au-dessus
  du foyer. Chaque nouveau départ est placé 7,5 cm sous la lèvre basse, avec une
  empreinte contenue dans l'ouverture ; la profondeur du vrai récipient masque
  sa partie basse. La transformation quaternion du contrôleur est conservée.
- `hook.gc` publie après les mises à jour de trajectoire du contrôleur actif.
  Les événements `stop` et la désactivation retirent immédiatement la source.
  Le filtre de région précède les lectures d'entité/racine ; les 61 identités
  exactes sont contrôlées en C++, sans lire le mode de particules des autres
  cartes. Une désactivation accepte une racine déjà libérée.
  Un acteur inconnu ou un renderer non initialisé conserve le spawn original.
  Aucun groupe de particules global ni aucun son, événement ou dégât n'est effacé.
- `CityFire.h` réutilise le volume à 48 échantillons, les langues de feu, braises,
  lumière locale, clipping opaque et mélange prémultiplié du palais. Le passage
  reste après OCEAN_NEAR et avant WATER, afin que l'eau réfracte le feu.
- Les phases sont attachées aux identités d'acteurs, même quand le tri change.
  Huit lumières proches au maximum, braises atténuées entre 28 et 48 m, volume
  lointain à 24 échantillons et atténuation native entre 200 et 300 m.

## Reproduction et installation

1. `python city-remaster/city-fire-v2/fit_sources.py`
2. `python city-remaster/city-fire-v2/prepare.py`
3. `python city-remaster/city-fire-v2/apply.py --apply` — sources seulement.
4. Compiler `generic-obs.gc` :
   `(m "goal_src/jak3/engine/common-obs/generic-obs.gc")`, puis compiler `gk`.
5. `python city-remaster/city-fire-v2/register.py --parent-record city-remaster/grass-contact/installed.json --object-sha256 HASH`
   examine les candidats. Ajouter `--apply` pour installer.
6. Exécuter le package commun puis lancer le jeu muet pour la revue native.

Le registre remplace **generic-obs uniquement**, conserve les autres blocs GAME
au byte près, et ajoute les six fichiers de shader au système de variantes.
Les versions originales reçoivent uniquement ces nouveaux fichiers inutilisés
par leur moteur ; aucun fichier préexistant original/V1 n'est remplacé.
Pour corriger uniquement `generic-obs` après une installation, ajouter `--revise` :
l'ancien objet, ses archives et son record restent figés dans le nouveau staging.
Les routes courantes doivent correspondre exactement à l'ancien résultat ou au
parent original restauré pour diagnostic. Tout autre changement est refusé.

## Validation effectuée avant build commun

- Registre C++ réel compilé : 61 identités, 35/26 par secteur, quaternion,
  activation/extinction, absence de doublons, rejet d'acteurs/transforms invalides,
  réinitialisation et portée 300 m.
- Six shaders réellement compilés/liés sur RTX 3080 Ti dans un contexte invisible.
  Rendu du volume à deux instants : animation mesurée, 6122 pixels de couverture
  dans la scène d'essai, occlusion complète par une profondeur opaque interposée.
- Inverses stricts des sources et chaîne herbe précédente ; candidat archive en
  mémoire et corruption d'un second objet volontairement rejetée.

La revue dans le jeu est distincte de ces contrôles techniques : voir
`NATIVE-QA.md`. Les portes WSD et la balise lointaine WWD n'appartiennent pas à
cette passe. Ce branchement ne constitue pas la refonte complète de Spargus.
