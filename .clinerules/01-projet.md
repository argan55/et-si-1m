# Règles du projet (lues par Cline)

## Source de vérité
- Avant toute tâche, lis `AGENTS.md` à la racine du projet. C'est la référence : but du projet, spec, conventions, règles et section « État ».
- Respecte les règles de `AGENTS.md`. (`CLAUDE.md` ne contient que des réglages propres à Claude Code : ignore-le.) En cas de doute, elles priment sur ces règles-ci.
- Ignore ce qui ne concerne que Claude Code : sous-agents, skills (`.claude/`), choix du modèle Claude, commandes `/`. Tu n'y as pas accès.
- Ne devine jamais le contenu d'un fichier : ouvre-le avant d'en parler ou de le modifier.

## Façon de travailler
- Réponds en français.
- Fais une seule tâche bien délimitée à la fois. Si la demande touche beaucoup de fichiers ou l'architecture, dis-le et propose de la laisser à Claude Code.
- Après une modification de code, lance les tests s'il y en a (`pytest`) et indique le résultat.
- Ne touche pas aux secrets (`.env`, clés API) et ne les affiche jamais.

## Passation avec Claude Code
- À la fin d'une tâche, mets à jour la section « État » de `AGENTS.md` : ce qui a été fait, ce qui reste, les problèmes connus.
- Marque tes lignes avec « (Cline) » pour que Claude Code sache quoi relire.
- Ne réécris pas le reste de `AGENTS.md` sans qu'on te le demande.
