# Hue Lab — Interface Web Philips Hue (v0.2)

Application locale Python + HTML permettant de piloter des ampoules Hue, simuler 24 h en accéléré, adapter leur luminosité et diagnostiquer leur comportement après une coupure de courant.

## Installation Windows — tout depuis l'interface

1. Récupérer la dernière version du dépôt dans `F:\_Projets\Hue` et conserver les fichiers existants du dossier, notamment `hue.py` (prototype CLI). Si le dossier est déjà un clone Git, `git pull` récupère les mises à jour du code ; cette commande **n'est pas nécessaire pour l'appairage**.
2. Double-cliquer sur `demarrer_hue.bat` : les dépendances manquantes sont installées automatiquement, puis le serveur est lancé.
3. Ouvrir `http://127.0.0.1:8765` dans le navigateur. Au premier lancement, l'onglet **Connexion au pont** s'affiche automatiquement :
   - Cliquer sur **Rechercher le pont** (ou utiliser l'adresse IP proposée `10.0.0.2` si la découverte Internet n'aboutit pas).
   - Cliquer sur **Démarrer l'association** et appuyer sur le gros bouton du pont Hue.
   - Le programme retente automatiquement pendant 45 secondes, vérifie la clé, crée la configuration locale et affiche les ampoules.

**Aucune édition de fichier ni appel à `python hue.py connect` n'est nécessaire.** L'association physique au pont reste obligatoire une seule fois pour autoriser l'application.

## Configuration et sécurité

- `hue_config.example.json` est **versionné sur GitHub**. Il contient l'adresse IP déjà connue du pont, sans clé secrète. Il sert de modèle au premier démarrage.
- `.hue_config.json` est **créé automatiquement sur le PC** et contient ensuite la clé d'application fournie par le pont. **Il est exclu de GitHub** via `.gitignore` pour ne pas rendre publiques les commandes de tes lampes.
- Quand une clé est absente, vide ou refusée, ouvrir l'onglet **Connexion au pont** et refaire l'association directement dans la page.
- `hue_settings.json` (courbes personnalisées) et `logs/hue.log` (journal) restent aussi locaux.
- Le serveur écoute par défaut uniquement sur `127.0.0.1` et refuse les adresses externes pour l'association. Les requêtes vers le pont utilisent son HTTPS local sans validation du certificat pour ce prototype.

## Fonctions

- Tableau de bord : on/off, luminosité et connexion Zigbee déclarée par le pont.
- Courbes individuelles avec interpolation douce et continuité à minuit.
- Horloge analogique 24 heures, simulation à vitesse accélérée et mode virtuel sans commandes physiques par défaut.
- Automatisation temps réel à activer explicitement, sans rallumer volontairement les ampoules éteintes par logiciel.
- Diagnostics `dimming`, `dynamics`, `powerup`, modèle, Zigbee, journal et export JSON sans clé.
- Tests de remise sous tension : mesures du temps entre les observations de connectivité Zigbee.

## Limitation physique importante

Un interrupteur classique coupe totalement l'alimentation de l'ampoule. Elle ne peut pas interroger le PC avant de se reconnecter. Le comportement initial dépend de son paramètre `powerup` embarqué. L'application peut corriger la luminosité après reconnexion, mais ne peut pas garantir qu'elle sera exacte dès la première milliseconde.

## Dépannage

- Si aucun pont n'est détecté, saisir une adresse locale valide (par exemple `10.0.0.2`) sur la page de connexion.
- Si le pont refuse l'association, appuyer sur son bouton pendant la phase d'attente, puis relancer si nécessaire.
- Le lanceur Windows indique les erreurs d'installation éventuelles et conserve la fenêtre ouverte en cas d'échec.
- Les logs sont dans `logs/hue.log` ; ne pas publier les logs sans les relire.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Les tests de l'appairage sont effectués avec un faux pont. L'appairage sur le matériel réel reste à valider.

## Fichiers

- `hue_web.py` : serveur Web FastAPI, appairage, supervision, diagnostics.
- `hue_core.py` : logique de courbe et de temps virtuel.
- `templates/index.html`, `static/app.js`, `static/style.css` : interface Web.
- `hue_config.example.json` : modèle de configuration versionné sans secret.
- `.hue_config.json` : configuration privée créée automatiquement et ignorée par Git.
- `tests/` : tests unitaires et des routes HTTP.
- `PROJECT_STATE.md` : état vérifié du projet et prochaines actions.
