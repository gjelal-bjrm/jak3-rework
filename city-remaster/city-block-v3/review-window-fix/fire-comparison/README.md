# Comparaison native du feu — WCA / WCB

Cette comparaison remet les **anciens émetteurs de particules de la ville** dans le **même moteur actuel**, avec la même géométrie, les mêmes textures, l'eau, les intérieurs et la lumière ambiante. Elle ne représente pas le rendu PS2 original complet.

## Fichiers préparés, sans installation

Lancer `C:\Python313\python.exe prepare.py` depuis ce dossier. Le script écrit uniquement ici et refuse d'écraser une preuve différente. Il prépare pour chaque route `arena` et `palace` :

- `staging/<route>/before-GAME.CGO` : parent grass archivé, émetteurs natifs.
- `staging/<route>/after-GAME.CGO` : version city-fire installée et validée.
- `preservation.json` : preuve octet par octet que seul `generic-obs` change, avec les **489 autres objets intégralement identiques**, entêtes et remplissage compris, et reconstruction inverse exacte.
- Les deux objets compilés, les deux sources GOAL avant modification et leurs manifestes historiques.

La version avant est extraite du parent exact de l'installation city-fire. Elle n'est ni recompilée aujourd'hui ni reconstruite approximativement. La version après est l'objet corrigé `0f8e38bd…`, jamais la révision abandonnée qui plantait au chargement du palais. Un contrôle négatif vérifie que modifier un autre objet fait échouer l'audit.

## Manipulation réservée au root, hors des scripts de ce dossier

1. Attendre que le nouveau moteur et les assets R4 soient installés et que le paquet soit terminé. Utiliser ensuite **ce même paquet pour les quatre captures**. Préparer normalement la route `palace`, avec le son désactivé et une vérification native du silence.
2. Arrêter le processus avant chaque changement de version. Après la préparation normale du lanceur, remplacer **uniquement** `data/out/jak3/iso/GAME.CGO` par l'archive avant de la route `palace`. Ne changer ni les routes permanentes, ni les variantes, ni les FR3, ni la configuration des pièces.
3. Démarrer un **nouveau processus** avec la commande native déjà utilisée, sans rappeler la préparation qui remettrait automatiquement GAME après. Garder `OPENGOAL_TEST_MUTE=1` et confirmer le silence. Le contrôle `snapshot` refuse une archive différente de la version demandée.
4. Rejoindre `wascitya-seem`, poser la caméra WCA ci-dessous, garder heure, FOV et résolution identiques. Attendre la stabilisation du chargement et au moins trois secondes. Capturer l'ancien feu. Puis rejoindre `wascityb-seem`, appliquer la caméra WCB et capturer l'ancien feu.
5. Arrêter ce processus, restaurer **exactement** `staging/palace/after-GAME.CGO` dans le chemin actif, redémarrer et refaire WCA/WCB avec les mêmes réglages. Conserver aussi une courte séquence ou plusieurs images pour juger le mouvement.
6. Après comparaison, conserver le GAME après, vérifier son SHA et relancer le contrôle complet du paquet. Ne jamais publier les archives avant comme variante de remaster.

**Un rechargement à chaud est insuffisant.** Les sources modernes sont publiées dans le registre C++ pendant l'exécution. Un ancien objet GOAL chargé dans le même processus laisserait des entrées déjà actives. Un processus neuf remet ce registre à zéro ; l'ancien objet ne publie aucune source et `CityFire::render` sort immédiatement avant tout dessin/éclairage. Les anciennes particules continuent leur chemin `spawn`. Le feu du palais reste inchangé dans les deux versions, puisqu'il ne fait pas partie de la comparaison.

Ne pas employer `../setup_baseline.py` : ce script change la géométrie et les fenêtres pour une autre comparaison. Ne pas réutiliser les anciennes images après isolées dans la galerie : refaire une vraie paire avec le paquet final identique.

## Caméras natives déjà utilisées

Les poses exactes sont épinglées dans `camera-views.json`.

| Vue | Acteur | Position (m) | Cible (m) |
|---|---:|---|---|
| WCA | 46685 | 2261.5, 26.5, -18 | 2265.489, 26.8, -11.864 |
| WCB | 46673 | 1833, 49.8, -390 | 1840.85, 49.7, -387.19 |

Ces deux lampes ordinaires n'ont ni condition de mission ni masque de désactivation. Les grandes torches conditionnelles ne servent pas de référence.

## Audit au moment des captures

`capture_audit.py` lit le GAME actif, le moteur, tous les fichiers du paquet et tous les shaders/intérieurs présents. Il n'écrit que des copies et rapports sous `captures/`. Un deuxième relevé refuse une modification concurrente pendant la prise de provenance.

Exemple, depuis ce dossier, après une vraie capture WCA avant :

```powershell
C:\Python313\python.exe capture_audit.py snapshot --tag before-wca-r4 --version before --scene palace --view wca --image C:\chemin\capture.png --log C:\chemin\runtime.log --state C:\chemin\native-state.json
```

Refaire après avec `--tag after-wca-r4 --version after`, puis WCB. Le JSON `--state` est un relevé fourni par l'opérateur depuis le jeu, sans valeurs inventées :

```json
{
  "eye_m": [2261.5, 26.5, -18.0],
  "target_m": [2265.489, 26.8, -11.864],
  "fov_degrees": 0,
  "time_of_day": "REMPLACER PAR LE RELEVE NATIF EXACT",
  "render_size": [0, 0],
  "fresh_process": true,
  "audio_muted": true
}
```

Les zéros et le texte ci-dessus sont des **exemples à remplacer**, pas des réglages suggérés. Ajouter les extraits de REPL/log justifiant les relevés dans le même JSON si disponibles. Les métadonnées de caméra/heure/son sont signalées explicitement comme fournies par l'opérateur ; le script ne prétend pas les déduire des pixels.

```powershell
C:\Python313\python.exe capture_audit.py pair --before before-wca-r4 --after after-wca-r4
C:\Python313\python.exe capture_audit.py pair --before before-wcb-r4 --after after-wcb-r4
```

Les paires refusent un moteur, asset, FOV, cadrage, heure ou résolution différents. Le résultat indique `provenance-passed` et laisse **la validation visuelle en attente**. Examiner les quatre images : le récipient et le décor doivent coïncider ; seules la flamme, ses braises et sa lumière locale peuvent changer. Vérifier l'ancrage, l'occlusion par le bord du récipient et l'animation avant d'annoncer un gain visuel.
