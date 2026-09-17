# Conversation des habitants — motion-v2

Ce dossier est un **candidat séparé**, pas une installation dans le jeu. Il remplace uniquement les animations `conversing-male` et `conversing-female`. Les modèles, les textures, les couleurs natives et le nombre de triangles sont conservés. L’homme assis n’est pas modifié.

## Ce qui change

- Les bras reviennent au repos entre les gestes ; ils ne restent plus constamment tendus.
- L’homme prend la parole pendant la première moitié du cycle, la femme pendant la seconde. Le partenaire écoute avec de petits mouvements de tête.
- Le bassin change légèrement d’appui. Les deux chaînes de jambes sont résolues vers des pieds fixes ; les semelles ne glissent pas et les membres ne sont pas étirés.
- Les rotations de tête compensent le mouvement du buste, avec une légère correction pour la différence de taille.
- Le cycle comprend **32 poses en 8 secondes**, avec interpolation des positions et des normales. Le raccord de boucle est continu.

Il n’y a pas de synchronisation labiale ni de dialogue audio. La qualité géométrique des personnages reste celle des vrais habitants natifs de Spargus ; ce lot corrige leur animation et leur posture.

## Placement et phase dans la pièce partagée

Les coordonnées ci-dessous sont les coordonnées locales de la pièce, en mètres, avec Y vers le haut. L’avant du personnage exporté est **+Z**. Le shader transforme cette direction en `(sin(yaw), 0, cos(yaw))`.

| Personnage | Position X / Y / Z | Rotation Y en radians |
|---|---|---|
| Homme | `0.25 / 0.058 / -2.15` | `2.2142974356` |
| Femme | `1.45 / 0.058 / -3.05` | `-0.9272952180` |

Ces orientations dirigent chaque habitant vers son partenaire, à 1,5 m de distance entre les origines. L’ancien angle masculin `1.05` le faisait regarder à environ 67° du partenaire.

**Les deux personnages doivent recevoir la même phase en secondes.** L’alternance est déjà inscrite dans leurs clips ; ajouter un décalage à la femme la désynchronise. Une autre paire peut recevoir une phase commune différente. Pour une paire placée autrement, calculer chaque angle avec `atan2(deltaX, deltaZ)`.

## Format et mémoire

Format inchangé : JSON + BIN de sommets triangulés, 12 float32 par sommet, soit 48 octets : position3, normale3, UV2, couleur4. Chaque pose conserve exactement les UV et les couleurs ; seuls positions et normales varient. Les normales interpolées doivent être normalisées.

- Homme : 5 310 sommets / pose, 1 770 triangles.
- Femme : 6 288 sommets / pose, 2 096 triangles.
- Deux clips : 17 814 528 octets de sommets au total (environ 17 Mio), chargés une fois par modèle.
- PNG natifs conservés sans modification. Leur alpha natif 128/255 est compensé par l’alpha2 des couleurs de sommets, comme auparavant.

## Reproduction et preuve

1. Exécuter `author.py` avec Blender 5.2 en arrière-plan : export des clips et des rigs `.blend` éditables.
2. Exécuter `preview.py` avec Blender : rendu des **sommets réellement exportés**, dans les positions et orientations indiquées ci-dessus.
3. Vérifier le manifeste `provenance.json` et les validations numériques associées.

`before/` conserve les quatre fichiers BIN/JSON prédécesseurs sans modification. Les textures, le personnage assis et les autres preuves historiques du dossier parent ne sont pas remplacés par ce candidat.

Les images `pair-frame-*.png` sont des **rendus de contrôle Blender**, pas des captures du jeu. Elles vérifient les gestes, les appuis et les orientations. Une observation du cycle complet dans le moteur est nécessaire pour valider le mouvement avec l’éclairage et les caméras du jeu.

Rendus inspectés : repos (image00), geste masculin (image06), angle latéral (image06-side), fin de phrase masculine (image12), réponse féminine (image22).
