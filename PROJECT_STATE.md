# PROJECT_STATE — Philips Hue Web

Mise à jour : 2026-10-23

## État vérifié
- Prototype CLI antérieur (`hue.py`) validé par l'utilisateur : découverte du pont `10.0.0.2`, appairage et détection de 3 ampoules (`Couloir - entrée`, `Salon`, `Couloir - douche`). L'utilisateur a validé le proof of concept.
- Nouveau projet Hue Web v0.1 développé **en espace isolé**, sans accès au disque `F:` du PC et sans possibilité de test sur les vraies lampes.

## Changements
- Interface Web locale FastAPI (port 8765), lecture de la clé déjà enregistrée dans `.hue_config.json`.
- Contrôle marche/arrêt et luminosité, découverte automatique des capacités déclarées par l'API Hue v2.
- Simulation analogique 24 h avec lecture/lecture accélérée et profils de luminosité séparés par ampoule ; interpolation smoothstep continue.
- Automatisation réelle opt-in, simulation sans commande réelle par défaut.
- Supervision Zigbee par sondage, correction après reconnexion si remontée, test secteur armable (mesure entre observations Zigbee), logs et exports diagnostics sans clé API.
- Paramétrage `powerup` manuel (pas de mise à jour automatique de la mémoire embarquée).

## Contrôles
- 13 tests unitaires Python exécutés localement, ainsi que contrôle de syntaxe JS et vérification HTTP via un pont simulé. Résultat : OK.
- Vérification visuelle dans Chromium des deux écrans (tableau de bord, horloge/courbes) avec données simulées : OK. Les capacités réelles des lampes restent à mesurer.
- Test en environnement réel : **à faire sur le PC Windows**.

## Blocages et limites
- Pas d'accès direct à `F:\_Projets\Hue` depuis cet environnement ; fournir un ZIP à extraire dans le répertoire existant.
- `powerup` dépend des modèles et du firmware ; n'est pas capable de lire l'heure PC avant alimentation.
- La reconnexion Zigbee détectée par polling peut prendre du temps ; ce n'est pas une preuve de coupure secteur.
- L'heure accélérée ne doit pas être confondue avec une garantie de fluidité réelle du matériel.

## Publication
- Code source v0.1 préparé pour un premier commit public sur `https://github.com/fchautems/Hue` (`main`).
- Les données locales sensibles (`.hue_config.json`, `hue_settings.json`, `logs/`) et les caches sont exclus du contrôle de version.

## Prochaine action
- Cloner ou mettre à jour le dépôt sur le PC, démarrer l’application, exporter les diagnostics des 3 modèles et tester la remise sous tension ; ajuster ensuite la stratégie de démarrage selon les capacités réellement observées.

## Correctif du lancement Windows — 2026-10-23
- Signalement utilisateur : `ModuleNotFoundError: No module named 'fastapi'` lors du lancement de `demarrer_hue.bat`.
- Lanceur : vérification de Python et des modules `fastapi`, `uvicorn`, `requests`, `jinja2` ; installation automatique via `python -m pip install -r requirements.txt` si un module manque ; contrôle final avant démarrage.
- `Jinja2` ajouté à `requirements.txt` pour les templates HTML ; consignes de démarrage du `README.md` mises à jour.
- Vérification : cohérence statique du lanceur et des dépendances. **Test réel du batch sous Windows et du pont Hue à effectuer sur le PC utilisateur**. Les 13 tests précédents concernent la version initiale.
- Prochaine action : `git pull` puis double-clic sur `demarrer_hue.bat` et vérification de http://127.0.0.1:8765.
