# Hue Lab v0.4 — mises à jour autonomes depuis le Raspberry Pi

## Fonctionnement

- Le Raspberry Pi 2 conserve l'application sur `~/hue-lab`, accessible en Wi-Fi domestique à `http://10.0.0.12:8765/`.
- L'onglet **Mises à jour** affiche les versions GitHub et installée, et deux boutons : **Vérifier GitHub** et **Installer et redémarrer**.
- L'installation demande un code privé défini au premier déploiement. Le code n'est pas publié sur GitHub : seul son hachage PBKDF2 salé est stocké dans `~/.config/hue-lab/update-pin.json`.
- Le service `hue-lab-update@.service` est **indépendant** du serveur FastAPI : c'est un processus `systemd --user` ponctuel. `hue-lab-update-check.timer` vérifie GitHub chaque heure, mais n'installe jamais sans une action manuelle.
- Le travailleur sauvegarde `.hue_config.json` et `hue_settings.json`, vérifie la possibilité d'une mise à jour sans divergence, prépare les dépendances et les tests avant l'arrêt, effectue une fusion Git rapide, redémarre le service et vérifie `/api/state`. En cas d'échec du redémarrage, il restaure le commit précédent et les fichiers de configuration.
- Les courbes, la clé du pont Hue, les logs et les environnements virtuels ne sont **jamais versionnés**. Le clone Git et les futures mises à jour ne doivent pas les remplacer.
- Le script `updater/worker.py` est copié hors dépôt, dans `~/.local/share/hue-lab-updater/worker.py`, afin que le processus puisse se mettre à jour lui-même après une installation réussie.

## Migration initiale — téléphone uniquement, via Termux

Prérequis : le Raspberry fonctionne sous l'utilisateur `fred`, avec `hue-lab.service` (service utilisateur) démarré ; SSH est activé et `git` est installé. L'installation existante issue d'une archive doit être présente à `~/hue-lab`.

Dans Termux :

```sh
ssh fred@10.0.0.12
```

Puis, **une fois la v0.4 publiée sur `main`**, télécharger le script et le lancer sur le Raspberry (sans `sudo`) :

```sh
curl -fsSLo /tmp/hue-bootstrap-v04.sh https://raw.githubusercontent.com/fchautems/Hue/main/updater/bootstrap_pi.sh
bash /tmp/hue-bootstrap-v04.sh
```

Le script vérifie l'installation existante, demande un code privé d'au moins huit caractères, télécharge le dépôt Git dans un nouveau dossier, effectue les tests **avant d'arrêter Hue Lab**, sauvegarde l'ancienne installation dans `~/hue-lab-avant-v04-...`, conserve le venv et la configuration puis redémarre le service. En cas d'échec du redémarrage, il restaure automatiquement l'installation précédente.

Une fois les vérifications terminées, accéder à la page Hue Lab depuis le navigateur Android, onglet **Mises à jour**. Ensuite, Termux ne sera plus nécessaire pour les mises à jour ordinaires ; le dépannage via SSH reste disponible.

## Vérifications techniques

```sh
python -m unittest discover -s tests -q
node --check static/app.js
bash -n updater/bootstrap_pi.sh
```

Les tests en environnement isolé ne remplacent pas un essai physique sur le Raspberry Pi et les ampoules Hue. Ne pas rediriger le port 8765 sur Internet : le serveur de pilotage des ampoules n'a pas d'authentification globale. Le code de mise à jour protège seulement les opérations de déploiement.
