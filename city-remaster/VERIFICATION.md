# Vérification des descendants de la ville

Lancer `models-v2/verify_package.py` **après** le package et le lancement natif
final. Il appelle `verify_descendants.py` en lecture seule. La vérification
complète n’est pas lancée pendant le staging.

## Chaîne reconnue

1. `installed.json` : modèles Merc du marché, candidats et audit natif.
2. `static-installed.json` : supports, deux palmiers et buissons du marché.
3. `environment/foliage/installed.json` : treize autres palmiers WCB.
4. `environment/installed.json` : textures régionales après les nouveaux modèles.

Chaque base doit être exactement la sortie validée du maillon précédent.
Les rapports de maillage doivent conserver Merc, collisions, textures d’origine,
instances de vent et triangles non sélectionnés ; avant/après/patch et rapport
natif détaillé sont vérifiés par SHA256.

WASWIDE est ancré séparément dans
`environment/baselines/waswide/baseline.json` : données originales actives,
deux copies immuables et variantes original/V1 identiques. Cette base devient
ensuite un prédécesseur autorisé de la passe de textures.

La passe ENV vérifie les snapshots du stage, l’audit et son parseur, le catalogue
de génération copié, les pixels RGBA préparés, les sélections exactes et les
hashes intégraux géométrie/Merc préservés. Les PNG de travail peuvent évoluer
ensuite : les pixels installés restent ceux du stage immuable. Les anciens lots
ENV sont suivis par leurs copies de manifeste de retour arrière.

## Changements moteur bornés

- `material-response.json` doit partir exactement du header final du correctif
  de repère du vent. Un inverse de trois modifications explicites (régions,
  seuil HD, liste de matériaux) restitue tout le header précédent ; la fonction
  `bind` et la classification du palais restent donc identiques.
- Les insertions du repère du vent et du ciel ont un inverse exact, comparé à
  leurs hashes avant modification. Les nouvelles sources ciel doivent être
  identiques aux fichiers auteurs.
- Les deux shaders `spargus_clouds` sont enregistrés avec
  `apply_shaders.py --clouds-only`. Le package remaster normal complète ensuite
  leurs copies et hashes finaux.

Ces preuves vérifient la composition des données et le périmètre du code.
Elles n’approuvent ni le rendu visuel, ni les performances, ni les collisions
de tous les nouveaux objets en situation de jeu.
