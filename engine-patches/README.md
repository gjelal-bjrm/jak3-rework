# Correctifs du moteur OpenGOAL

Le dossier `engine-src/` n'est pas versionné dans ce dépôt : c'est un clone
séparé de https://github.com/open-goal/jak-project figé à la version **v0.3.6**
(commit `553a713a`), avec une branche locale `remaster-spargus` qui contient
toutes les modifications du moteur.

Ce dossier `engine-patches/` conserve ces modifications sous forme de correctif
Git, pour pouvoir les réappliquer sur une machine neuve.

## Reconstruire `engine-src/` depuis zéro

```bash
git clone --branch v0.3.6 --depth 1 https://github.com/open-goal/jak-project.git engine-src
cd engine-src
git checkout -b remaster-spargus
git am ../engine-patches/*.patch
```

Puis compiler avec `liquids-v3/build_engine.py` (MSVC 2019, voir le README
principal).

## Mettre à jour le correctif après une modification du moteur

```bash
cd engine-src
git add -A
git commit -m "Description de la modification"
git format-patch v0.3.6 -o ../engine-patches
```

Un fichier `.patch` par commit est produit ; ils s'appliquent dans l'ordre.
