# Maisons pilotes de la ville basse : retour à la géométrie d'origine

Les deux maisons pilotes (WCA, TIE arbre 1, instances 1 et 2) portaient cinq ouvertures collées à
un escalier ; la pièce d'angle ressortait dans le vide de l'escalier. À la demande de l'utilisateur
(« plus de maisons sous des escaliers »), `restore.py` :

1. exporte les faces actuelles des groupes de ces deux maisons (`native-pilot-current.json`) ;
2. écrit un patch qui retire toutes leurs faces remodelées (17 734) et remet les 948 faces natives de
   l'export d'avant remodelage (`environment/architecture/wascitya-native.json`) ;
3. l'applique avec le bridge sur la sortie R4 et passe l'audit de préservation (163 contrôles) ;
4. installe le FR3 dans `data/` et `variants/remaster/`, puis regénère les intérieurs avec les
   **7 fenêtres finales** (`interiors/window-anchors-final.json`) : quartiers est, ouest, bas, nord
   de la ville basse et trois bâtiments autour du marché.

Les plaques de bronze de la maison 2 (TIE arbre 0, révisions ornaments) ne font pas partie de ces
groupes et restent en place. Les dossiers historiques R1 à R4 sont conservés tels quels.
