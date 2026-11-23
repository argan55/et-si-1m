# RTK : économiser des tokens sur les commandes

`rtk` est installé sur cette machine. Il compresse la sortie des commandes avant que tu la lises.

- Préfixe tes commandes shell par `rtk` : `rtk git status`, `rtk git diff`, `rtk git log`, `rtk pytest`, `rtk pip install …`, `rtk ls`, `rtk grep …`.
- Pour lire ou chercher dans des fichiers depuis le shell : `rtk read <fichier>`, `rtk grep <motif>`, `rtk find <motif>`.
- Si une commande échoue à cause de `rtk` (commande non prise en charge), relance-la sans le préfixe.
