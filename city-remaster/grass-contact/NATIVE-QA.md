# Contact de l'herbe — validation native

Le lancement du 16 septembre enregistre la sortie audio muette. Le journal
contient une transmission réelle de Jak au shader : position
1501.818 / 29.010 / -328.268, région WCB, trois échantillons actifs. Le hook
utilise la position de contact au sol, pas celle de la caméra.

Les captures `grass-contact-rest-v1.png` et `grass-contact-bend-v1.png` dans
le dossier screenshots du profil remaster-palace montrent une même touffe du
marché, avec Jak éloigné puis au contact. Ce placement utilise le REPL de test ;
il ne constitue pas un parcours manuel complet à la manette. Le personnage
masque une partie des brins dans la seconde image.

`gpu-validation.json` vérifie directement le shader GLSL complet empaqueté sur
GPU : racines inchangées, déplacement local, absence d'effet à distance ou à un
autre étage, récupération monotone puis retour exact au vent seul après une
seconde. Les contacts n'agissent ni sur le palais ni sur ses plantes.

Cette première implémentation suit Jak. Les contacts des PNJ sont une extension
ultérieure ; ils ne sont pas annoncés comme fonctionnels.
