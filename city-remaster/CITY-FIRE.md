# Feux de Spargus — inventaire et intégration proposée

Lecture seule des placements `inventory.json`, vérifiés contre les définitions
GOAL. Aucun rendu, groupe de particules ou FR3 modifié par cet inventaire.

| Groupe natif | Placements | Particules |
|---|---:|---|
| group-waswide-gaslamp (484) | WCA 33, WCB 26 | 1919–1923 |
| group-waswide-talltorch (485) | WCA 2 | 1924–1926 |
| group-wasdoors-gaslamp (393) | WSD 4 | 1603–1607 |
| group-wascity-palace-fire-beacon (471) | WWD 1 | 1857–1859 |

Total : **66 placements source**, pas 66 feux toujours actifs. Toutes les
transformations et identités se trouvent dans
`inventory.json/source_actor_fire_candidates_all_maps`. Les AID WCA 60265 et
46703 partagent une position : conserver leurs règles d'activation avant toute
déduplication. Premier contrôle côtier conseillé : WCB AID 46673,
`(1840.852, 48.817, -387.194)` mètres. Les torches 37740/37741 et la balise
lointaine à Y=507.394 m nécessitent leurs propres dimensions.

## Point de raccordement sûr

`engine-src/goal_src/jak3/engine/common-obs/generic-obs.gc` :

- `part-spawner init-from-entity!` (1976) résout `art-name`, quaternion,
  décalages et groupe. Conserver l'identité niveau + AID + groupe.
- L'état `active` (1929) possède `enable`, les événements start/stop et les
  transformations éventuellement animées ; publier le foyer uniquement au
  moment du `spawn` actif. `deactivate` (1909) retire immédiatement le foyer.
- Les familles sélectionnées n'utilisent pas les voies sp8/sp9 qui transfèrent
  un groupe au moteur de niveau puis détruisent le contrôleur. Ces autres
  familles doivent être traitées séparément lors de l'extension globale.
- Le groupe gaslamp commence avec un décalage **local Z de 0.4 m**. Appliquer
  le quaternion et ajuster l'ouverture du récipient ; ne pas ajouter 0.4 au Y
  mondial sans vérifier l'orientation.

Un pont synchronisé GOAL → C++ peut reprendre le mécanisme de `WaterContacts.h`.
Un registre de sources actives évite les feux fantômes de scènes chargées mais
inactives. Retirer uniquement les anciennes couches correspondant à un foyer
modernisé effectivement présent ; conserver sons, déclencheurs et dégâts.

## Réutilisation du rendu accepté

Le palais est actuellement limité à 24 sources constantes dans les six shaders
générés par `fire-v1/prepare.py`. Conserver sa recette, ses plans de combustible
et son ajustement des neuf vasques. Le rendu partagé doit recevoir les sources
et recettes séparément, sans modifier cette base acceptée.

Préserver le passage avant l'eau (après OCEAN_NEAR 462, avant WATER 463), la
profondeur opaque, le mélange prémultiplié et la restauration d'état OpenGL.
Cela garde le feu visible dans la réfraction sans le montrer à travers un mur.

Le shader de lumière fait actuellement 24 recherches par pixel, avec quatre
probes de profondeur par foyer. Ne pas simplement multiplier cette boucle par
66 ou par les 571 candidats toutes cartes : limiter les sources proches et
visibles, les lumières locales et les braises, avec une représentation distante.

Premier lot recommandé : les 59 lampes WCA/WCB, puis les deux grandes torches,
avec tests à l'ouverture du récipient, de profil, à travers l'eau et pendant
start/stop et les transitions WCA/WCB. WSD et la balise suivent avec leur recette.
La généralisation toutes cartes reste autorisée mais n'est pas déjà réalisée.
