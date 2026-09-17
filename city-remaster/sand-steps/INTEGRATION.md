# Intégration des pas dans le sable

`register.py` ne compile rien et ne contrôle pas le jeu. Après la compilation de
`effect-control.o` par le responsable de la session :

```powershell
C:/Python313/python.exe city-remaster/sand-steps/register.py
C:/Python313/python.exe city-remaster/sand-steps/register.py --apply
```

La première commande prépare uniquement les candidats et preuves dans `staging`.
La seconde remplace les routes remaster palais/arène et le `GAME.CGO` actif,
puis met à jour les deux hashes de routes dans `runtime-manifest.json`.
Elle ne modifie pas le moteur ni les variantes de comparaison.

Chaque route conserve sa propre sauvegarde dans `before/routes` : les objets de
démarrage du palais et de l’arène sont différents. Un seul bloc, `effect-control`,
peut changer ; les **489 autres objets** restent identiques, avec leurs en-têtes,
ordre et padding. Le remplacement inverse doit restituer l’archive entière exacte.
Le script refuse également les changements étrangers déjà présents dans le live.

Les sources sont comparées aux trois insertions exactes : table des surfaces et
`helper.gc` après la déclaration de contrôle, `hook.gc` dans la méthode par
surface, puis `npc-hook.gc` après le bloc natif `ecf0` de `do-effect`,
avec hashes et inverse. L’objet doit être plus récent que les sources et contenir
les symboles privés attendus. La table est liée aux exports et aux sondes de
`surface-validation.json`. Cette vérification complète la compilation native ;
elle ne remplace pas le contrôle du journal du compilateur.

`installed.json` lie les candidats, sources, preuves et snapshots du manifeste.
`models-v2/verify_package.py` revérifie ces fichiers, les blocs réels des deux
archives et les variantes original/V1 protégées. Aucun `GAME.CGO` n’est ajouté au
registre des variantes : le choix de route reste géré par `launch.py`.

Les sept essais de `register-validation.json` sont exécutés en mémoire : aller-
retour inchangé, remplacement/inverse, refus d’une mutation étrangère pour chaque
route, et refus d’une archive tronquée. Ils ne constituent pas une validation
visuelle des particules.
