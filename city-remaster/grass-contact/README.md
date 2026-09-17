# Herbe : contact local avec Jak

## Règle de végétation

Les touffes reconstruites doivent conserver leurs espèces, silhouettes et
couleurs de Spargus, avec de vrais brins galbés. Elles accompagnent le vent et
s'écartent au passage du personnage, puis se redressent. Ne pas appliquer cette
souplesse aux cactus, aux troncs ou aux palmiers. Leur position et les collisions
natives restent inchangées.

Cette première interaction concerne **Jak**, WCA/WCB et exclusivement la texture
privée `market-shrub-orange-v1`. Les 69 touffes acceptées et les 1 482 touffes du
nouveau lot partagent cette texture et la convention V=4096 à la racine / V=0 à
la pointe. Les cactus `city-cactus-green-v2` et `wascity-cactus-flower` sont exclus.
Les NPC n'ont pas de contact d'herbe ajouté dans ce lot.

## Fonctionnement

Un seul raccordement dans `logic-target.gc::joint-points` publie la position
physique de Jak et la hauteur réelle du contact au sol. Il exige le personnage
cible, le contact au sol et un niveau de ville autorisé ; il exclut l'eau et le
pilotage. Aucune position de caméra, heuristique de couleur ou lecture à offsets
de mémoire du jeu n'est utilisée.

`GrassContacts.h` copie au plus 16 positions avec un mutex entre jeu et rendu.
Le shader écarte doucement les brins dans un rayon de 0,78 m, jusqu'à 28 cm
horizontalement et 8 cm vers le bas aux pointes. La racine est mathématiquement
immobile. Les positions sont échantillonnées à 16 Hz ; le plus fort contact
s'applique, sans addition des passages ou des échantillons immobiles. Le retour
est lissé et devient exactement nul après une seconde. Un changement de région,
une interruption des mises à jour ou une téléportation réinitialise l'historique.
La hauteur rejette une végétation située sur un autre étage.

Le mode du palais et le vent accepté restent intacts après l'inverse strict du
nouveau code. Le binder réinitialise le nombre de contacts à zéro pour les autres
matériaux et les autres niveaux. Il ne modifie aucun shader de palmiers.

## Preuves et état

- `apply.py` : préparation par défaut, `--apply` explicite, snapshots complets
  des six sources modifiées et inverse exact ; moteur/data identiques.
- `validation.json` : racines fixes, rayon et hauteur bornés, aucune amplification
  en doublant les contacts et retour monotone jusqu'à zéro.
- `verify_gpu.py` / `gpu-validation.json` : **14 contrôles PASS sur le vrai shader
  complet empaqueté**, compilé et exécuté par la RTX 3080 Ti dans un contexte WGL
  caché, avec récupération des positions par transform feedback. Racines, autres
  étages et points éloignés identiques bit pour bit ; retour exact au vent seul à
  une seconde ; aucun effet des contacts sur les modes 0 et palais 1. Déplacement
  maximal mesuré 29,124 cm, incluant l'arrondi float aux coordonnées de Spargus.
  Aucun fichier ni processus du jeu n'a été modifié par ce contrôle GPU.
- `logic-target.o` compilé par root, 100 609 octets, SHA256
  `bda9445ece1b1aa376c2780227e8beb938c6b5d13adbf6b8b94d4b2a72cd16ab`.
- `register.py` installe uniquement cet objet dans chaque route GAME actuelle.
  Les 489 autres blocs, dont `effect-control` et les effets d'eau, sont préservés
  octet pour octet. L'inverse restaure intégralement la route poussière précédente.
  Une mutation injectée dans un autre objet a été refusée par l'audit.
- `installed.json` garde les deux prédécesseurs distincts et leurs preuves. Les
  anciens enregistrements poussière ne sont ni écrasés ni relâchés.

**À valider en jeu :** shader compilé, passage dans une touffe, sortie et
redressement, racines sans glissement, cactus/palmes/palais inchangés. La première
liaison d'un contact à un draw d'herbe écrit `Remaster grass contact: Jak position`
dans le log. Cela prouve l'arrivée d'une vraie position dans le shader ; une
capture du mouvement reste nécessaire pour conclure sur son aspect.

Les contrôles de paquet doivent suivre le packaging root : le nouveau shader
et le binaire recompilé doivent être enregistrés avant le PASS final.
