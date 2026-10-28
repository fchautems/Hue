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

## v0.5.2 — Courbe simple continue (2026-10-25)
- Profil par lampe « Simple » / « Personnalisée », indépendamment du Manuel/Auto. Par défaut, les anciens profils personnalisés restent actifs et intacts.
- Courbe simple C2 : nuit stable, montée monotone par smootherstep quintique, plateau haut, descente monotone puis nuit stable, sans rebroussement aux jonctions.
- Réglages : lever (début de montée), fin de montée, début de descente, coucher (fin de descente), luminosités mini/maxi. Validation stricte des horaires et valeurs.
- Calcul temps réel côté serveur `hue_simple_profile.py`, utilisé en mode réel et accéléré sans modifier les autres consignes Hue. Une ampoule éteinte ne sera pas rallumée.
- Stockage local seulement : ajout de `simple_profiles` et `profile_types` dans `hue_settings.json`, maintien des `profiles` personnalisés et `light_modes`.
- UI `static/v052.js` et `static/v052.css` : aperçu indépendant, choix de profil, annulation et activation explicite, contrôles mobiles accessibles.
- Tests nouveaux : math et API (`tests/test_v052_math.py`, `tests/test_v052_simple.py`), contrôle syntaxe JS, interactions Chromium avec ampoules simulées sur 320, 390 et 1320 px ; tests de l'application complète à exécuter avant déploiement sur Raspberry via le moteur autonome.
- V0.6 plus tard : températures de blanc/couleurs ; v0.7 : soleil et météo.

## Hue Lab v0.6 — Roue de couleur et automatisme RGB (2026-10-26)
- Nouvelle section mobile Couleurs RGB avec choix de lampe, Manuel/Auto, roue tactile, saturation, luminosité, six préréglages, aperçu, quatre phases et panneau d'horaires repliable.
- Bouton Couleurs → sur les cartes des ampoules compatibles, mode modifié seulement après validation explicite.
- hue_rgb.py : HSV -> xy CIE D65, limitation au gamut de l'ampoule, interpolation angulaire la plus courte avec smootherstep pour les phases Matin/Journée/Soir/Nuit.
- hue_web.py : trois nouvelles clés locales (rgb_profiles, rgb_manual, rgb_auto_enabled), GET/PUT /api/rgb/{uid}, couleur calculée dans la boucle Auto seulement sur les lampes activées RGB et profil Simple.
- Une lampe éteinte n'est pas rallumée par les couleurs. Le choix manuel s'applique immédiatement uniquement après Enregistrer et si l'ampoule est déjà allumée et joignable. L'état initial après une coupure secteur dépend du powerup de l'ampoule.
- Les anciennes courbes personnalisées, modes individuels et clés Hue restent sauvegardés. Aucune conversion automatique des lampes non configurées en couleurs.
- Couleurs par point personnalisé, soleil et météo : hors v0.6.
- Tests : conversion couleur et courbes, API Hue simulée, Chromium mobile 320/390 px + bureau 1320 px. Matériel réel : non testé.

## v0.6.1 — Navigation fusionnée, horloge préservée (2026-10-26)
- Suppression de l'onglet autonome Couleurs RGB ; réunion de la roue et des profils sous Horloge & lumières.
- Horloge analogique 24 h visible par défaut sur mobile ; seules les commandes de simulation sont repliables.
- Le sélecteur de lampe est commun aux deux éditeurs, avec synchronisation JavaScript et protection des modifications non sauvegardées.
- La roue RGB et la courbe couleur simple sont visibles ; l'éditeur de courbe Simple/Personnalisée reste sous détails avancés.
- Navigation des raccourcis Carte -> Couleurs et Carte -> Courbes corrigée, sans suppression des préférences.
- Fichiers modifiés : templates/index.html, static/app.js, static/v06.js, static/v052.js ; nouveaux : static/v061.css, static/v061.js, README_V061.md, tests/test_v061_navigation.py.
- Pas de modification des fichiers Python de pilotage, des API ou de hue_settings.json ; vérifier les lampes réelles après installation.

## Historique de présence — écran compact (2026-10-28)
- **Décision** : écran séparé « Historique » très simple, en lecture seule, sans nouvelle interaction avec les lampes. Afficher date/heure, nom d'ampoule et nature de l'événement.
- Le journal existant reste local à `logs/presence_events.csv` et demeure exclu de GitHub. La nouvelle méthode `PresenceLog.recent(limit)` lit les dernières observations en ordre antéchronologique avec mémoire bornée ; route `GET /api/presence/events?limit=40`.
- L'onglet Historique s'actualise à l'ouverture, sur clic, et toutes les 15 s lorsqu'il est visible ; présentation compacte pour téléphone, horodatage Europe/Zurich. Aucune donnée utilisateur ne transite par GitHub.
- Les quatre événements possibles sont `light_on`, `light_off`, `zigbee_connected` et `zigbee_disconnected`. Une déconnexion Zigbee ne prouve pas que l'interrupteur mural a été coupé. Aucune donnée initiale fictive n'est créée.
- **Vérifications réalisées** : syntaxe JavaScript compilée par V8 pour les deux scripts ; contrat statique HTML ↔ JS ↔ route API contrôlé après publication. Le numéro de cache du script principal a été augmenté pour forcer le chargement de la navigation modifiée.
- **Non vérifié** : exécution de la suite Python dans un clone complet, rendu visuel en navigateur, installation sur le Raspberry et résultat avec le pont réel. Tests Python ajoutés mais non exécutés à ce stade.
- **Prochaine action** : installer la dernière version depuis Hue Lab, ouvrir « Historique », provoquer un allumage/extinction par télécommande et vérifier la ligne ; pour l'interrupteur secteur, attendre l'observation Zigbee et vérifier séparément.

