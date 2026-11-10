# PROJECT_STATE — Philips Hue Web

## v0.15.1 — Tracé de l’appartement et déplacement libre — 2026-11-10
- Retour sur Pixel : le plan v0.15.0 ne reproduit pas la forme des pièces, l’encadré des parties communes est superflu et le déplacement par cases manque de finesse. Trois lampes sont prévues en plus des deux du salon.
- Tracé repris du croquis sans échelle : salon et cuisine ouverts en haut, chambre et bureau avec décroché, couloir en L à droite, salle de bain en bas à droite. Le rectangle extérieur au centre reste vide et inactif.
- Déplacement continu au doigt, limité au contour de la pièce et sans déplacement des voisins. Les positions sont conservées dans le navigateur. Si une ancienne position tombe dans un décroché, le repère reprend une place valide. Les repères trop rapprochés restent séparés pour garder des cibles tactiles distinctes.
- CI 42896089928 : après rechargement, un test Soleil a observé la valeur par défaut dans le formulaire alors que le serveur conservait le réglage. La première lecture est désormais lancée après l’enregistrement des éditeurs différés. Le test ralentit le chargement du script Soleil pour couvrir cet ordre.
- Contrôles réussis sur pont simulé : écran 320 et 393 px, vide central inactif, précision du glissement, persistance après rechargement et cinq ampoules accessibles dans le salon à 320 px. CI PR 42896778161 et CI main 42897021209 vertes.
- Publication : PR #32 fusionnée sur `main` au commit `d845a58`. L’installateur détecte v0.15.1 depuis la v0.15.0 en installation de test.
- Prochaine action : installer depuis Mises à jour et essayer le plan sur le Pixel avec le pont réel.

## v0.15.0 — Plan interactif — PR #31 — 2026-11-10
- Accueil Pièces : plan schématique de six pièces, sans échelle. Le couloir et les escaliers communs au centre sont signalés et ne commandent aucune lampe. Un appui sur la surface d’une pièce commande ses lampes ; un appui sur un repère commande la lampe correspondante.
- Les positions sont réparties sur deux rangées dans chaque pièce. En édition, déplacer un repère au doigt ou au clavier échange les places si nécessaire. L’affectation et les positions sont conservées dans le navigateur par adresse de pont. La liste repliée donne accès aux lampes hors plan ou en surnombre.
- CI 42885664867 sur `b454b47` : Python, Node et Soleil réussis ; le test d’ergonomie attendait la liste repliée sans l’ouvrir. Le scénario vérifie désormais le plan fermé à 320 × 680 et 393 × 680, les commandes tactiles, la zone commune, le déplacement, la persistance et la liste ouverte.
- Contrôles locaux : 222 tests Python, test de parité et six suites Node réussis. La CI 42887581947 a constaté un débordement vertical de 5 px à 393 px ; la hauteur du plan est maintenant plafonnée à 320 px sur mobile.
- Limites : géométrie fixe, affectation initiale par nom de pièce du pont et configuration propre à chaque navigateur. Essai sur Pixel, Raspberry et pont réels à faire.
- CI 42887865013 réussie sur `7196b98` : parcours complet, dont rendu sans défilement à 320 × 680 et 393 × 680, appuis pièce/lampe, parties communes inactives, déplacement tactile et persistance sur pont simulé. Le test attend désormais la fin de la lecture des pièces avant de comparer la position après rechargement.
- Publication : PR #31 fusionnée sur `main` au commit `fdf338e`. CI 42888943326 (PR) et 42889165835 (main) réussies. L’installateur a détecté le passage v0.14.3 → v0.15.0 dans une installation de test, à partir du dépôt GitHub.
- Prochaine action : installer et redémarrer depuis Mises à jour, puis essayer les commandes dans Pièces sur le Pixel avec le pont réel.

Mise à jour : 2026-11-10

## Audit télécommandes Hue — réaffectation et scènes — 2026-11-10
- Trois régressions reproduites sur `e8461bb` : ancienne cible réutilisée jusqu’à 60 secondes sans notification de configuration, appui en file réattribué après une modification, scène explicite ignorée.
- Correction : un instantané des ressources du pont par lot d’appuis, abandon des appuis antérieurs à un changement signalé, et résolution des scènes à partir des lampes effectivement visées. Les cycles à cibles variables, actions marche/arrêt et cibles ambiguës ne créent pas de suspension. Une liste de lampes vide ne retombe pas sur toute la pièce.
- Contrôles sur pont simulé : réaffectation A → B sans redémarrage et sans notification, changement de configuration pendant une lecture, zone et groupe multi-lampes, scène, marche/arrêt, erreur de lecture, molette, reprise d’Auto au rallumage et priorité de Vacances.
- Prochaine action : vérifier la CI puis essayer sur le pont réel avec un bouton réaffecté. La structure de configuration réellement exposée par la molette reste à confirmer.

## Commandes des lampes : état et couleur — 2026-11-10
- Retour Pixel : la même lampe allumée apparaît verte dans Lampes & vacances et brune dans Pièces, et l’état affiché peut attendre la prochaine lecture du pont.
- Décision de Fréd : bouton marche-arrêt pour la pièce, ligne tactile et petit point pour chaque lampe. Gris éteint, ambre dès la demande, vert après confirmation. Le mode Auto reste indépendant.
- Correction : couleurs partagées entre les vues et attente suivie par lampe, y compris quand la même lampe figure dans plusieurs groupes. L’acceptation de la requête ne confirme pas l’allumage.
- Retour Pixel du 2026-11-10 : le Raspberry affiche `47fef0e51011` (v0.14.1) et les deux rangées d’onglets. La v0.14.2 est en validation dans la PR #28.
- La relance de la CI 42803961954 sur `4bb3dac` passe sans changement, y compris Soleil et les commandes de lampe. Chromium local ne démarre pas dans cet environnement.
- Le bouton de groupe reprend le dessin de l’interrupteur de Lampes & vacances, en gardant une cible tactile de 48 px. Le test navigateur vérifie aussi que l’attente reste visible en changeant d’onglet.
- Prochaine action : valider les parcours navigateur sur la PR #28, puis installer sur le Raspberry et essayer sur le pont réel.

