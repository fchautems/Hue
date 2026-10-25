# Hue Lab — Interface Web Philips Hue (v0.3)

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
- Sélecteur unique : Manuel, Temps réel ou Accéléré (ce dernier pilote les ampoules physiques). Horloge 24 h, vitesses, pause et curseur de temps.
- Temps réel : suivi continu de la courbe locale, sans rallumer les ampoules volontairement éteintes par logiciel.
- Démarrage sur valeur fixe 10 % proposé pour chaque ampoule compatible via `powerup.custom` : écriture uniquement sur clic, puis relecture du réglage.
- Reconnexion : SSE Hue v2 et secours par sondage 2 s, transition adaptative 500–2 000 ms ; animation quotidienne par `dynamics.duration` si disponible.
- Diagnostics `dimming`, `dynamics`, `powerup`, statut SSE, délai observé de correction, modèle, Zigbee, logs et export JSON sans secret.
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

## Hue Lab v0.3 — Utilisation

1. Depuis le clone Git, effectuer `git pull`, puis relancer `demarrer_hue.bat`. La configuration locale de v0.2 est préservée.
2. Choisir le mode depuis le sélecteur en haut de page : **Manuel** (aucune courbe appliquée), **Temps réel** (courbes sur l'heure du PC), **Accéléré** (courbes sur l'horloge virtuelle, commande PHYSIQUE des ampoules).
3. Dans **Diagnostics**, pour une ampoule annonçant `powerup`, cliquer sur **Démarrage / powerup**, choisir **Luminosité fixe personnalisée**, 10 %, puis **Appliquer au matériel**. Lire le résultat de la vérification par relecture et tester une coupure avec l'interrupteur.
4. En Temps réel, à la reconnexion, la consigne de la courbe est appliquée par une transition courte et douce. La première lumière dépend de la mémoire et du firmware de l'ampoule.
5. Les diagnostics donnent le statut des événements SSE et la latence entre observation et envoi de commande ; ils ne mesurent pas le délai optique réel.

Manuel et Temps réel sont mémorisés. Accéléré est réinitialisé en Manuel au redémarrage pour éviter un pilotage intempestif. Le double allumage à 100 % est reporté à une éventuelle v0.4.

**Tests :** 27 tests Python hors réseau sur moteur v0.3 adapté et routes API, et `node --check` sur le JavaScript ; intégration textuelle avec la source v0.2 vérifiée. Pas de test avec tes trois ampoules ni de test complet du projet sur Windows dans cet environnement.

## Raspberry Pi — mises à jour autonomes (v0.4)

Voir [README_V04.md](README_V04.md) pour la migration initiale via Termux, le bouton de mise à jour GitHub, les sauvegardes et le retour arrière.

## Hue Lab v0.5 — Manuel / Auto par lampe

Chaque lampe possède son propre mode **Manuel** ou **Auto**. Le choix de l'heure réelle ou de la simulation accélérée ne s'applique qu'aux lampes en Auto. Les courbes existantes sont conservées à l'installation et les réglages individuels restent locaux.

Consulte [README_V05.md](README_V05.md) pour les étapes de mise à jour depuis l'interface du Raspberry et les limites des transitions selon les ampoules.

## v0.5.1 — Ergonomie mobile des courbes

L’éditeur présente une courbe interactive et des pastilles horaires accessibles au doigt, avec des réglages précis HH:MM / luminosité, l’ajout et la suppression de points, ainsi qu’une sauvegarde et une annulation explicites. La simulation est repliable sur téléphone. Aucune modification du moteur Hue ou des profils enregistrés n’est nécessaire. Détails dans [README_V051.md](README_V051.md).

## v0.5.2 — Courbe simple progressive

L’onglet **Courbes horaires** permet de choisir entre la courbe personnalisée à points et une **courbe simple** : début/fin de montée, début/fin de descente, luminosités minimale et maximale. Les rampes sont monotones, arrondies et continues, avec un plateau de jour et un minimum nocturne. La courbe personnalisée existante n’est jamais écrasée. [Détails](README_V052.md).