## Mode Vacances — moteur autonome et priorité au bouton Hue (2026-10-28)
- **Livré au dépôt principal** : `hue_vacation.py` planifie sept jours d'allumages/extinctions sans IA, à partir des sessions logiques ON/OFF fiables des logs (`presence_events.csv`), complétées par des plages matin/soir et des variations déterministes selon jour/lampe. Statistiques révisées quotidiennement, seulement si assez de données.
- **État persistant** : champ `vacation` dans `hue_settings.json` (déjà ignoré par Git) avec `enabled`, ampoules sélectionnées, planning, graine et priorités. État retrouvé après redémarrage ; service Raspberry autonome en heure réelle ; horloge accélérée incompatible tant que mode activé.
- **Priorité de 10 minutes** : changement externe ON d'une ampoule sélectionnée pendant Vacances -> maintien ON pendant 600 secondes ; commande externe OFF -> priorité OFF identique ; délai par ampoule, conservé après reboot, puis reprise immédiate de la consigne calculée. Les propres commandes ON/OFF du simulateur sont filtrées pour éviter une boucle de priorité et de faux exemples dans les logs. Le bouton Hue est pris en compte via le changement d'état **observé**, et non via l'identifiant du bouton ; un appui sans transition n'est pas détectable.
- **Coordination** : le mode Vacances prend la priorité sur les courbes Auto existantes et la restauration manuelle initiale **uniquement pour les lampes sélectionnées**. Les autres lampes continuent de fonctionner normalement. Aucune commande envoyée aux lampes Zigbee déconnectées.
- **Interface** : carte dans Tableau de bord, choix des lampes, Activer/Arrêter, statut, aperçu des événements à venir. API GET/POST `/api/vacation` ; scripts `static/vacation.js` / `static/vacation.css`, documentation `README_VACATION.md`.
- **Vérifié** : exécution locale isolée des algorithmes planification, déterminisme, sessions historiques, calcul d'état, validation de sélection ; compilation JavaScript de `static/vacation.js` et contrôle statique du contrat UI ↔ API / moteur.
- **Non vérifié** : exécution de la suite complète de tests sur le dépôt et comportement avec le pont Hue / télécommande réels. Tests de non-régression ajoutés à `tests/test_vacation.py` mais pas exécutés dans un clone complet.
- **Prochaine action** : exécuter les tests sur un clone de Hue Lab, puis déployer depuis l'onglet Mises à jour. Tester ON du bouton Hue pendant une plage prévue OFF : vérifier maintien 10 min et reprise sans coupure secteur. Avant vendredi 30 octobre, confirmer que les ampoules restent alimentées et que le service Raspberry est actif.

### Contrôles supplémentaires (2026-10-28)
- Workflow CI ajouté : `.github/workflows/tests.yml`, compilation Python et `unittest discover` sur commits Python de `main`. Aucune exécution GitHub Actions confirmée depuis le connecteur (le suivi des runs de push n'est pas accessible). Ce n'est pas une validation positive de la suite.
- `vacation_state` corrigé : n'affiche aucun prochain événement lorsque Vacances est arrêté et compare les timestamps plutôt que les chaînes (changement d'heure).
- Check local isolé du moteur exécuté : construction d'horaires, déterminisme, interprétation de deux sessions historiques, état logique à une heure donnée et validation des IDs réussis. Test complet FastAPI/Hue simulé et essai physique encore à faire.

