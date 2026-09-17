# Habitants des fenêtres — trois acteurs animés

Les personnages proviennent des vrais `wlander-male-lod0` et
`wlander-female-lod0` de Spargus, avec leur squelette, leurs couleurs et leurs
textures. Le GLB d'origine réunit plusieurs habits et têtes alternatifs ;
`prepare.py` sélectionne un seul corps complet par sexe à partir des groupes
Merc du FR3, sans arme et sans superpositions de variantes.

## Livrables

- `sitting-male` : assis, jambes vers l'avant, mains proches des cuisses,
  respiration et petits mouvements de tête ; boucle de 5,6 secondes.
- `conversing-male` et `conversing-female` : debout, une main accompagne la
  conversation, tête orientée vers un interlocuteur ; boucle de 4,8 secondes.
- Chaque acteur possède un `.blend` avec squelette et cinq poses clés (la
  cinquième ferme la boucle), un aperçu PNG, un JSON et un binaire.
- `actors.json` recense les acteurs. `validation.json` contient 48 vérifications
  réussies sur les données finales. Les trois aperçus Blender ont été inspectés.

Les jambes restent fixes pendant les gestes. Les amplitudes maximales des
changements entre poses sont environ 2,9 cm pour l'acteur assis et 5 cm pour la
conversation. Il s'agit de silhouettes humaines natives animées, pas de
personnages construits avec des primitives.

## Format du moteur

Le binaire contient quatre tableaux successifs de `vertex_count` sommets.
Chaque sommet est constitué de **12 float32 little-endian, 48 octets** :

| Décalage | Attribut | Composantes |
| ---: | --- | ---: |
| 0 | Position | 3 |
| 12 | Normale | 3 |
| 24 | UV | 2 |
| 32 | Couleur RGBA | 4 |

Toutes les poses ont le même ordre de triangles déroulés. Il n'y a donc aucun
index séparé. Pour chaque entrée `draws`, utiliser `glDrawArrays(GL_TRIANGLES,
first, count)` avec sa texture. Le chemin `texture` est relatif à ce dossier.
Le dernier quart de la boucle interpole la pose 3 vers la pose 0. Interpoler les
positions et normaliser le mélange des normales ; les UV et couleurs sont
strictement constants entre poses.

Le repère est X à droite, **Y vers le haut, +Z vers l'avant**, en mètres. Les
semelles les plus basses sont à Y=0 pour toutes les poses. L'homme mesure 2 m,
la femme 1,9 m debout. `seat.recommended_cushion_top_m` et `seat.center_m`
indiquent l'assise mesurée, à utiliser pour positionner la banquette. Le fichier
Blender conserve l'échelle native d'auteur ; les exports ont déjà reçu le
facteur `source_to_metres_scale` et le repositionnement au sol.

### Couleurs et alpha

Le GLB natif applique un `baseColorFactor` égal à 2. Ce facteur est **déjà
intégré dans RGBA** : RGB est approximativement entre 0 et 1, A vaut 2. Les PNG
sont les images natives exactes, dont l'alpha opaque est 128/255. Multiplier
simplement `texture(albedo, uv) * vertex_color` avant l'éclairage. Ne pas
appliquer de nouveau facteur 2 et ne pas interpréter A=2 comme un octet.

Conserver les deux faces, comme dans le GLB natif. Un rejet des fragments dont
l'alpha résultant est inférieur à 0,15 convient aux découpes des matériaux ;
les autres fragments sont opaques. Les UV sont livrés selon l'orientation
native glTF, V=0 au premier rang des pixels PNG. Si le chargeur retourne
verticalement les PNG, compenser ce retournement une seule fois.

## Reproduction

1. Exécuter `prepare.py` avec le Python de Blender disposant de zstandard.
2. Exécuter Blender en arrière-plan avec `--python author.py`.
3. Exécuter `verify.py` avec Python.

Les scripts écrivent exclusivement dans `inhabitants`. Aucun fichier moteur,
aucune archive et aucun paquet de jeu n'est modifié.

**Limite :** ces contrôles et aperçus ne constituent pas une validation native
dans le jeu. L'intégration avec les vraies ouvertures, leur profondeur, le
mobilier et l'éclairage doit encore être vérifiée par le rendu du moteur.
