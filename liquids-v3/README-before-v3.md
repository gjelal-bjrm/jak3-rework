# Jak 3 — prototype remaster de l’arène de Spargus

Première zone jouable du tutoriel, checkpoint `game-start`. Prototype visuel fidèle, isolé de l’installation habituelle. Vérifié dans OpenGOAL v0.3.6 le 16 septembre 2026.

## Jouer et comparer

1. Double-cliquer sur **Jouer-REMASTER.cmd** dans ce dossier.
2. Attendre quelques secondes : le jeu place Jak directement dans le tutoriel, à 09:00, avec les textures et l’éclairage modifiés.
3. Observer les plaques métalliques juste sous Jak et les panneaux des échafaudages.
4. Fermer cette fenêtre, puis lancer **Comparer-ORIGINAL.cmd** pour la même zone, la même heure et les mêmes réglages avec les graphismes originaux.

**Le lanceur OpenGOAL habituel utilise toujours l’installation originale.** Utiliser les deux fichiers ci-dessus pour ce test. Une seule variante du prototype peut être ouverte à la fois. Les deux profils ont leurs propres sauvegardes ; chaque lancement revient au point de test.

Le lancement emploie Python et le moteur déjà présents sur cette machine. Aucune extraction ni compilation n’est nécessaire pour jouer. Pour les commandes clavier/manette, consulter le menu des contrôles du jeu.

## Changements visibles

- **Huit textures retravaillées à partir des originales**, avec une résolution multipliée par quatre sur chaque axe : métal des plateformes, panneaux, parois, roche et sol en grès. Les motifs et la palette restent proches du jeu.
- **Treize remplacements** répartis entre `wasstada-tfrag` et `wasstadb-tfrag`. Ce second ensemble contient notamment le sol du tutoriel : son inclusion était indispensable pour rendre le résultat visible dès le départ.
- **Première passe d’éclairage local** : soleil chaud, lumière de ciel plus froide, ombres moins uniformément orange et éclairage orienté selon les faces du décor. Les couleurs de lumière du niveau sont également rééquilibrées.
- Géométrie, collisions, personnages et mécaniques conservés pour ce test. Aucun nouvel objet ajouté.

## Portée de l’éclairage

Les shaders des décors `tfrag3`, `tie_wind` et `etie_base` utilisent une normale calculée à partir de la géométrie et conservent une part de l’éclairage précalculé comme approximation d’occultation. L’effet est limité spatialement autour de l’arène. Les couleurs d’ambiance du niveau affectent aussi l’éclairage des acteurs.

Il s’agit d’une première passe visuelle sur le moteur existant. **Une refonte complète avec nouvelles ombres dynamiques, éclairage indirect et matériaux à relief reste à réaliser.** Le gros halo jaune près de Jak est le marqueur du tutoriel déjà présent dans l’original ; il ne démontre pas un nouvel effet de lumière.

## Vérification

- Extraction réussie de `WASSTADA` et `WASSTADB`, avec les treize remplacements détectés.
- Compilation GOAL réussie après correction du lancement direct du tutoriel.
- Les deux variantes démarrent et produisent une capture réelle 1920 × 1080 depuis le moteur, avec anticrénelage MSAA ×4.
- `comparison/arena-original.png` et `comparison/arena-remaster.png` montrent la même caméra et une heure figée à 09:00. Les particules et la lave peuvent différer entre les lancements.
- Intégrité vérifiée des fichiers des variantes et correspondance de la référence avec l’installation originale. L’alpha PS2 à 128 a été conservé sur les textures.
- Vérification du démarrage et du rendu, sans parcours complet du tutoriel ni mesure de performances. La fonction de capture native signale une erreur OpenGL dans les deux variantes, tout en produisant les PNG correctement.

Voir `validation-report.json`, `texture-validation.json`, `extraction.log` et `build.log` pour les résultats techniques.

## Fichiers pour continuer le travail

- `art/masters/` : sources haute résolution générées ; provenance dans `texture-manifest.json`.
- `data/custom_assets/jak3/texture_replacements/` : textures intégrées au jeu.
- `arena-lighting.glsl` et `apply_lighting.py` : éclairage et script d’application.
- `apply_boot.py` : lancement direct et capture automatique, identiques dans les deux variantes.
- `variants/` : fichiers rendus interchangeables ; `launch.py` vérifie leur intégrité avant chaque lancement.

Pour reconstruire : intégrer les textures, appliquer l’éclairage et le démarrage, extraire les deux niveaux, compiler le jeu, puis exécuter `prepare_variants.py` avec les fichiers modifiés présents dans `data`. Ce script de préparation est réservé à la reconstruction ; les lanceurs suffisent pour comparer.