## Navigation mobile — 2026-11-10
- Retour sur le Pixel : la v0.14.0 affiche deux rangées dans Pièces et trois dans les autres onglets ; le titre Hue Lab disparaît dans Pièces. Fréd demande deux rangées partout, les six onglets visibles sans défilement et le titre rétabli.
- Correction : grille mobile commune de trois colonnes ; le bandeau Hue Lab reste visible sur l’accueil. Contrôle Chromium réussi sur tous les onglets à 320 et 390 px : deux rangées, six commandes visibles, pas de défilement horizontal, titre présent. L’accueil avec pont simulé tient à 320 × 680 et 393 × 680. CI 42803068107.
- Publication : v0.14.1 fusionnée sur `f195f19` (PR #27). Prochaine action : installer via Mises à jour et vérifier la navigation sur le Pixel.

## Accueil Pièces — 2026-11-10
- Décision : commandes des pièces et des lampes à l’accueil, en une page sans pagination ni défilement sur le téléphone de Fréd. Le futur plan reste un chantier séparé.
- L’accueil récupère les pièces et les zones du pont, affiche leurs lampes et réutilise la commande existante par lampe, y compris lors d’un allumage de groupe. Les lampes non attribuées restent accessibles. L’ancien écran est accessible via Lampes & vacances.
- Contrôles : 216 tests Python, suites Node et CI Chromium 42801863249 réussis. Avec le pont simulé, commandes de groupe et par lampe vérifiées, sans défilement à 320 × 680 et 393 × 680, avec des boutons de 48 px.
- Publication : v0.14.0 fusionnée par [PR #26](https://github.com/fchautems/Hue/pull/26) sur `f0716cc`. Disponible via Mises à jour ; installation sur le Raspberry et test matériel encore à faire.
- Prochaine action : valider le rendu et l’absence de défilement sur le Pixel avec les groupes réels, puis vérifier la commande de groupe et le maintien des profils sur le Raspberry.

## Télécommandes Hue — Manuel temporaire — 2026-11-09
- Demande : la gradation via touches +/− ou molette suspend Auto sur les lampes visées. Une extinction observée libère la suspension et le prochain allumage reprend le profil. Le bouton Auto permet aussi de reprendre immédiatement.
- Association déduite en lecture seule des actions du pont. Les touches de gradation sont reconnues par leur action et les pièces ou zones sont développées en lampes. Une commande sans cible exploitable ne suspend aucun profil. Le mode choisi par lampe et la priorité de Vacances restent indépendants de la suspension temporaire.
- Contrôles sur pont simulé : touches, molette, zone avec sélection de lampes, extinction/rallumage rapide, redémarrage, reprise manuelle d’Auto, scène et Vacances. Forme de l’association de la molette et fonctionnement sur le pont de Fréd à confirmer.
- Publication : v0.13.0 fusionnée par PR #25 au commit `86f853a`, arbre identique au commit testé. CI 42710142461 réussie (216 tests Python, parité, suites Node et Chromium).
- Prochaine action : installer la mise à jour sur le Raspberry, puis vérifier une gradation +/−, une rotation et une extinction/rallumage avec le pont réel.

## Réveil lumineux — intégration v0.12.0 — 2026-11-08
- Fréd confirme la détection du changement du prochain réveil sur son Pixel. Le premier journal de 12 h 45 reste l’historique d’un essai antérieur.
- La carte Réveil lumineux dans Lampes & vacances enregistre une lampe couleur, la teinte, le nombre de minutes d’avance et l’intensité finale. L’APK Hue Lab 0.2 envoie la date et l’heure du prochain réveil. La carte affiche l’heure reçue et la dernière synchronisation, avec un bouton de synchronisation immédiate dans l’APK.
- Le Raspberry conserve l’alarme reçue et exécute l’aube en heure réelle, même hors ligne côté téléphone. Maintien du niveau final cinq minutes. L’arrêt manuel et Vacances gardent la priorité. Android relit l’alarme à l’ouverture, sur changement reçu et via une tâche de secours reportable.
- Contrôles : 212 tests Python, parité Python/JS, six suites Node, Chromium avec scénario Réveil lumineux à 320 px et APK Android 0.2 compilée et signée. CI 42522883650 et 42522883692 réussies.
- Publication : PR #24 fusionnée sur main au commit `687b505`, arbre identique au commit testé. APK 0.2 livrée, signature de prototype distincte de l’APK 0.1.
- Prochaine action : installer les deux mises à jour puis essayer une alarme proche sur une lampe couleur après confirmation de l’heure et passage en mode avion. Chaîne Pixel → Raspberry → Hue à vérifier sur le matériel.

## Saturation au coucher du soleil — 2026-11-08
- Cause vérifiée sur `4db19445` : la couleur du soir partageait la progression retardée de la luminosité. À 19 h 20, l’aperçu du 8 novembre affichait 2 % de saturation et 98 % de luminosité, pour un coucher solaire à 17 h 10.
- Décision et changement : la saturation prend de l’avance du coucher solaire jusqu’au coucher personnel. La luminosité garde sa courbe et les niveaux de confort et de nuit restent ceux des réglages existants. L’aperçu et le pilotage Auto utilisent le même calcul.
- Contrôles locaux : 207 tests Python, parité Python/JS et six suites Node réussis. Le scénario passe à 10 % de saturation à 18 h 10 et à 34 % à 19 h 20, avec 98 % de luminosité à 19 h 20.
- Publication : v0.11.1 fusionnée par PR #23 au commit `19ca9b4`, arbre identique à celui testé. CI 42511730834 réussie, parcours Chromium compris.
- Prochaine action : installer via Mises à jour et essayer le profil Soleil sur une ampoule RGB. Essai matériel à faire.

## Historique du premier essai Pixel — 2026-11-08
- Retour utilisateur : APK autonome de test installée, lecture du prochain réveil correcte ; journal partagé et analysé.
- Faits du journal : événement `diffusion statique (manifest) | CHANGEMENT` à 12:45:17, avec nouvelle heure de réveil le lendemain ; tâche `JobScheduler` à 12:58:58, 13:13:22 et 13:31:45, heure stable. D'autres diffusions statiques ont été consignées plus tôt.
- Correction apportée par l'utilisateur (2026-11-08) : il a vraisemblablement **rouvert l'APK autour de 12:45**, après l'avoir fermée auparavant. Le journal contient effectivement une `ouverture de l'application` à 12:44:44, puis une notification statique à 12:45:17. **Aucune preuve de réception de l'événement après swipe tant que l'app reste fermée** : retirer la précédente conclusion affirmative. La lecture des alarmes et les exécutions JobScheduler sont observées. Tester une modification d'alarme après swipe, sans rouvrir l'APK pendant un délai connu, et comparer horodatages du journal après réouverture.
- Les vérifications périodiques ont eu des intervalles variables, notamment de 10:40:29 à 12:44:44 (~2 h 04 min) ; pas de garantie de passage toutes les quinze minutes. La détection sur événement est prometteuse mais pas encore démontrée en arrière-plan.
- Code et suivi : APK de diagnostic isolée sur PR #21, sans envoi au Raspberry ni contrôle Hue. Hypothèse Wi-Fi coupé en mode avion conservée.
- Suite envisagée à l’issue de cet essai : isoler les conditions de détection après balayage et écran verrouillé. Voir l’état actuel du Réveil lumineux ci-dessus.

## Décision / test Android « prochain réveil » — 2026-11-08
- Décision utilisateur : **supposer le Wi-Fi coupé la nuit en mode avion** ; le Raspberry doit connaître le prochain réveil avant la coupure. Ne pas dépendre d'une synchronisation nocturne.
- But : lecture du prochain réveil Android par `AlarmManager.getNextAlarmClock()`, avec date et heure, et transmission vers Raspberry uniquement lors d'un changement confirmé, selon disponibilité réseau.
- Point de vigilance vérifié dans la documentation Android : `ACTION_NEXT_ALARM_CLOCK_CHANGED` est envoyé aux receivers enregistrés ; une inscription dépendant d'un processus vivant ne garantit **pas** d'événement quand l'APK a été balayée/fermée. Ne pas présenter cette détection comme acquise. Un fallback périodique tolérant les reports Android est à évaluer, sans promesse de notification immédiate.
- Vérifié dans le dépôt : `android/` contient l'APK prototype WebView 0.1 (target SDK 35), sans lecture de réveil ni synchronisation native.
- Test demandé sur Pixel : (1) obtenir et afficher date/heure exactes du prochain réveil Google Horloge, (2) modifier l'alarme app ouverte, puis app balayée, puis téléphone verrouillé ; observer événement et latence réelle, (3) vérifier le dernier envoi sur le Raspberry avant passage en mode avion avec Wi-Fi désactivé, (4) tester redémarrage/force stop et impact batterie.
- Contrôles réalisés : revue de documentation officielle Android et inspection de l'état GitHub. **Aucune APK de test construite, aucun test physique réalisé.** Ne pas implémenter une synchronisation de production avant validation du comportement sur appareil.
- Blocage : test réel nécessite installer une APK instrumentée sur le Pixel et disposer du Raspberry en réseau local.
- Prochaine action : créer une APK de test dédiée à l'observation du réveil et des notifications, sans modifier l'automatisation Hue de production.

## État actuel — v0.11.0 et prototype Android publiés — 2026-11-07
- Base publiée v0.10.1 vérifiée au commit 27e2b6e. Reprise des demandes vocales, fiche Brain et guide modèle lus.
- Simulation : Pause/Reprendre près du curseur et saisie d’une heure exacte. Le déplacement fixe cette heure et met la lecture en pause. Les vitesses restent dans les commandes repliables. Les lampes Auto suivent toujours la référence choisie.
- Navigation : Mises à jour et Paramètres ont des pages distinctes. Pont Hue et diagnostics restent dans Paramètres. Champs des trois rangées Soleil alignés sous les libellés longs.
- Android : prototype WebView du serveur local, adresse initiale 10.0.0.12:8765 et IPv4 privée/port modifiables. Écran de récupération réseau. Compilation et signature de test par CI. Source dans android/.
- Validation : 206 tests Python, parité Python/JS, six suites Node et deux parcours Chromium réussis. CI PR 42354228352 et main 42354367556 vertes. APK 0.1 compilé en CI 42354228366 avec signatures v2/v3 vérifiées. Onze cas de validation d’adresse testés localement.
- Publication : PR #20 fusionnée au commit 7f96d2e8153978818baa5a50f1b9a9b9e7501ed5. Arbre de code identique au code testé. APK 0.1 livré séparément, signature de prototype. Brain mis à jour.
- Prochaine action : mise à jour web depuis le Raspberry et installation de l’APK sur le téléphone pour valider la connexion réelle. Automatisation en pause.

## État actuel — v0.10.1 publiée — 2026-11-07
- Signalement sur Raspberry : mise à jour de 98233468 vers e1c5b09b interrompue pendant les tests avant installation. La révision installée reste 98233468.
- Cause reproduite localement : le test de parité Python/JavaScript, découvert par l’installateur v0.9.0, appelle Node.js et échoue avec FileNotFoundError si Node.js est absent. Les captures ne fournissent pas le détail du journal système du Raspberry.
- Correctif : sortir ce test de la découverte Python standard et l’exécuter explicitement en CI. Le Raspberry peut utiliser l’installateur déjà présent et exécuter tous les tests Python de déploiement.
- Vérification locale : installateur exact de 98233468 sur un dépôt de test, PATH sans Node.js et service simulé. La v0.10.0 est refusée avant tout arrêt. La v0.10.1 s’installe directement, redémarre le service simulé et préserve les fichiers de réglages et du pont à l’identique. Test de parité avec Node.js réussi.
- Publication : PR #19 fusionnée au commit 4bb12ff4a1f78e0baec143c2388b8fe8005cf22c, arbre identique au code testé. CI PR 42348078473 et main 42348150164 réussies (206 tests Python, parité, JavaScript et Chromium). Brain mis à jour.
- Prochaine action : sur le Raspberry, vérifier GitHub puis installer et redémarrer depuis Mises à jour. Essai sur le matériel à faire. Automatisation en pause.

## État actuel — v0.10.0 publiée — 2026-11-06
- PR #18 fusionnée sur main au commit 0b63a4c686bc4801f73c23adc1a747ccbca99937 ; arbre identique au commit validé 6da61b1 (2024fa3f). Aucun déploiement matériel.
- Livré : confort et saturation réglables au réveil/coucher, durée commune de transition avant/après, luminosité nocturne réglable et saturation de nuit 100 %. Courbes en S asymétriques, transitions cycliques traversant minuit sans chevauchement.
- Couleurs : trois teintes pleines matin/soir/nuit, blanc de journée indépendant CIE D (5000 K proposé, 4000–6500 K réglable), commandes xy limitées au gamut ; rendu écran indicatif, spectre solaire non reproduit.
- Interface : un formulaire/enregistrement par lampe, double courbe luminosité/saturation, aperçus datés en lecture seule. Les anciens profils conservent leur comportement jusqu’à adoption explicite ; types Simple/Personnalisé et Manuel/OFF/Vacances préservés. Copies fixes de luminosité sans changement des couleurs ; édition des copies selon les contrôles Simple visibles.
- Contrôles : 207 tests Python, six suites Node, deux parcours Chromium 320/390/1320 px réussis ; CI PR 42303072513 completed/success, captures relues. Le scénario de rechargement attend désormais les lampes initiales. CI main 42303253108 completed/success.
- Limites : pont simulé uniquement, pas de test physique Raspberry/Hue, pas de météo ; réveil et coucher personnels dans la même journée.
- Prochaine action : installer via Mises à jour puis ouvrir Soleil et adopter/enregistrer les nouveaux réglages une fois par lampe ; vérifier les niveaux réels, les couleurs et les priorités. Automatisation laissée en pause.

## Rythme solaire v0.10.0 en cours — 2026-11-06
- Demande : confort au réveil/coucher, transition commune avant/après ces heures, minimum nocturne avec saturation 100 %, paliers réglables ; courbes en S asymétriques, teintes matin/soir/nuit et blanc de journée ajustable.
- Base vérifiée : main 9823346 propre, v0.9.0 publiée. Brain et MODEL_GUIDE lus ; aucune reprise d’automatisation ni accès matériel.
- Implémentation : options nouvelles séparées du schéma solaire historique ; les profils existants gardent leur comportement jusqu’au nouvel enregistrement. Moteur cyclique pour les transitions passant minuit, interpolation du blanc CIE D (5000 K proposé, 4000–6500 K réglable) vers les teintes saturées.
- Contrôles locaux : 207 tests Python et six suites Node réussis ; syntaxe/compilation et diff valides. Tests des paliers exacts, continuité, monotonie, passage minuit, CIE D50/gamut, parité Python/JS chaque minute, commandes simulées/persistance, copies et compatibilité. Chromium local interdit de créer son socket ; validation des parcours par CI requise. Aucune publication de cette version à ce stade.
- Publication : PR #18 ouverte, moteur Python/Node vert en CI. Premier parcours navigateur arrivé à la validation des durées ; attente erronée du test corrigée (180 min tenaient bien dans une nuit de 405 min). Parcours général adapté aux nouvelles bornes de réveil.
- Relecture : parcours solaire et général réussis dans CI 42302537233, captures 390/1320 relues. Finition : piste des teintes colorée et édition explicite des copies solaires fixes convertie vers les contrôles Simple visibles ; protection des brouillons étendue à cette conversion. Nouveau contrôle navigateur ajouté pour ce cas.
- Prochaine action : terminer CI/parcours et captures 320/390/1320 px, corriger si nécessaire puis fusionner si vert. Aucun déploiement matériel, automatisation toujours en pause.

## État actuel — v0.9.0 publiée — 2026-11-06
- PR #17 fusionnée sur main au commit ba02d8f86c8a2b135e81276f2b49cd45d2ba1b2c, après validation complète du commit ea9874d.
- Livré : choix permanent Simple/Personnalisé/Soleil par lampe ; réveil/coucher, niveaux et lieu enregistrés une fois. Horaires et couleurs évalués selon chaque date locale, cache journalier en mémoire, reprise après redémarrage. L’aperçu daté ne modifie jamais le suivi.
- Interface intégrée : formulaire et enregistrement unique, aperçu automatique, annulation/protection des brouillons, statut Manuel/Auto synchronisé ; trois libellés lisibles à 320 px. Couleurs éditables sans désactiver Soleil ni dupliquer les horaires.
- Compatibilité : anciens profils fixes conservés sans conversion implicite, Manuel/OFF/Vacances prioritaires, personnalisation des couleurs préservée. Copie complète = options quotidiennes ; copie de luminosité seule = courbe fixe du jour.
- Contrôles : 198 tests Python, six suites Node et deux parcours navigateur 320/390/1320 px réussis ; CI PR 42283707888 completed/success. Captures relues, arbre fusionné identique au code validé. CI main 42283937344 completed/success.
- Limites : aucun essai physique Raspberry/Hue ni déploiement matériel. Sans météo ni relief, journée sans passage de minuit, repli sur le rythme personnel si soleil absent ; simulation accélérée sur les horaires d’aujourd’hui.
- Prochaine action : installer via Mises à jour sur le Raspberry puis choisir Soleil, enregistrer et utiliser Auto sur les lampes concernées. Tâche de développement automatique toujours en pause.

## État actuel — v0.8.1 publiée — 2026-11-06
- PR #16 fusionnée sur main au commit 20204fb11822b3ad38b94f2c4ac40725400e95ee. Autorisation explicite confirmée par Fréd dans cette reprise.
- Livré : cible issue du seul profil actif du serveur, luminosité lue et état Manuel/Auto/Vacances séparés ; parcours solaire clarifié, retour à la lampe nommée ; passage Simple/Personnalisée réversible sans perdre les vrais brouillons.
- Nouveaux profils solaires : horaires sans plafonds de deux/trois heures ; exemple vérifié 05:15–07:23 et 17:13–22:30. Montée rapide puis lissée, baisse plus tardive, couleurs calées sur ces horaires. Les profils existants restent conservés ; repréparer puis appliquer pour adopter le correctif.
- Contrôles : 192 tests Python, six suites Node et deux parcours navigateur 320/390/1320 px réussis ; CI PR 42264568465 et CI main 42264894227 completed/success, captures relues. Arbre fusionné identique au code validé.
- Limites : aucun déploiement ni test physique Raspberry/Hue. Profil fixe pour la date choisie, sans recalcul quotidien ni météo. Tâche automatique toujours en pause.
- Prochaine action : installer via Mises à jour sur le Raspberry, repréparer/appliquer le profil solaire et vérifier les lampes réelles.

## Reprise v0.8.1 — 2026-11-06
- Envoi Git sans identifiants indisponible ; correctif envoyé via le connecteur GitHub au commit b634770. CI 42264150851 : défaut réel identifié dans le sélecteur Simple/Personnalisée : consulter l’autre type rendait le retour au type actif impossible, le bouton Annuler étant masqué. Correction : autoriser les changements de vue sans édition, conserver la protection des champs modifiés. Régression navigateur renforcée pour les deux cas.
- Périmètre confirmé avec la conversation précédente : cible stable, ergonomie Profils & simulation, suppression des plafonds de deux/trois heures ; montée avancée, baisse retardée, teintes calées sur les horaires solaires.
- PR #16 reprise au commit 9828793. CI 42262017834 : Python, Node et navigateur solaire réussis ; parcours ergonomique bloqué par un clic du test sur Annuler, masqué après passage à la vue personnalisée.
- Correction du scénario : retour par le bouton Simple et vérification de l’absence de brouillon, sans supprimer le contrôle anti-alternance de la cible.
- Contrôles de reprise : 192 tests Python et six suites Node réussis localement. Chromium local échoue sur la création du socket système ; validation navigateur par CI requise.
- Blocage : l’envoi du commit local 21779c8 vers fchautems/Hue, branche fix/solar-target-v081 (PR #16), a été refusé par la revue automatique pour autorisation destination/contenu insuffisamment explicite. Aucune nouvelle tentative ni fusion.
- Accord ciblé reçu le 2026-11-06 : Fréd confirme « Oui toujours » à l’envoi des corrections v0.8.1 dans fchautems/Hue, PR #16, puis fusion si tous les contrôles passent. Blocage d’autorisation résolu.
- Prochaine action : envoyer ces corrections, vérifier la CI et les captures, puis fusionner si succès. Aucun accès matériel ni reprise de la tâche automatique.

## Correctifs v0.8.1 en cours — 2026-11-06
- Demande confirmée : corriger la cible instable, supprimer les limites solaires de 2/3 heures, montée plus rapide le matin et baisse plus tardive le soir ; clarifier cet écran.
- État vérifié : base main 6949331, aucun MODEL_GUIDE.md/AGENTS.md dans le dépôt. Brain non exposé. Deux écrivains concurrents du champ cible identifiés (timer app.js enregistré avant surcharge v052.js).
- Changements : cible du serveur uniquement, luminosité lue et priorité Manuel/Auto/Vacances visibles ; soleil avant couleurs, étapes et aperçu sans commande explicites, application nommée et compte rendu par lampe. Horaires solaires directs, sauf ordre et transition minimum de 30 minutes si le soleil est hors plage personnelle, avec explication.
- Nouveaux profils solaires : paramètre optionnel transition_shape=asymmetric ; préservation de la forme des profils existants et des teintes RGB. Le profil reste fixe pour la date choisie, sans recalcul quotidien ni météo. Repréparer/appliquer pour bénéficier des nouveaux horaires.
- Contrôles locaux : 192 tests Python et six suites Node réussis, compilation/syntaxe et diff --check valides. Test ajouté : consigne affichée égale commande de luminosité sur pont simulé, couleur du même profil, conservation après redémarrage. Scénario navigateur anti-alternance et application solaire ajouté.
- Blocage local : Chromium interdit de créer son socket système ; parcours navigateur à exécuter dans la CI avant fusion. Aucun accès au Raspberry ni aux lampes physiques. Aucun déploiement, aucune reprise de l’automatisation.
- Prochaine action : publier sur branche, vérifier CI/captures puis fusionner si tout passe.

## État actuel — v0.8.0
- Refonte ergonomique fusionnée sur `main` via PR #15 au commit `dad1066915666a1e32d935030ec102c655919ad9` le 2026-11-06.
- Navigation : Lampes & vacances, Profils & simulation, Historique ; Pont/Avancé/Maintenance dans Paramètres. Accès permanent aux mises à jour et badge. Courbe/horloge rapprochées, couleurs/soleil/copies repliables.
- IP saisie et configuration locale conservées ; aucun modèle d'IP imposé, choix explicite d'un pont détecté et secours SSDP local. Aucun changement des schémas de données ni des moteurs Hue.
- Validation avant fusion : 187 tests Python, six suites Node, deux parcours navigateur 320/390/1320 réussis ; CI PR `42250031236` verte, captures relues.
- [CI main 42250382795](https://github.com/fchautems/Hue/actions/runs/42250382795) terminée completed/success : Python, Node et les deux parcours navigateur réussis. Aucun déploiement ni essai physique Raspberry/Hue. La découverte multicast reste à valider sur le réseau utilisateur.
- Prochaine action : installer depuis Mises à jour sur Raspberry et vérifier le fonctionnement matériel. Automatisation laissée en pause.

Les sections suivantes conservent l'historique des versions.

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

## Mode Vacances — frise compacte par lampe (2026-10-29)
- **Demande** : visualiser facilement les périodes allumées/éteintes de chaque lampe pendant Vacances, sans alourdir l'interface ni toucher aux automatismes.
- **Réalisé** : remplacement de la longue liste « Prochains événements » par une frise 24 h compacte par lampe, segments dorés pour ON, horaires exacts, deux flèches pour naviguer d'aujourd'hui aux six jours suivants. Visible dans Tableau de bord → Mode Vacances, après activation ; lecture seule.
- **Données** : `GET /api/vacation/schedule` expose le planning enregistré dans `HueServer.vacation["schedule"]` pour les lampes sélectionnées. Le navigateur le récupère une fois par génération et navigue localement ; le plan se recharge automatiquement si la date de génération change. `GET /api/vacation` fournit `plan_date` pour détecter ce changement.
- **Périmètre** : pas de nouvelle tâche en arrière-plan, pas de stockage supplémentaire ni de dépendance JS, pas de modification du moteur Vacances ou de la priorité Hue des voisins. La frise montre les horaires prévus, pas les dérogations temporaires de 10 min.
- **Vérification effectuée** : compilation syntaxique JavaScript dans V8 ; contrat des identifiants DOM, assets versionnés, route GET, absence d'appels de contrôle Hue, navigation bornée à sept jours ; test de route Python ajouté dans `tests/test_vacation.py`.
- **Non vérifié** : exécution des tests Python du dépôt entier et affichage sur Raspberry ; tentative de clone direct du dépôt dans le conteneur échouée (résolution DNS GitHub indisponible). Aucun test de matériel Hue revendiqué.
- **Prochaine action** : installer la mise à jour dans Hue Lab, activer Vacances et vérifier visuellement les plages par lampe ainsi que les flèches jour précédent/suivant sur téléphone.

## v0.6.2 — Copie de courbe entre lampes (2026-11-04)
- **Fonction ajoutée** : dans « Horloge & lumières », copie explicite de la courbe de luminosité active d'une lampe source vers la lampe sélectionnée, avec confirmation. Compatible avec les courbes Simple et Personnalisée via les API existantes. Aucune copie des couleurs RGB, du mode Manuel/Auto, de l'état ON/OFF ou des règles Vacances.
- **Garde-fous** : aucune action si la source et la destination sont identiques ; copie refusée en présence d'un brouillon non enregistré ; confirmation avant remplacement de la courbe active ; contrôle du changement de destination pendant la lecture de la source ; aucun appel direct au pont depuis l'interface de copie.
- **Fichiers** : `static/v062.js`, `static/v062.css`, `tests/test_v062_ui.cjs` et `templates/index.html`. Aucune modification des API Python ou des réglages locaux persistants hors action explicite de copie.
- **Contrôles** : `node --check` sur le nouveau JavaScript ; cinq scénarios Node avec navigateur simulé (Simple, Personnalisée, brouillon, annulation, changement de lampe) réussis localement ; endpoints GET/PUT existants et ordre des scripts vérifiés par revue. La suite Python complète, les essais visuels en navigateur, le Raspberry et les ampoules physiques ne sont pas testés ici.
- **Prochaine action** : mettre à jour Hue Lab depuis l'onglet Mises à jour, ouvrir « Horloge & lumières », sélectionner la destination puis « Reprendre la courbe de » pour choisir la source. Tester sur deux lampes et vérifier que le mode Manuel/Auto et les couleurs restent inchangés. Itération suivante : profil intelligent simple par défaut, sans casser l'éditeur avancé.
- **Cadence retenue** : itérations automatisées toutes les 4 heures dès 16:00 Europe/Zurich ; petits correctifs uniquement entre 22:00 et 08:00. Publication seulement après vérification du changement ciblé.


## Préparation copie de profil — 2026-11-04, 16 h (Europe/Zurich)
- **État vérifié :** l'API actuelle conserve les courbes personnalisées, simples et RGB par lampe. La nouvelle ampoule démarre normalement en Manuel. Aucun transfert de profil entre lampes n'était proposé.
- **Changement préparé :** branche `feature/hue-profile-copy-20261104`, méthode `copy_profile` et route `POST /api/profile/copy/{target_uid}` avec `source_uid`. Copie des deux courbes et des couleurs automatiques compatibles ; préserve mode Manuel/Auto, état ON/OFF et luminosité manuelle de la cible. Pas de commande Hue lors de la copie. Ajout de deux tests de non-régression.
- **Contrôles :** revue des contrats API et des tests existants ; **suite Python non exécutée**, car le clone du dépôt via réseau est indisponible dans l'environnement de test. Pas de test sur Raspberry ou lampes réelles.
- **Blocage :** exécuter la suite complète avant fusion ; aucune release principale annoncée. L'interface utilisateur de copie reste à ajouter après validation.
- **Prochaine action :** exécuter la CI de branche et vérifier le résultat, ajouter un bouton de copie simple puis tester sans écraser les réglages de la destination.


## Revue de l'incrément copie — 2026-11-04, 19:55 (Europe/Zurich)
- **État vérifié :** `main` contient déjà la v0.6.2, avec un sélecteur « Reprendre la courbe de » et une copie explicite de luminosité Simple/Personnalisée par les routes existantes. La PR #1 est distincte : elle ajoute une API de copie de profil complet (y compris couleurs automatiques compatibles), sans interface utilisateur pour cette API. Ne pas présenter cette PR comme une nouvelle interface ni dupliquer la v0.6.2.
- **Changement effectué :** sur la branche isolée `feature/hue-profile-copy-20261104`, le workflow `.github/workflows/tests.yml` déclenche désormais les tests Python aussi sur les pull requests vers `main`, avec filtres de fichiers inchangés. Aucun changement au pilotage des lampes ou aux réglages du Raspberry.
- **Contrôles :** revue de la PR #1, de `tests/test_v052_simple.py`, de la configuration CI et de l'état de `main`. Tentatives de clone et d'exécution Python dans le conteneur interrompues par une erreur d'environnement ; aucune suite exécutée localement. Après le commit du workflow, aucun run de branche n'était encore visible lors de la consultation ; statut CI non validé.
- **Blocages :** vérifier que GitHub Actions lance la PR et que les tests réussissent ; revoir la sémantique de copie des couleurs et l'effet différé possible sur une lampe déjà en Auto. Ne pas fusionner sans ces vérifications.
- **Prochaine action :** examiner les résultats CI, corriger les défauts éventuels, puis décider si l'API de copie complète apporte une valeur réelle au-delà de la copie de courbe déjà livrée. Pas de release utilisateur sur cette itération.

## v0.6.3 — Copie du profil complet — 2026-11-04 (Europe/Zurich)
- **État vérifié :** v0.6.2 déjà sur main ; PR #1 ajoutant l'API de copie de profils et tests Python, CI initiale de branche terminée avec succès (run 41892035968). 
- **Changements :** bouton séparé « Copier le profil complet » dans Horloge & lumières, confirmation explicite avant copie des courbes et couleurs automatiques compatibles ; l'ancien bouton « Copier vers cette lampe » reste limité à la luminosité. API `POST /api/profile/copy/{target_uid}` issue de la PR #1 ; conservation du mode Manuel/Auto, de l'état ON/OFF et des règles Vacances. Version affichée mise à jour.
- **Contrôles :** ajout du test Node de sept scénarios, exécution des tests Node et Python ajoutée à GitHub Actions. Tests CI pour l'incrément complet à confirmer avant fusion dans main ; pas de test matériel réel.
- **Limites :** si une lampe cible est déjà en Auto, le profil peut modifier la lumière au prochain cycle après confirmation ; aucune donnée privée publiée. Aucun changement déployé directement sur Raspberry.
- **Prochaine action :** confirmer la CI de la PR, fusionner uniquement si succès, mettre à jour Hue Lab sur Raspberry et vérifier la copie de couleurs RGB et courbes en mode Manuel d'abord.

### Validation et publication v0.6.3 — 2026-11-04 (Europe/Zurich)
- **État vérifié :** PR #1 fusionnée sur `main` avec succès, commit `aa7d10cf39f6def6fc7cffe309eb34748c5ed7e6`. Le fichier `static/v063.js` est présent sur `main`.
- **Tests :** GitHub Actions run `41901196573` terminé avec succès sur la PR : compilation Python, suite complète de tests unitaires Python, syntaxe JavaScript, scénarios de copie v0.6.2 et v0.6.3. Ce résultat ne vaut pas test physique des lampes ou du Raspberry.
- **Contrôles / sécurité :** modes Manuel/Auto et état ON/OFF de destination préservés ; confirmation utilisateur avant copie, avertissement explicite de possible changement de lumière si cible en Auto. Pas de déploiement Raspberry effectué.
- **Blocage :** vérifier sur le Raspberry l'installation et la compatibilité réelle de la copie de couleur selon les ampoules, notamment ampoules non RGB.
- **Prochaine action :** installer v0.6.3 via Mises à jour ; sélectionner une destination en Manuel, copier un profil complet d'une source RGB, vérifier courbes/couleurs et conservation du mode ; essai en Auto seulement ensuite.

## v0.6.4 — Historique navigable (4 novembre 2026, 21 h Europe/Zurich)
- **État initial vérifié :** v0.6.3 publiée et testée par CI ; historique limité aux 40 dernières observations.
- **Changements :** pagination en lecture seule via `offset` optionnel de `GET /api/presence/events`, sans rupture pour les clients existants ; tampon mémoire borné à 10 100 lignes ; pages de 40, boutons « Plus anciens » et « Plus récents », rafraîchissement automatique seulement sur la première page, bouton Actualiser revenant aux plus récentes.
- **Contrôles préparés :** tests Python (pagination, égalité d'horodatage, contrat HTTP et absence de commande Hue), tests Node de navigation, syntaxe JavaScript ; CI déclenchée aussi par JS/HTML/tests.
- **Blocages :** résultat CI de cette modification à confirmer avant fusion ; aucune vérification sur Raspberry ni sur lampes physiques à ce stade.
- **Prochaine action :** valider GitHub Actions puis publier si tous les tests réussissent ; sur Raspberry, vérifier navigation et actualisation sans impact sur les lampes.

### Publication et validation v0.6.4 — 2026-11-04, Europe/Zurich
- **État vérifié :** PR #2 fusionnée sur `main` ; commit de version `edeb5ef970d59ae3588c898046e2a7b406ed2cc3`. Nouvelle interface présente dans `templates/index.html`, paramètre `offset` conservant la compatibilité de l'API.
- **Tests :** CI de PR [41903020474](https://github.com/fchautems/Hue/actions/runs/41903020474) réussie ; CI de `main` [41903124649](https://github.com/fchautems/Hue/actions/runs/41903124649) réussie : compilation Python, suite complète Python, vérification JavaScript et tests Node dont navigation de l'historique. Aucun essai physique.
- **Blocages :** affichage réel mobile et installation Raspberry non vérifiés ; profondeur d'historique visible limitée à 10 040 observations les plus récentes, sans suppression du CSV.
- **Prochaine action :** mettre à jour le Raspberry, vérifier le retour aux événements récents, puis poursuivre un profil intelligent ou l'historique du mode Vacances à la prochaine version.

## Décision de feuille de route — 2026-11-04 : soleil, météo, ergonomie
- **Décision confirmée :** les profils intelligents doivent prendre en compte le **lever et le coucher réels du soleil** suivant la date, la saison et le lieu, **distincts des horaires personnels** de réveil/coucher. La météo (nébulosité / conditions extérieures) est une option d'affinage, non un prérequis ; le service doit fonctionner sans Internet avec comportement de repli explicite.
- **Expérience utilisateur :** privilégier une interface très ergonomique avec peu de clics, gros contrôles tactiles et réglages simples en premier, prévisualisation lisible et configuration avancée toujours accessible mais secondaire. Les changements de luminosité et de couleur doivent être progressifs et faciles à comprendre.
- **État vérifié :** cette note exprime une priorité produit, **pas une fonctionnalité déjà implémentée**. V0.6.4 reste la dernière version fonctionnelle vérifiée à ce stade.
- **Changements :** feuille de route et consigne de développement automatique mises en cohérence ; aucune commande Hue, aucun fichier de configuration utilisateur et aucune fonctionnalité runtime modifiés.
- **Contrôles :** lecture du dépôt et des consignes automatiques ; aucun test logiciel requis pour cette note de planification.
- **Blocages :** choix exact de l'algorithme solaire et du fournisseur météo à définir lors du développement, avec prise en charge hors ligne.
- **Prochaine action :** traiter un petit incrément solaire testable séparément (calcul des événements selon date/lieu, tests de fuseaux et changement d'heure), puis prévoir l'adaptation des courbes et l'interface utilisateur.

## Correctif nocturne v0.6.5 — 2026-11-05, 00:00 Europe/Zurich
- **État vérifié :** `main` au commit `59fb4607f9c6e8b52ffebe702aa252af015deee4` ; dernière version affichée v0.6.4, dernière CI main réussie 41903124649 ; aucune GitHub Release publiée. La copie de courbe v0.6.2 vérifiait la destination après lecture asynchrone, mais pas la source.
- **Changement isolé :** `static/v062.js` refuse maintenant d'écrire la courbe si la lampe source change pendant le chargement ; `tests/test_v062_ui.cjs` ajoute un scénario de non-écriture après changement de source. Aucun réglage, moteur Hue ou mode de lampe modifié.
- **Contrôles :** test de régression ajouté ; résultat CI de PR à vérifier avant toute fusion ; pas de test matériel. **AUCUNE VERSION PUBLIÉE** tant que CI non confirmée.
- **Prochaine itération (04:00 Europe/Zurich) :** confirmer la CI et fusionner ce correctif si tous les tests réussissent ; sinon corriger le test. Puis cibler une amélioration ergonomique purement visuelle du sélecteur de profils, en commençant par `static/v062.css`, avec test de taille tactile mobile >=44 px ; sans changement de commandes Hue ni de configuration locale. La priorité solaire reste prévue pour une session de jour : calcul local lever/coucher distinct du réveil/coucher personnel, tests de date et DST.

## v0.6.5 — Fusion et validation (2026-11-05, 04:00 Europe/Zurich)
- **État vérifié :** PR #3, CI GitHub Actions 41930200673 réussie (suite Python et Node) ; fusion squash sur main au commit `5addabfd44c561bff9f1f1cfea4c9a2ae3436b8f`. Aucun GitHub Release autonome ; version v0.6.5 désigne le correctif sur main.
- **Limites :** tests réels Raspberry/Hue non effectués ; aucune configuration locale ni commande matérielle modifiée.

## Incrément nocturne v0.6.6 — 2026-11-05, 04:00 Europe/Zurich
- **État vérifié :** v0.6.5 sur main, sélecteur de copie de courbe de v0.6.2 encore compact et sans style explicite de focus ; pas de release GitHub dédiée.
- **Changements :** `static/v062.css` agrandit les contrôles de copie à 48 px, améliore la lisibilité du libellé et affiche le focus clavier ; `tests/test_v062_accessibility.cjs` vérifie les cibles tactiles >=44 px et le focus ; workflow CI modifié pour exécuter ce test et réagir aux CSS.
- **Contrôles :** CI de la nouvelle PR à confirmer avant fusion ; aucun essai sur téléphone réel, Raspberry ou ampoules.
- **Blocage :** publication v0.6.6 conditionnée au succès GitHub Actions ; ne pas fusionner sur échec.
- **Prochaine session 08:00 :** confirmer la CI de l'incrément v0.6.6, corriger et fusionner si succès ; puis préparer en journée un calcul astronomique local isolé dans `hue_solar.py` (sans activation du pilotage), avec tests du 21 juin et du 21 décembre en Europe/Zurich, ainsi que des transitions d'heure d'été. Les heures de réveil/coucher personnels resteront distinctes et les réglages actuels inchangés.

## 5 novembre 2026 — v0.6.6 fusionnée, comptes rendus rendus accessibles
- **État vérifié :** la PR #4 d'ergonomie a passé sa CI Python/Node ([41958392901](https://github.com/fchautems/Hue/actions/runs/41958392901)) et a été fusionnée sur `main` au commit `cfd777040c2c416cc62311e656b2b638a00bd019`. Les contrôles post-fusion sur `main` sont consultables via [41969707759](https://github.com/fchautems/Hue/actions/runs/41969707759).
- **Modifications :** fusion de la v0.6.6 (cibles tactiles et focus clavier) ; création du journal de cycle permanent [RELEASE_LOG.md](https://github.com/fchautems/Hue/blob/main/RELEASE_LOG.md) contenant un compte rendu pour 00 h, 04 h et la correction de publication.
- **Contrôles :** tests Python et Node de PR réussis, code relu ; aucune vérification physique sur Raspberry ou lampes. Journal consultable sur la branche `main`.
- **Blocage résolu :** la CI réussie de v0.6.6 n'avait pas été prise en compte par l'automatisation, achevée quelques secondes trop tôt. Le prompt automatique demande désormais explicitement de reprendre et contrôler le résultat final CI avant de conclure.
- **Limite :** l'envoi de notification push dépend de ChatGPT, état de livraison inconnu ; la publication du journal GitHub est vérifiable indépendamment.
- **Prochaine action :** à 08 h, vérifier `main` et la CI, puis créer un incrément de calcul astronomique local (`hue_solar.py`) séparé du pilotage, avec tests des saisons et des changements d'heure Europe/Zurich.


## Cycle 08 h — 2026-11-05 Europe/Zurich
- État vérifié : main v0.6.6, CI 41969707759 réussie, aucune PR ouverte avant intervention, aucune GitHub Release dédiée.
- Code : PR #5, module solaire local autonome hue_solar.py et tests/test_solar.py, sans effet sur Hue ni sur les données locales.
- Contrôles : 3 tests Python locaux réussis après correction de rollover UTC ; GitHub Actions nouvelle PR en attente de verdict final.
- Blocage : ne pas fusionner avant CI concluante et validation des cas de dates locales.
- Prochaine action à 12 h : améliorer hue_solar.py et tests/test_solar.py pour heure d'hiver, date locale et précision de référence ; vérifier CI et fusionner uniquement si validation complète, sans activation de commande de lampes.

- **Publication v0.6.7 :** PR #5 validée par CI 41983753042 (success) et fusionnée sur main, commit fcc336df27bf774605e3c75843b0ef6c0f1b4b12. CI post-fusion 41983798530 terminée avec succès. Aucun déploiement Raspberry.

## Cycle 12 h — 2026-11-05 Europe/Zurich — v0.6.8
- **État vérifié :** `main` initial `8647b33`, aucune PR ouverte ; v0.6.7 et CI post-fusion 41983798530 réussies. Pas de GitHub Release dédiée.
- **Code :** `hue_solar.py` refuse coordonnées non finies, non numériques et booléennes avant calcul ; `tests/test_solar.py` couvre NaN, infinis, types invalides, changement d'heure d'hiver et date locale.
- **Contrôles :** PR #6 CI 42016086337 terminée `success`, fusion squash sur `main` au commit `0ab06fb9760b712fdd335dfeffd8b8f1a80da90f`, CI post-fusion 42016159059 terminée `success`. Aucune lampe ni Raspberry réel testé ou modifié.
- **Blocages :** aucune intégration solaire aux profils ; précision astronomique à comparer à une référence indépendante ; aucune GitHub Release dédiée.
- **Plan 16 h :** ajouter un test de référence de lever/coucher pour Lausanne/Nyon dans `tests/test_solar.py` avec tolérance explicite et, si écart confirmé, corriger uniquement `hue_solar.py` sans toucher aux commandes Hue. Vérifier saisons et DST en CI ; publier seulement après succès. Ensuite envisager l'aperçu solaire purement visuel.

## Cycle 16 h — 2026-11-05 Europe/Zurich — v0.6.9
- **État vérifié :** main dd2ad379 (journal v0.6.8), aucune PR ouverte, CI post-fusion v0.6.8 42016159059 success ; pas de GitHub Release dédiée.
- **Code :** ajout de tests de référence saisonniers Lausanne et dates locales Nyon dans tests/test_solar_reference.py, sans changement de moteur Hue, de réglages ou de calcul de production.
- **Contrôles :** la CI de la PR doit être vérifiée jusqu'au verdict final ; pas de tests physiques Raspberry/ampoules.
- **Blocage :** la référence est volontairement arrondie (tolérance 20 minutes), non une validation astronomique de précision ; ne pas présenter cette couverture comme telle.
- **Plan pour 20 h :** commencer par hue_solar.py : corriger la gestion de la date UTC lors d'un lever/coucher qui franchit minuit UTC, sans modifier les commandes Hue. Ajouter tests/test_solar_dateline.py couvrant longitudes extrêmes, dates locales et cas polaires. Critère : calcul daté correctement et CI Python/Node réussie ; limiter le périmètre au module solaire.


## Cycle 2026-11-05 20:00 Europe/Zurich — v0.6.10
- **État vérifié :** main à `fc8bddaa28de4d8653c6b267304a243b5bc217c0` avant intervention, PR ouvertes : aucune ; CI post-fusion v0.6.9 `42051449446` completed/success. Pas de GitHub Release dédiée.
- **Code :** correction ciblée dans `hue_solar.py` : résolution du jour UTC (-1/0/+1) donnant la date civile locale demandée, au lieu de supposer UTC = date locale. Ajout de `tests/test_solar_dateline.py` pour Kiritimati, Pago Pago, Tokyo, Zurich aux solstices.
- **Contrôles :** simulation Python isolée du même algorithme sur huit combinaisons lieu/date : dates et ordre lever/coucher OK. Vérification GitHub Actions de PR à consigner après création. Aucune commande Hue ni changement de configuration.
- **Limites :** validation du dépôt complet et CI nécessaires avant fusion ; calcul astronomique toujours approximatif, pas de matériel réel.
- **Plan précis cycle 2026-11-06 00:00 (nuit) :** commencer par `tests/test_solar_dateline.py` et `hue_solar.py` ; ajouter tests des transitions de dates civiles autour du Nouvel An (31 décembre/1er janvier) dans les deux fuseaux dateline, corriger uniquement si échec. Critère : tests solaires et CI complète verts ; aucun changement moteur Hue, aucune migration. Vérifier d'abord toute PR ouverte.

- **Publication vérifiée 20 h :** PR #8 fusionnée sur main au commit `15a91fa3eb5fa282125d650bda8afd2168a2e985`. GitHub Actions PR [42089869262](https://github.com/fchautems/Hue/actions/runs/42089869262) completed/success ; post-fusion [42089947588](https://github.com/fchautems/Hue/actions/runs/42089947588) completed/success. Version v0.6.10 publiée sur main (non déployée sur Raspberry). Prochaine étape inchangée : tests du Nouvel An sur la ligne de changement de date, sans pilotage matériel.


## Cycle 2026-11-06 00 h (Europe/Zurich) — v0.6.11
- **État vérifié :** main au commit 35575481 ; aucune PR ouverte avant cycle ; v0.6.10 CI post-fusion réussie (42089947588). Aucune GitHub Release dédiée.
- **Changements :** huit cas supplémentaires de franchissement du Nouvel An à Kiritimati/Pago Pago dans tests/test_solar_dateline.py ; aucune modification du moteur, stockage, profils ou commandes.
- **Contrôles :** CI PR #9 déclenchée (run 42126332719) ; verdict à vérifier avant fusion. Aucun test matériel.
- **Blocage :** ne pas fusionner tant que la CI n'est pas completed/success.
- **Prochain cycle 2026-11-06 04 h :** commencer par tests/test_solar.py : ajouter des tests d'invariance des résultats solaires (mêmes entrées -> mêmes heures), notamment changement de fuseau et dates hivernales ; corriger hue_solar.py uniquement en cas d'échec. Critère : suite complète CI verte ; aucun changement de comportement des lampes.

## Cycle 2026-11-06 04 h (Europe/Zurich) — v0.6.12
- **État vérifié :** main c6e52ec (confirmation CI v0.6.11), aucune PR ouverte ; CI v0.6.11 post-fusion 42126397135 completed/success. Pas de GitHub Release dédiée.
- **Code :** tests/test_solar.py enrichi de tests de reproductibilité sur quatre dates et d'invariance d'instants UTC sur trois dates (hiver, été, changement d'heure d'hiver). Aucun changement moteur Hue, stockage, interface ni Raspberry.
- **Contrôles :** validation CI de PR à attendre avant toute fusion ; aucun essai physique.
- **Blocage éventuel :** si CI non concluante, conserver la PR sans fusion et reprendre sa validation.
- **Plan précis cycle 2026-11-06 08 h :** commencer par tests/test_solar.py et hue_solar.py : tester la cohérence du calcul autour de l'équinoxe, sans modifier le moteur de lampes ; ajouter un test de progression saisonnière et corriger seulement si nécessaire. Critère : suite CI verte, dates locales correctes, aucun effet sur Hue. En journée, envisager ensuite un aperçu ergonomique des heures solaires sans commande matérielle.

- **Publication confirmée 04 h :** PR #10 fusionnée sur main c3eda0f7b7bdbdf26ad48a9736b4df2b2347504a ; CI PR 42153467048 completed/success ; CI main 42153532541 completed/success. Prochain incrément : test de progression équinoxe dans tests/test_solar.py, puis aperçu non pilotant.


## Cycle 2026-11-06 08 h (Europe/Zurich) — v0.6.13
- **État vérifié :** main 07371be (documentation v0.6.12) ; PR #11 créée sur branche isolée. Dernière version de code confirmée sur main : v0.6.12.
- **Changements :** tests/test_solar.py : nouveau test de progression des levers/couchers autour de l'équinoxe de mars à Nyon (dates locales, progression monotone, absence de sauts anormaux). Aucun changement du moteur Hue, stockage, modes ni Raspberry.
- **Contrôles :** GitHub Actions run 42177586752 lancé ; attendre le verdict completed/success avant toute fusion. Clone local impossible (DNS GitHub indisponible). Aucun test matériel.
- **Blocage :** CI en cours ; ne pas fusionner avant conclusion.
- **Prochaine session 2026-11-06 12 h :** commencer par le verdict de la PR #11 ; si verte, fusionner et vérifier la CI main. Puis examiner templates/index.html et static/v061.js pour une prévisualisation des horaires solaires en lecture seule, sans sauvegarde ni commandes. Critère : horaires visibles sur téléphone et PC, aucun appel de commande Hue, tests UI/CI verts. Risque : intégration UI ; préserver Manuel/Auto et simulation accélérée.

- **Publication confirmée 08 h :** PR #11 fusionnée sur main au commit 0aa089de08c317850cf28f2a4e183615954f1a8b ; CI PR 42177638803 completed/success. Vérifier la CI post-fusion. Plan suivant : aperçu solaire non pilotant, fichiers templates/index.html et static/v061.js ; test contrat UI et CI verte.

## Correctif « mises à jour invisibles » — 2026-11-06 (Europe/Zurich), branche en validation
- **État vérifié :** l'interface affichait toujours v0.6.4 malgré les commits plus récents ; le moteur de mise à jour compare bien les SHA Git, mais n'indiquait pas les changements.
- **Changements préparés :** lecture locale du SHA installé sans réseau dans hue_update_api.py ; révision exacte visible dans l'interface ; CSS/JS versionnés par SHA pour invalider le cache après mise à jour ; HTML avec Cache-Control no-store ; panneau « Quoi de neuf ? » dans Mises à jour, qui distingue les changements d'interface des tests et autres changements internes. Le worker de mise à jour conserve les titres des commits installés et le dernier historique. Le journal RELEASE_LOG.md sert de repli pour le premier passage depuis une ancienne version du worker.
- **Contrôles :** tests Python tests/test_update_visibility.py et Node tests/test_update_ui.cjs ; node --check static/app.js dans GitHub Actions. Verdict CI requis avant fusion ; aucun essai Raspberry/ampoules.
- **Contraintes :** aucun changement de commandes Hue, réglages, ou mode Manuel/Auto. Première mise à jour depuis l'ancien worker : seulement le dernier cycle du journal comme repli, pas de comparaison de commits.
- **Prochaine action :** valider la PR et la suite CI ; fusionner dans main seulement après succès. Vérifier CI main et compléter RELEASE_LOG.md ; reprise de l'aperçu solaire non pilotant au cycle de 12 h.
 
## Validation du correctif mises à jour — 2026-11-06
- **État vérifié :** PR #12 fusionnée sur main, commit bb36b475a80c5323c63ddb3abb3b313bfe49b3c8.
- **Contrôles :** GitHub Actions de PR run 42178779968 completed/success (tests Python, contrôles JS). CI main post-fusion pas encore vérifiée. Tests Raspberry et matériel : non réalisés.
- **Documentation :** RELEASE_LOG.md contient désormais le résumé lisible, en plus du journal de cycles.
- **Prochaine action :** vérifier la CI main et les informations d'installation sur le Raspberry lors de la prochaine mise à jour ; poursuivre l'aperçu solaire purement visuel, sans commandes Hue.

## v0.7.0 — Aperçu solaire et rythme personnel — 2026-11-06
- **État vérifié :** reprise sur main `64b9372` ; tâche automatique « Développement agile Hue Lab » mise en pause à la demande de Fréd (confirmation du service). Aucun prochain cycle demandé.
- **Changements :** panneau visible dans Horloge & lumières : Le Muids/Arzier, Nyon, Lausanne ou coordonnées/fuseau personnalisés ; date, retour à aujourd’hui, heures de lever/coucher, durée du jour, frise jour/nuit et repères personnels réveil/coucher. Préférences d’aperçu dans le navigateur uniquement. API GET `/api/solar/preview`, calcul local, aucun accès au contrôleur ou aux réglages Hue. Gestion des erreurs, cas polaires et réponses asynchrones devenues obsolètes.
- **Contrôles locaux :** 177 tests Python réussis ; suites Node existantes et nouveau test solaire réussis ; compilation Python et syntaxe solaire JS valides. Le lancement Chromium local est bloqué par les sockets système ; contrôle navigateur 320/390/1320 px préparé pour GitHub Actions, non exécuté.
- **Limites :** événements solaires approximatifs, sans relief ni météo ; aperçu indépendant du pilotage. Aucun essai Raspberry/ampoules ni déploiement matériel. L’aperçu ne génère pas encore de profil automatique solaire.
- **Prochaine action :** demander l’autorisation explicite de publication, puis exécuter la CI navigateur et publier après succès. Reprise ultérieure : proposer un brouillon de profil luminosité ET couleur issu du rythme personnel et du soleil, avec activation explicite. Automatisation laissée en pause.

### Blocage de publication — 2026-11-06
- Commit local de fonctionnalité créé ; l’envoi Git vers la branche de travail a été refusé par la revue automatique, qui juge l’autorisation de développement insuffisante pour une publication externe. Aucun contournement ni nouvelle tentative d’envoi.
- Publication et CI navigateur non effectuées. Code et tests conservés localement ; aucun déploiement matériel.
- Prochaine action : accord explicite de Fréd pour publier `fchautems/Hue`, puis branche/CI et fusion après succès. La tâche automatique reste en pause.

### Publication autorisée — 2026-11-06
- Fréd a explicitement donné carte blanche pour publier cette version. Le blocage d’autorisation précédent est résolu ; validation CI navigateur en cours de préparation, tâche automatique toujours en pause.

## v0.7.0 publiée et validée — 2026-11-06
- **État vérifié :** publication explicitement autorisée par Fréd ; PR #13 fusionnée sur main au commit `fc9f8d1c173207ed4d27f722cdba8361d47f7457`. Ancien blocage de publication résolu.
- **Contrôles :** CI PR [42186168064](https://github.com/fchautems/Hue/actions/runs/42186168064) et CI main [42186352053](https://github.com/fchautems/Hue/actions/runs/42186352053) terminées completed/success : suite Python, régressions Node et scénarios Chromium 320/390/1320 px. Captures mobile/PC relues ; espacement desktop et masquage des cas polaires corrigés avant fusion.
- **Livré :** aperçu solaire hors ligne dans Horloge & lumières (lieu, date, lever/coucher, durée du jour, frise, réveil/coucher personnel). Aucun changement aux commandes des lampes ni aux profils persistants. Pas de déploiement ni d’essai physique Raspberry/Hue.
- **Blocages :** aucun pour la publication GitHub. Le nouvel aperçu ne génère pas encore de profil automatique solaire.
- **Prochaine action :** installer via Mises à jour sur le Raspberry et vérifier l’aperçu ; développement futur du brouillon de profil solaire luminosité/couleur à activation explicite. Tâche toutes les quatre heures maintenue en pause, aucune reprise automatique.

## v0.7.1 — Brouillon solaire luminosité et couleur — 2026-11-06
- Générateur borné par réveil/coucher personnels ; montée de 30 à 120 minutes, descente de 30 à 180 minutes modulées par les heures solaires. Repli rythme personnel pour les cas polaires ; journée sans passage de minuit, durée minimale trois heures.
- Aperçu graphique, couleur et luminosité par pas de quinze minutes ; minimum/maximum réglables. Profil fixe pour la date choisie, aucune adaptation quotidienne ou météo revendiquée.
- Application explicite atomique luminosité/couleurs compatibles à une lampe ; modes, état ON/OFF, Vacances et anciennes courbes personnalisées conservés. Aucune commande de pont dans la route d’application ; le worker normal applique ensuite si Auto. Restauration mémoire si sauvegarde échoue.
- Contrôles locaux : suite Python et Node ; CI et navigateur à vérifier avant publication. Aucun essai matériel.
- Prochaine action : terminer CI et publier ; tâche automatique maintenue en pause.

## v0.7.1 publiée — 2026-11-06
- PR #14 fusionnée sur main au commit `dc454a1047c98e6e0c39134df71cc137e4c5ca75`. [CI PR 42189702290](https://github.com/fchautems/Hue/actions/runs/42189702290) et [CI main 42189888211](https://github.com/fchautems/Hue/actions/runs/42189888211) completed/success.
- 181 tests Python locaux réussis ; régressions Node et scénarios navigateur réussis, dont brouillon, curseur, invalidation après édition, rythme invalide, annulation et application explicite (requête simulée en navigateur). Capture du brouillon relue.
- Profil fixe pour la date choisie, sans recalcul quotidien ni météo. Modes Manuel/Auto, ON/OFF, Vacances préservés ; ancien profil personnalisé conservé dans les réglages avancés. Aucun essai physique ni déploiement Raspberry.
- Prochaine action : tester depuis Mises à jour sur Raspberry ; prochaine évolution possible : configuration solaire persistante recalculée chaque jour, réutilisant ce générateur avec aperçu et activation explicite. Tâche automatique toujours en pause.

## Refonte ergonomique v0.8.0 — analyse du 2026-11-06
- **Base vérifiée :** `main` à `9b0388e`, copie de travail propre ; aucun MODEL_GUIDE.md ni AGENTS.md dans le dépôt. Brain non exposé dans cette session. Automatisation laissée en pause.
- **Inventaire :** Tableau de bord (commandes individuelles, Manuel/Auto, Vacances et test 60 s), Horloge & lumières (horloge, simulation, soleil, sélecteur de lampe, copies, RGB, courbes simple/personnalisée), Historique, Diagnostics & logs (capacités, powerup, latences, tests secteur, exports), Connexion au pont, Mises à jour.
- **Comportements vérifiés dans le code :** un seul sélecteur réel/accéléré existe déjà, mais apparaît à tort dans les écrans techniques. La découverte utilise le service Internet Hue, pas une découverte LAN ; son résultat écrase le champ IP. L'adresse 10.0.0.2 vient du modèle et de la valeur HTML, pas d'un résultat réseau fabriqué par le serveur. Les deux copies diffèrent volontairement (courbe seule / profil complet). Le test Vacances et la simulation des courbes ont des moteurs et finalités distincts.
- **Décision :** trois activités principales (Lampes & vacances, Profils & simulation, Historique), Paramètres secondaires pour pont/avancé/maintenance, accès permanent aux mises à jour. Conserver les deux copies et simulations distinctes, tous les contrats de stockage et toutes les commandes matérielles.
- **Contrôles à venir :** suite Python/Node complète, tests navigateur de navigation, sauvegardes, découvertes asynchrones et affichage 320/390/1320 px ; pas d'accès au pont ou au Raspberry réel.
- **Prochaine action :** implémenter le regroupement et corriger le parcours pont sans migration des données ; publier uniquement après validation.

### v0.8.0 — première implémentation et contrôles locaux
- **Changements :** navigation par activités et Paramètres regroupés ; raccourci permanent de mise à jour avec badge ; courbe/horloge rapprochées, lampe en tête, couleurs/soleil/copies en volets. Sélecteur réel/accéléré déplacé dans l'horloge ; toutes les simulations et copies distinctes conservées.
- **Pont :** modèle neuf sans IP imposée ; configuration existante préservée ; IP saisie conservée pendant recherche/initialisation asynchrones ; sélection visible uniquement pour plusieurs résultats ; instructions d'association clarifiées. Repli SSDP Hue local borné après échec/résultat vide du service Internet, sans dépendance supplémentaire ni balayage du sous-réseau.
- **Robustesse :** protection des brouillons pour tous les accès de navigation, y compris les raccourcis programmatiques, avec restauration des champs après abandon explicite.
- **Contrôles locaux :** 187 tests Python réussis ; six suites Node réussies, syntaxe JS et compilation Python valides. Scénarios navigateur ajoutés pour responsive 320/390/1320, profils/couleurs/simulation, IP asynchrone, association, copies, Vacances, historique, diagnostics et mises à jour.
- **Limite :** Chromium local bloqué par création de socket système (Operation not permitted). Les scénarios navigateur seront exécutés par CI sur branche avant fusion. Aucun test matériel ni déploiement Raspberry. Données privées, schémas de stockage, worker Hue et services systemd inchangés.
- **Prochaine action :** publication autorisée sur branche, CI navigateur, corrections éventuelles puis fusion et vérification de la CI main.

### v0.8.0 — contrôle navigateur initial
- CI PR #15 : Python, Node et scénario solaire réussis ; navigation responsive, simulation, sauvegardes/brouillons, copies et découverte passés jusqu'au contrôle marche/arrêt. Échec du script de test : il cliquait l'input masqué sous le décor de l'interrupteur, au lieu de son label visible. Test corrigé pour utiliser le contrôle réellement cliquable.
- Captures 320/390/1320 relues : aucune troncature horizontale de la page. Suppression du titre « Courbe de luminosité » répété et du lien vers Diagnostics déjà dans ce même panneau. Navigation mobile rendue persistante pour garder l'accès aux mises à jour lors du défilement.
- Ajout d'un bouton explicite « Utiliser [IP] » si un seul pont détecté diffère de l'adresse saisie : aucune frappe ni remplacement automatique nécessaire. Une configuration déjà appairée ne lance aucune recherche au simple passage dans Paramètres.
- Prochaine action : rejouer la CI complète et terminer les parcours Vacances/diagnostics/installation initiale.

### v0.8.0 — validation complète avant fusion
- **État vérifié :** code `ca304929a3e97f70752f2aebddd1083511dc4808`, PR #15 ; [CI 42250031236](https://github.com/fchautems/Hue/actions/runs/42250031236) completed/success.
- **Contrôles :** 187 tests Python ; six suites Node ; compilation Python/syntaxe JS ; deux scénarios Chromium complets. Responsive 320/390/1320 px, horloge visible, aucune page débordant horizontalement, sauvegarde/annulation/brouillons des profils simple/personnalisé/RGB, deux copies, référence réelle/accélérée et pause/vitesse, IP conservée pendant recherche, sélection explicite du pont, association, ON/OFF et Manuel/Auto, Vacances et test 60 s, historique, dialogue powerup, export JSON, logs, badge et disponibilité de l'installation.
- **Relecture visuelle :** captures finales 390 et 1320 relues, captures 320 de la première passe également relues ; doublons de titres corrigés. Contrôles utiles conservés ; seul l'ancien raccourci Diagnostics devenu une auto-navigation dans son nouveau panneau a été retiré.
- **Limites :** pont simulé uniquement ; SSDP dépend du support/filtrage multicast du réseau. Pas d'essai physique ni de déploiement Raspberry. Pas de migration de données, schémas de profils et moteurs inchangés. Tâche automatique laissée en pause.
- **Prochaine action :** fusion autorisée sur main, vérification CI post-fusion ; puis installation depuis Mises à jour sur Raspberry et validation matérielle par Fréd.


### v0.8.0 publiée — 2026-11-06
- PR #15 fusionnée sur main au commit `dad1066915666a1e32d935030ec102c655919ad9`.
- [CI avant fusion 42250031236](https://github.com/fchautems/Hue/actions/runs/42250031236) et [CI main 42250382795](https://github.com/fchautems/Hue/actions/runs/42250382795) completed/success : 187 tests Python, régressions Node et deux parcours Chromium complets. Captures téléphone/PC relues.
- Version disponible via Mises à jour. Aucun déploiement Raspberry ni essai matériel effectué ; paramètres, profils et données privées conservés, aucun changement des moteurs de pilotage. Automatisation laissée en pause.
- Prochaine action : installation et validation matérielle par Fréd, notamment découverte sur le LAN réel et maintien des profils/couleurs/Vacances.
