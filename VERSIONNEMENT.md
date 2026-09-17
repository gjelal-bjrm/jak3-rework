# Versionnement du prototype

Dépôt GitHub : https://github.com/gjelal-bjrm/jak3-rework

## Ce que Git conserve

- Les scripts Python, les shaders GLSL, les fichiers GOAL modifiés et toute la
  documentation Markdown.
- Les manifestes JSON légers (validation, inventaires, positions).
- Les sources Blender `.blend` et les modèles `.glb` exportés, via **Git LFS**.
- Les textures HD remasterisées des dossiers `masters/`, via **Git LFS**.
- Le correctif du moteur dans `engine-patches/` (voir son README).

## Ce que Git ne conserve pas, et pourquoi

| Exclu | Raison |
|---|---|
| `data/`, `variants/`, `routes/`, `profiles/`, `*.fr3`, `*.cgo`, `*.dgo` | Données issues de l'ISO du jeu, sous copyright. Le dépôt est public. |
| `engine-src/` | Dépôt Git séparé (clone d'OpenGOAL v0.3.6, branche `remaster-spargus`). |
| `engine-build/`, `runtime/`, `toolchain/`, `*.exe` | Résultats de compilation, se reconstruisent. |
| `*patch*.json`, gros JSON `native`, `surfaces`, `objects` | Extractions intermédiaires de plusieurs centaines de Mo, régénérées par les scripts. |
| `**/staging/`, `**/backup/`, `**/before/`, `*.blend1` | Copies de travail et sauvegardes automatiques. |
| `*.png` hors `masters/`, `*.gif` | Captures d'écran de vérification, gardées en local. |

## Sauvegarde hors ligne

Le dossier `..\..\sauvegardes\` contient une archive ZIP de tout ce qui est
versionné, générée à chaque étape importante. À copier sur un disque externe
ou un espace cloud personnel. Les données du jeu se régénèrent à partir de
l'ISO avec le lanceur OpenGOAL officiel.

## Gestes quotidiens

```bash
git status                 # voir ce qui a changé
git add -A                 # préparer toutes les modifications
git commit -m "Message"    # enregistrer une étape
git push                   # envoyer sur GitHub
```

Ne jamais faire `git checkout` ou `git reset --hard` dans `engine-src/` sans
avoir d'abord commité sur la branche `remaster-spargus`.
