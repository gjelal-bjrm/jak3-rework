# Herbe : racines réelles et passage de Jak

## Cause corrigée

Le contact précédent utilisait la distance entre Jak et chaque sommet. Il
annulait l'effet au-dessus de 1,85 m, alors que 665 des 1 482 touffes de rue sont
plus hautes. Des pointes extérieures sortaient aussi du rayon de 0,78 m. Le
déplacement restait au centre des feuilles, souvent masqué par Jak.

Le nouveau passage SHRUB reconstruit les connexions de chaque brin à partir
des triangles effectivement chargés. Les coordonnées identiques sont soudées
dans une structure temporaire, sans modifier le mesh. Le V natif 4096 identifie
les racines. Un attribut GPU contient la racine et la hauteur de chaque brin.
Le shader mesure le contact au pied de la plante : les grandes pointes suivent
la courbure, les racines restent fixes, et la plante revient progressivement au
vent seul une seconde après le dernier contact. Des contacts simultanés sont
bornés, sans accumulation à l'arrêt.

Seul `market-shrub-orange-v1` dans WCA/WCB reçoit cet attribut. Les textures,
palettes, maillages, collisions, cactus et plantes du palais ne sont pas modifiés.
Le hook GOAL existant continue de fournir le véritable point de contact au sol
de Jak ; aucun échantillon artificiel n'est injecté par ce correctif.

## Sources et intégration

- `GrassAnchors.h` : extraction des racines à chaque chargement SHRUB.
- `contact.glsl` : shader de contact, hauteur et retour progressif.
- `apply.py` : génération réversible et copies strictes des sources précédentes.
- `manifest.json`, `before/`, `staging/` : provenance de cette succession.

`--apply-source` a modifié uniquement les sources dans `engine-src`. Il faut
recompiler le moteur, puis appliquer `--apply-data` quand le moteur correspondant
est prêt et intégrer le shader via le paquet habituel. Cette étape n'a pas été
effectuée par ce sous-travail. Il ne faut recompiler aucun objet GOAL.

```powershell
C:/Python313/python.exe city-remaster/grass-contact-v2/apply.py --apply-source
# Après compilation du moteur par la tâche principale :
C:/Python313/python.exe city-remaster/grass-contact-v2/apply.py --apply-data
```

Le validateur de `grass-contact/apply.py` remonte cette révision par un inverse
strict avant de comparer son ancien état. Les manifestes historiques restent
inchangés. Le fichier nouveau `GrassAnchors.h` doit aussi être ajouté à la liste
des sources protégées du paquet par la tâche principale.

## Vérifications réalisées

Un export en lecture seule du FR3 WCA installé contient 6 510 triangles de
vraies touffes proches des maisons, soit 19 530 sommets. Le C++ d'extraction
reconnaît 105 brins, sans composant dépourvu de racine. Sa compilation autonome
et ce test ne compilent ni ne lancent le moteur.

Le shader complet corrigé a été exécuté sur ces sommets par retour GPU dans un
contexte WGL masqué, RTX 3080 Ti, OpenGL 4.6. Les 13 contrôles passent : racines
exactes, pointes hautes et extérieures actives, exclusion des autres étages et
plantes, absence d'amplification des doublons et récupération monotone. La pointe
haute mesurée se déplace de 65 cm ; une pointe extérieure de 52 cm. Cela est un
contrôle GPU sur les véritables meshes, pas encore une validation de marche
normale dans le jeu. Rapports : `qa/anchors-validation.json`, `qa/gpu-validation.json`.

## Contrôle natif à effectuer

Lancer muet (`OPENGOAL_TEST_MUTE=1`). Après chargement WCA, le journal doit
contenir `Remaster grass roots [wascitya]` avec les nombres de brins et sommets
ancrés. Le journal du contact existant confirme le passage GOAL vers le shader.

Deux touffes de référence :

| Instance native | Racine X/Y/Z (m) | Hauteur de la touffe |
| --- | --- | --- |
| WCA 2464 | 2264,5806 / 17,1749 / 9,4635 | ≈ 2,32 m |
| WCA 2465 | 2264,0200 / 16,5976 / 8,1148 | ≈ 1,49 m |

`native-qa.gc` propose une traversée courte dans un processus de test qui
appelle `(suspend)` chaque image ; le REPL n'est donc pas bloqué par une boucle
active. Il utilise `move-to-point!` pour déplacer aussi les sphères de collision
et synchronise la racine du personnage. Il journalise position de contrôle,
racine et état au sol. Il laisse la gravité et le contact Y à la physique du jeu.
La fonction native se trouve dans `engine/collide/collide-shape.gc:2156` ; une
écriture isolée de `control.trans` laisse les sphères à l'ancien endroit.

Pour les captures : même caméra fixe, repos avant la traversée, contact avec la
touffe, sortie puis repos après 1,2 s. Le script traduit Jak de façon contrôlée ;
il ne prouve pas son animation de marche. Compléter ensuite par une traversée
normale à la manette. Ne pas annoncer l'interaction comme validée en jeu avant
d'avoir observé cette traversée et son redressement.
