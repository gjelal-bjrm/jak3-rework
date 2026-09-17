# Accessoires du marché : reconstruction des volumes

Les cinq GLB de ce dossier sont prêts pour l'extraction Merc en staging. Ils
conservent les contrôles natifs de WCA/WCB, leur pivot, leurs dimensions et les
articulations `align`, `prejoint`, `main`. Toutes les faces restent pondérées sur
`main`, comme les objets d'origine. Aucun modèle du palais, effet d'eau, shader,
fichier FR3 ou DGO n'a été modifié par ce lot.

| Contrôle / fichier GLB | Triangles d'origine | Triangles auteur | Reconstruction visible |
| --- | ---: | ---: | --- |
| `market-crate-lod0.glb` | 132 | 6 304 | Planches épaisses individuelles, chanfreins usés, couvercle encastré, montants, traverses et chevilles d'assemblage. |
| `market-basket-a-lod0.glb` | 132 | 14 744 | Jarre ocre réellement creuse, col et lèvre arrondis, pied, épaulement modelé et filet de cordes séparé du corps. |
| `market-basket-b-lod0.glb` | 128 | 14 664 | Corbeille arrondie, montants et brins entrelacés, bord lié, remplissage de riz HD et cent grains en volume. |
| `market-sack-a-lod0.glb` | 144 | 12 728 | Sac ouvert affaissé, trois plis profonds, col incliné et replié, coutures et contenu ocre en retrait. |
| `market-sack-b-lod0.glb` | 192 | 11 014 | Sac fermé asymétrique, plis profonds convergents, col incliné, double ligature, nœud et queue de tissu retombante. |

Les formes sont reconstruites à partir de profils, surfaces, cordes et pièces
assemblées. Le résultat ne vient pas d'une subdivision du maillage original.
Les limites exactes du volume source sont reprises après construction ; le
nouveau relief reste dans l'emprise utilisée par le jeu.

La passe d'affaissement des sacs est détaillée dans `SACK-DRAPE.md`. Elle garde
la caisse, la jarre et la corbeille strictement identiques à leur première passe.

## Sources et reproduction

- `author_accessories.py` : auteur Blender reproductible ; produit les cinq
  GLB, les cinq `.blend`, les rapports individuels et les aperçus `*-authored.png`.
- `inspect_accessories.py` : aperçus `*-source.png` des sources originales,
  éclairage et caméra identiques à ceux des modèles reconstruits. Le cadrage
  utilise les limites natives indexées et exclut les sommets auxiliaires que
  l'import Blender peut présenter.
- `validate_accessories.py` : contrôle des exports par `import_market.validate_model`
  puis contrôle des limites, sommets inutilisés, triangles dégénérés, normales et
  résolution des matières. Rapport `accessories-import-validation.json`.
- `accessories-author-report.json` : inventaire auteur des cinq modèles.

Depuis la racine du prototype :

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python city-remaster/author_accessories.py
python city-remaster/validate_accessories.py
```

Une sélection est possible après `--`, par exemple `-- market-sack-b-lod0`.
Les fichiers de travail `.blend` contiennent aussi la caméra et les éclairages
d'inspection ; le GLB n'exporte que la mesh et son armature.

## Matières HD et fidélité

Chaque matériau est présent une seule fois dans le GLB, sous une primitive
indexée unique. Les images PNG sont embarquées dans les matériaux du GLB :
l'import Merc ne dépend donc pas d'un remplacement TextureDB séparé.

- `wood-hd.png` : 1 774 × 887, bois sec dans la palette beige/olive du marché.
- `market-cotton-hd.png` : 1 254 × 1 254, coton grossier et fibres poussiéreuses.
- `market-clay-hd.png` : 1 254 × 1 254, ocre sombre usé. Une première version
  trop claire a été conservée sous `market-clay-hd-v1.png`, puis remplacée dans
  les GLB par une génération plus proche de la matière d'origine.
- `market-rice-hd.png` : 1 254 × 1 254, grains gris/beige. La projection plane
  du remplissage évite la convergence des UV au centre de la corbeille.

Les nouvelles images ont été créées avec le **mode intégré ImageGen**, à partir
des images natives inspectées. Les prompts complets et chemins des images
générées sont dans `wood-provenance.json`, `accessory-textures-provenance.json`
et `accessory-textures-refinement.json`. Aucune correction de pixels manuelle
n'a été appliquée aux sorties retenues. Le raccordement a été demandé à la
génération ; l'égalité exacte des pixels des bords opposés n'est pas garantie.

## Validation réalisée et portée

Les cinq fichiers passent les contrôles du format natif : mesh monde identité,
JOINTS_0 unsigned byte, WEIGHTS_0 float, NORMAL/UV/COLOR présents, ordre et
matrices du squelette identiques, une primitive par matériau, PNG HD embarqués,
matériaux opaques ou MASK. L'écart maximal des limites indexées est inférieur
à 0,000000002 m. Aucun sommet auxiliaire inutilisé ni triangle de surface nulle
ne subsiste ; les normales sont unitaires.

Les aperçus Blender ont été inspectés et les défauts de couleur trop claire et
d'étirement central du remplissage ont été corrigés. **Ces aperçus ne sont pas
des captures du jeu.** Ce lot n'a exécuté aucune extraction, compilation,
installation ou lancement. L'extraction native, la visibilité à différentes
distances, les états de casse et le coût en jeu restent à vérifier dans le
test d'intégration coordonné par la tâche principale.
