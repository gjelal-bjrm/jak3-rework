# Cadres des fenêtres — lot WCA/WCB

**278 cadres métalliques** refaits : WCA arbre0/prototype3 (145 instances),
WCB arbre0/prototype10 (133). Quatre LOD conservés ; base FR3 commune ENV001.

Le volume comprend des coins extérieurs chanfreinés, une moulure en métal
autour de l’ouverture, un appui saillant avec profil de rejet d’eau et quatre
fixations au LOD proche. Le corps reste dans les bornes natives ; l’ouverture,
les faces de vitre et leur réflexion d’origine restent intactes. Les matériaux,
UV issus du cadre d’origine et palettes horaires sont conservés.

Les grands encadrements arqués WCA prototype9/WCB prototype1 sont exclus :
ils comportent un fond sombre et ne sont pas les fenêtres étroites confirmées.
Les autres familles de fenêtres restent donc à traiter séparément.

## Livrables

- `wascitya-patch.json` : 19 720 faces retirées, 132 385 ajoutées tous LOD.
- `wascityb-patch.json` : 18 088 faces retirées, 121 429 ajoutées tous LOD.
- `author.py`, `export.py`, `validate.py` : production Blender et contrôles.
- `*-lod0-before.png`, `*-lod0-after.png`, `*-lod0.blend` : comparaison et scènes
  représentatives des deux familles. Les vues montrent le cadre seul, sans
  synthétiser une nouvelle vitre.
- `author-report.json`, `validation.json` : provenance et résultats.

**30 contrôles d’auteur passent** : identités natives, clés disjointes du lot
stucco, matériaux/groupes, normales unitaires, poids de couleur convexes,
triangles non dégénérés, respect du rayon maximal des instances et absence
d’obstruction de l’ouverture sur les quatre LOD.

Le chanfrein automatique a été contraint aux dimensions natives après détection
d’un débord aux coins inférieurs ; les modèles finaux passent le contrôle de rayon.
Les détails de relief restent à l’intérieur de ce rayon d’origine.

Ces patches doivent être **combinés** au lot architecture et végétation avant
import sur la base ENV, pas appliqués séquentiellement avec d’anciens indices.
Aucun FR3 n’a été importé ou déployé ici. L’audit natif du lot combiné et la
validation visuelle en jeu restent nécessaires ; les images Blender n’en tiennent
pas lieu.