## Mode Vacances — test accéléré de 60 secondes (2026-10-28)
- **Demande** : permettre de vérifier les véritables allumages/extinctions immédiatement, sans attendre les horaires naturels (parfois plusieurs heures).
- **Livré sur GitHub** : bouton **▶ Tester 60 s** (visible dans Tableau de bord → Mode Vacances, actif uniquement si Vacances est activé), indicateur de progression, heure virtuelle, dernier événement, bouton d'arrêt **■ Arrêter le test**.
- **Exécution** : le worker Hue existant joue sur les lampes sélectionnées une période de 24 h du planning enregistré compressée sur 60 s. Le test commence 72 minutes virtuelles avant le premier événement (premier allumage généralement vers 3 s), force les ampoules sélectionnées initialement OFF puis rejoue les transitions ON/OFF. Plages ON courtes prolongées au moins 2 s pour rester observables. Les lampes non sélectionnées et profils hors Vacances ne changent pas.
- **Reprise et sécurité** : le test est strictement transitoire (non sauvegardé) ; le planning Vacances réel reste intact et redevient prioritaire à la fin, au clic d'arrêt, ou après un redémarrage du service. Aucune commande de test ne doit alimenter les statistiques d'habitudes ni la priorité télécommande de 10 minutes. Le test expire au bout de 60 s même si le pont perd provisoirement sa connexion ; les commandes reprennent quand il revient. La simulation accélérée générale est interdite tant que Vacances reste actif.
- **API / UI** : `POST /api/vacation/test` avec action start/stop, GET `/api/vacation` contient statut, avancement, heure simulée, événements parcourus et dernier événement. Changements dans `hue_web.py`, `static/vacation.js`, `static/vacation.css`, `templates/index.html`, documentation `README_VACATION.md` et tests `tests/test_vacation.py`.
- **Contrôles effectués** : JavaScript compilé avec V8 et intégration statique HTML ↔ JS ↔ API cohérente ; tests automatisés de régression ajoutés (lancement, annulation, expiration, statut, redémarrage, API). Aucune exécution intégrale de la suite Python ni test physique sur Raspberry vérifié depuis cette session. Le résultat des GitHub Actions n'est pas confirmé.
- **Prochaine action** : depuis le Raspberry, vérifier/installer la dernière version, activer Vacances avec quelques lampes alimentées puis cliquer « Tester 60 s » ; observer les vraies transitions, la barre de progression, l'arrêt/retour au planning réel. Faire séparément un essai télécommande de 10 minutes en dehors du test rapide.

## Protection des logs en phases de test (2026-10-28)
- **Décision durable** : ne jamais alimenter `logs/presence_events.csv` avec les effets artificiels du test rapide Vacances ou de l'horloge générale accélérée. Conserver `logs/hue.log` pour diagnostics techniques.
- Dans `hue_web.py`, toutes les quatre écritures d'observations (`light_on/off`, `zigbee_connected/disconnected`) et la détection de priorité manuelle sont filtrées par `_presence_history_suppressed(uid)`. Pendant le test rapide, aucune ampoule ne contribue à l'historique ; 45 s après sa fin, les lampes testées restent exclues pour absorber les réponses tardives du pont. L'expiration automatique, l'arrêt manuel et la désactivation de Vacances prolongent cette protection.
- La simulation horaire accélérée suspend également l'apprentissage de toutes les lampes et applique une marge de 45 s lors du retour à l'heure réelle. Les autres lampes reprennent l'enregistrement dès la fin du test Vacances.
- **Limite assumée** : les actions réellement effectuées pendant le test ou sa marge de sécurité ne sont pas apprises ; pas de nettoyage rétroactif des anciens logs.
- **Contrôles réalisés** : vérification statique des quatre sites d'écriture, de la priorité manuelle, de tous les chemins de fin du test et des exclusions de l'horloge ; tests de régression ajoutés pour ces scénarios dans `tests/test_vacation.py`.
- **Non vérifié** : exécution complète des tests Python et essai avec le pont réel, faute d'environnement Raspberry dans cette session.
- **Prochaine action** : déployer depuis Hue Lab, noter le nombre de lignes dans Historique, lancer `Tester 60 s`, vérifier que ce nombre n'augmente pas durant le test ni pendant les 45 secondes suivant sa fin, puis déclencher une vraie commande après le délai et vérifier la reprise de l'enregistrement.

## Apprentissage suspendu pendant toute la période Vacances (2026-10-28)
- **Décision durable** : `logs/presence_events.csv` n'est **jamais alimenté tant que Vacances est activé**, pour toutes les ampoules, afin que les scénarios que le moteur exécute ne viennent pas réentraîner le moteur. Le programme continue à lire l'historique antérieur en entrée.
- `_presence_history_suppressed(uid)` contrôle les quatre sources d'observation `light_on/off` et `zigbee_connected/disconnected`. L'activation de Vacances active immédiatement le blocage ; sa désactivation déclenche 45 s de quarantaine globale avant la reprise des vraies observations pour absorber les retours tardifs.
- La logique **priorité manuelle Hue pendant 10 minutes** demeure indépendante du blocage des logs (garde séparée `_vacation_test_blocks_override(uid)`). Cette distinction empêche que la nouvelle protection casse l'usage prévu par les voisins.
- Les logs techniques `logs/hue.log` continuent en Vacances, l'historique antérieur reste visible. L'exclusion couvre aussi les lampes non sélectionnées (choix simple et conservateur).
- Tests mis à jour : pauses d'apprentissage en mode Vacances, détection d'une commande manuelle ON sans nouvelle ligne CSV, événement d'autre lampe, persistance après redémarrage, délai de reprise de 45 s, régression des tests rapides.
- **Contrôles** : revue du code et du contrat entre les quatre appels de journalisation et le filtre ; publication des changements GitHub effectuée. **À vérifier** : exécution de la suite Python et essai de télécommande sur Raspberry.
- **Prochaine action** : mettre Hue Lab à jour, observer la stabilité du tableau Historique pendant Vacances, actionner la télécommande pour confirmer les 10 minutes de priorité ; après désactivation et 45 s, vérifier qu'une nouvelle action apparaît dans Historique.
