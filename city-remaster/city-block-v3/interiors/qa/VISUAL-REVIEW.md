# Exécution réelle des shaders d'intérieur sur GPU

`qa_gpu.py` a compilé et lié les deux shaders fournis par root, puis dessiné les
binaires des pièces et les trois acteurs dans un FBO OpenGL. Le contexte WGL
est caché. Aucun jeu n'a été lancé ni manipulé. Les fichiers des shaders et des
modèles sont restés inchangés.

Résultat technique : **10 contrôles réussis**, OpenGL 4.6, RTX 3080 Ti. L'alpha
natif 128/255 est correctement compensé par l'alpha de sommet égal à 2 ; les
texels transparents sont rejetés. Le changement de pose modifie 2 659 pixels
dans le salon et 11 351 pixels dans la pièce de conversation.

Les images `lounge-pose-0.png` et `conversation-pose-0.png` ont été inspectées :
corps complets et cohérents, mobilier volumique visible, visages texturés,
couleurs natives conservées, gestes discrets. Il ne s'agit pas d'une capture
du jeu : la caméra de ce test est synthétique et utilise les vrais shaders.

## Corrections de placement transmises à root

- Le tapis et ses motifs culminent à Y=0,0425–0,057 m. Les habitants debout
  posés à Y=0 ont une partie des semelles enfouie ; utiliser environ Y=0,058 m.
- L'acteur assis déplacé de +0,09 m a son assise à 0,6624 m, cohérente avec le
  dessus du coussin à 0,665 m. Ses semelles sont alors à 0,09 m, légèrement
  au-dessus du tapis. Une assise abaissée de quelques centimètres ou un
  repose-pieds doit résoudre le support des chaussures.

Ces remarques n'ont pas été masquées par les contrôles GPU réussis. Les
ouvertures dans les façades, les ancrages mondiaux et la visibilité native
restent à contrôler dans le jeu après intégration.
