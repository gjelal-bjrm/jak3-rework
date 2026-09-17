# Revue native à effectuer après build/package

**État : non réalisée par le sous-agent. Aucun jeu lancé, arrêté ou déplacé.**
Le parent effectue l'installation commune et cette revue.

Lancer avec `OPENGOAL_TEST_MUTE=1`. Le log doit confirmer que chaque échantillon
stéréo est mis à zéro. Charger normalement WCA puis WCB, attendre trois secondes
pour laisser mourir les sprites émis avant le premier rendu moderne.

## Scènes

- WCB : `(start 'play (get-continue-by-name *game-info* "wascityb-seem"))`.
  Lampe AID 46673, centre de l'ancien effet `(1840.852, 48.817, -387.194)` m.
  Consulter `source-fit.json` pour le foyer ajusté. Caméra à environ
  `(1847, 49.8, -379)` vers `(1840.85, 49.7, -387.19)` pour voir le récipient
  et la flamme entière ; refaire de profil et légèrement en contre-plongée.
- WCA : `(start 'play (get-continue-by-name *game-info* "wascitya-seem"))`.
  Les grandes torches 37740/37741 sont à `(2313.869, 55.717, -276.159)` et
  `(2338.507, 55.717, -276.159)`. Leurs règles natives peuvent les désactiver.
  Ne pas les allumer artificiellement pour annoncer une validation normale.
- Revenir au palais : recette, ancrage des vasques et feu vu à travers l'eau
  identiques à la passe acceptée. Revenir ensuite en ville pour vérifier la
  transition et laisser la caméra normale, jouable.

## À contrôler réellement

- Dans le log : `City fire: accepted palace recipe`, puis `City fire live` avec
  nombres et identités de sources actives ; `City fire GPU` après douze mesures.
- Feu suffisamment ample, évoluant entre deux images espacées de 0,5 seconde.
- Pas d'intervalle visible au-dessus du récipient, ni sortie sous le fond.
- Pas de rectangle ou de globe de l'ancien sprite après trois secondes.
- Mur masquant correctement le volume ; visibilité à travers la réfraction de
  l'eau, à un endroit permettant réellement cette ligne de vue.
- Extinction et retour corrects si un événement de jeu stop/start intervient,
  puis passage WCA/WCB/palais sans foyer résiduel.

Les captures doivent conserver le contexte du récipient et les axes de caméra.
Un succès de compilation seul ne vaut pas validation visuelle.
