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

## v0.2 — Parcours autonome de connexion — 2026-10-23
- **Décision durable :** toute découverte / association doit s'effectuer dans l'interface Web, sans CLI ni manipulation du fichier de configuration.
- Ajout du modèle public `hue_config.example.json` (IP connue du pont, clé vide) et de la création automatique de `.hue_config.json` sur le PC ; vraie clé jamais suivie par Git.
- Ajout des routes `GET /api/setup/status`, `GET /api/setup/discover`, `POST /api/setup/pair` ; refus des IP non privées, association via le bouton physique, validation de la clé par appel à `/clip/v2/resource/light`, écriture atomique de la config et démarrage du contrôleur après succès.
- Ajout d'un onglet de connexion avec découverte, sélection ou IP manuelle, et attente automatisée pendant 45 secondes de l'appui sur le bouton. Écran affiché à la première installation ou en cas de clé refusée.
- L'appairage coupe les automatismes existants lors d'un changement de client et réinitialise les caches pour éviter de commander des appareils obsolètes.
- Tests : **20 tests Python réussis**, dont cas 101, clé invalide, IP invalide, routes Web et absence de clé dans les réponses. `node --check` sur JS OK. Écran affiché avec Chromium en environnement isolé, sans erreur JS ; accès HTTP via navigateur local non disponible à cause d'une restriction du navigateur de test.
- **Non vérifié :** appairage et redémarrage Windows avec un pont Hue réel. Contrôle à effectuer sur le PC utilisateur.
- **Prochaine action :** synchroniser le dépôt, double-cliquer `demarrer_hue.bat` et appairer exclusivement via l'onglet Connexion au pont ; puis vérifier la présence des trois ampoules et les diagnostics.

## v0.3 — Modes, reconnexion et powerup — 2026-10-23
- Choix durable : modes exclusifs Manuel / Temps réel / Accéléré, automates contrôlés par un unique mode serveur ; simulation accélérée pilotant les lampes réelles uniquement après sélection explicite.
- Démarrage matériel : paramètre `powerup.custom` proposé à 10 % par ampoule, écrit sur action utilisateur et contrôlé par relecture API ; test réel du retour secteur restant nécessaire.
- Réactivité : ajout SSE Hue API v2, reprise automatique du flux, sondage de secours toutes les 2 secondes et transitions à la reconnexion de 0,5 à 2 s selon l'écart.
- Après redémarrage : mode Manuel ou Temps réel restauré ; Accéléré réinitialisé sur Manuel ; changement de pont réinitialise le pilotage.
- Diagnostics : état SSE, latence entre détection logicielle et commande après reconnexion, logs sans clé.
- Contrôles : **27 tests Python réussis** en local sur sources v0.1 adaptées à v0.3, incluant HTTP FastAPI et faux pont ; syntaxe JavaScript Node correcte ; patches v0.3 appliqués proprement aux sources GitHub v0.2 sans chevauchement. Tests Windows/Hue physiques et campagne complète des tests v0.2 encore à effectuer.
- Limites : la première luminosité est déterminée par le firmware de l'ampoule ; `powerup` et `dynamics` peuvent être absents ; les événements de reconnexion ne prouvent pas la coupure électrique.
- Prochaine action : synchroniser GitHub, régler powerup 10 % individuellement depuis Diagnostics, tester coupure et transitions puis analyser les logs.
- Hors périmètre : double extinction/allumage rapide à 100 % (v0.4 ultérieure).

## v0.4 — Gestion des mises à jour sur Raspberry Pi — 2026-10-25
- Implémentation préparée sur branche `feature/hue-lab-v0.4-updates` : interface de mise à jour, code PIN privé, service systemd utilisateur indépendant, vérification horaire sans installation automatique.
- Déploiement : sauvegarde config locale, Git fetch + fusion fast-forward, contrôles du nouveau code avant interruption, redémarrage et restauration de l'ancienne version si panne.
- Première migration : script Termux `updater/bootstrap_pi.sh`, archive locale -> clone Git, `.venv` et données Hue conservées.
- Tests locaux : 44 tests Python réussis, incluant dépôts Git simulés, restauration sur échec et authentification ; syntaxe JS et bash vérifiée.
- Non vérifié : installation et fonctionnement sur le Raspberry Pi 2 réel. Ne pas lancer la migration tant que le code n'est pas publié sur `main`.

## v0.5 — Pilotage individuel des lampes — 2026-10-25
- Fonction : commande Manuel/Auto propre à chaque lampe, sans sélecteur global de mode ; la référence horaire « réel/accéléré » est commune seulement aux lampes en Auto.
- Le contrôle manuel mémorise niveau lumineux et état marche/arrêt localement dans `hue_settings.json` et peut les restaurer après redémarrage du serveur. Les reconnections Zigbee ultérieures ne déclenchent pas de rallumage manuel.
- Le passage Manuel vers Auto demande une transition de 2 secondes lorsque `dynamics.duration` est disponible, sinon dépend du firmware. Auto respecte l'état OFF d'une ampoule.
- Migration v0.4.1 : courbes préservées ; mode global ancien « reel » donne Auto par défaut, sinon Manuel. L'horloge accélérée revient à réel au reboot.
- Nouveaux fichiers : `static/v05.css`, `tests/test_v05.py`, `README_V05.md`. La mise à jour autonome v0.4.1 reste inchangée.
- Vérifications locales : 65 tests Python réussis, contrôle de syntaxe Python/JS, scénarios interface téléphone/ordinateur dans Chromium avec lampes simulées. Pas de test physique Raspberry ou Hue effectué.
- Suivant : v0.6, couleur et température selon l'heure ; v0.7, prise en compte du soleil et de la météo.

## v0.5.1 — Ergonomie pure (2026-10-25)
- Aucun changement serveur ni commande Hue, ni modification du contrat JSON des courbes. Les modes et réglages de la v0.5 sont préservés.
- Nouvelle interface d'édition : points horaires sélectionnables au doigt, mouvement sur la courbe, HH:MM en 24 h et pas de 1 minute, luminosité 1–100%, boutons ± 5, ajout/suppression, annulation et sauvegarde explicite.
- Contrôle des doublons, 2–24 points, alerte en cas de navigation avec changements non enregistrés ; aucune requête PUT avant confirmation.
- Simulateur repliable sur mobile, boutons et navigation optimisés pour écrans tactiles, sans modifier le modèle ni le protocole Hue.
- Fichiers : `static/v051.js`, `static/v051.css`, `tests/test_v051_frontend.py`, `README_V051.md` et `templates/index.html`.
- Vérifié : 4 tests unitaires nouveaux, `node --check`, interactions simulées dans Chromium (mobile 320 et 390 px, desktop 1320 px). Aucune lampe réelle testée ; la v0.5 doit être installée/testée sur Raspberry.
