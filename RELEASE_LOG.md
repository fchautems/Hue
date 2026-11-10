# v0.14.1 — Navigation mobile cohérente — 2026-11-10

- Les six onglets restent sur deux rangées, sans défilement horizontal, et le titre Hue Lab apparaît aussi sur l’accueil Pièces.

# v0.14.0 — Pièces et lampes à l’accueil — 2026-11-10

- Retrouve les pièces et zones configurées sur le pont. Dans chaque carte, le bouton marche/arrêt commande le groupe et chaque lampe se commande directement.
- L’accueil affiche les commandes dans une grille compacte. Les réglages par lampe, le réveil et Vacances restent dans Lampes & vacances.

# v0.13.0 — Manuel temporaire avec les télécommandes Hue — 2026-11-09

- Les touches de gradation et la molette suspendent Auto sur les lampes concernées lorsque le pont expose leur association. Une extinction suivie d’un rallumage fait reprendre le profil.
- L’écran affiche « Manuel temporaire » pendant la suspension. Le bouton Auto permet aussi de reprendre immédiatement.

# v0.12.0 — Réveil lumineux — 2026-11-08

- Une carte dans Lampes & vacances règle la lampe, la couleur, le nombre de minutes d’avance et la luminosité à l’heure du réveil.
- Hue Lab Android 0.2 transmet le prochain réveil au Raspberry sur le Wi-Fi local. La carte confirme l’heure reçue. Le Raspberry exécute ensuite la montée sans dépendre du téléphone.

# v0.11.1 — Couleur du soir plus tôt — 2026-11-08

- Soleil : la couleur du soir apparaît progressivement dès le coucher solaire, pendant que la luminosité suit sa baisse tardive. Les niveaux configurés au coucher personnel et de nuit restent les mêmes.

# v0.11.0 — Simulation et navigation — 2026-11-07

- Pause et reprise à côté du curseur. Déplace le curseur ou saisis une heure pour mettre la simulation en pause à cet instant.
- Mises à jour ouvre sa propre page. Les réglages du pont et les diagnostics restent accessibles dans Paramètres.
- Les trois paires de champs Soleil restent alignées quand un libellé revient à la ligne.
- Prototype Android séparé. L’icône ouvre l’interface web du serveur local.

# v0.10.1 — Installation sans Node.js — 2026-11-07

- Corrige l’installation de la v0.10.0 depuis le Raspberry. Le test comparant les courbes Python et JavaScript s’exécute sur GitHub. L’installateur embarqué peut lancer sa suite Python sans Node.js.
- Depuis Mises à jour, vérifier GitHub puis installer et redémarrer. L’installateur de la v0.9.0 peut appliquer directement ce correctif.

# v0.10.0 — Réveil anticipé, soirée confortable — 2026-11-06 — PUBLIÉE SUR MAIN

- Soleil : niveaux de confort et saturation réglables au réveil/coucher, durée commune avant réveil/après coucher, nuit au minimum lumineux et saturation 100 %.
- Courbes en S asymétriques : montée avancée, baisse retardée ; transitions nocturnes possibles à travers minuit, sans chevauchement.
- Trois teintes pleines matin/soir/nuit et blanc de journée indépendant, référence 5’000 K ajustable de 4’000 à 6’500 K. Conversion xy et gamut de la lampe ; aperçu écran indicatif.
- Formulaire par lampe avec un seul enregistrement, deux courbes luminosité/saturation et aperçu daté sans commande. L’ancien profil est conservé jusqu’à l’adoption explicite.
- Persistance, saisons, fuseau, Manuel/OFF/Vacances et copies préservés. La copie de luminosité seule ne remplace pas les couleurs de destination.
- Validation : 207 tests Python, six suites Node et deux parcours Chromium 320/390/1320 px réussis, CI PR 42303072513 et main 42303253108 completed/success ; captures relues. PR #18 fusionnée au commit 0b63a4c. Aucun essai matériel ni déploiement Raspberry.

# v0.9.0 — Soleil au quotidien — 2026-11-06 — PUBLIÉE SUR MAIN

- Un seul choix de profil par lampe : Simple, Personnalisé ou Soleil.
- Soleil mémorise le lieu, le réveil/coucher et les niveaux lumineux. Les horaires se recalculent automatiquement chaque jour, selon le fuseau du lieu, y compris après redémarrage. Aucun besoin de réappliquer le profil.
- La date sert uniquement à prévisualiser une autre journée ; l’aperçu ne modifie ni les réglages ni la lampe.
- Manuel suspend le suivi, Auto l’exécute, Vacances garde la priorité ; une lampe éteinte reste éteinte.
- Les couleurs suivent les horaires du jour. Leur édition conserve Soleil et les anciens profils fixes restent intacts. La copie complète garde le suivi quotidien ; la copie de luminosité seule produit une courbe fixe du jour.
- Validation : 198 tests Python, six suites Node et parcours navigateur 320/390/1320 px réussis ; CI PR 42283707888 et CI main 42283937344 completed/success, captures relues. PR #17 fusionnée au commit ba02d8f. Pas d’essai matériel ni de déploiement Raspberry. Sans météo.

# v0.8.1 — Soleil et cible cohérents — 2026-11-06 — PUBLIÉE SUR MAIN

- Cible issue du profil actif calculé par le serveur : suppression de l’alternance avec l’ancienne courbe. Luminosité lue sur le pont et état Manuel/Auto/Vacances visibles séparément.
- Nouveaux profils solaires : lever/coucher du soleil utilisés sans plafonds de deux/trois heures ; montée rapide le matin et baisse plus tardive le soir. Teintes existantes conservées ; les anciens profils ne changent pas automatiquement.
- Préparation solaire avant les couleurs, aperçu clairement séparé des commandes et retour après application à la lampe nommée.
- Profil toujours fixe pour la date choisie : régénérer et appliquer pour profiter de la correction. Pas de recalcul quotidien ni météo dans cette version.
- Sélection Simple/Personnalisée réversible pour consulter les courbes ; protection des champs modifiés conservée.
- Validation : 192 tests Python, six suites Node et parcours navigateur 320/390/1320 px réussis ; CI PR 42264568465 et CI main 42264894227 completed/success, captures relues. PR #16 fusionnée, commit 20204fb. Aucun test matériel ni déploiement Raspberry.

# v0.7.1 — 6 novembre 2026 — PUBLIÉE SUR MAIN

## v0.8.0 — Navigation par activités — 2026-11-06
- Trois activités : Lampes & vacances, Profils & simulation, Historique. Pont, diagnostics, powerup, logs et maintenance regroupés dans Paramètres.
- Mises à jour en accès permanent, badge de disponibilité et statut local rafraîchi chaque minute.
- Sélecteur de lampe en premier, courbe et horloge rapprochées, couleurs/soleil/copies repliables ; référence réelle/accélérée unique dans le simulateur.
- IP initiale vide, configuration existante conservée, recherche sans écrasement des saisies ; liste réservée aux résultats multiples et repli réseau local SSDP.
- Contrats de stockage et moteurs de pilotage inchangés. Tests Python/Node et parcours navigateur avec pont simulé ; aucun déploiement Raspberry ni test physique.


- **Code concret :** générateur de profil luminosité/couleurs à partir du réveil/coucher et du soleil, niveaux mini/maxi réglables, courbe et aperçu couleur par curseur. Application explicite à la lampe choisie, avec confirmation.
- **Limite claire :** profil fixe pour la date sélectionnée. Aucune adaptation quotidienne ou météo. Modes Manuel/Auto, ON/OFF et Vacances préservés ; une lampe déjà en Auto peut appliquer le nouveau profil immédiatement. Luminosité seule sur lampe non RGB.
- **Publication :** [PR #14](https://github.com/fchautems/Hue/pull/14), [commit dc454a1](https://github.com/fchautems/Hue/commit/dc454a1047c98e6e0c39134df71cc137e4c5ca75).
- **Tests :** 181 tests Python locaux réussis, CI Python/Node/Chromium [PR 42189702290](https://github.com/fchautems/Hue/actions/runs/42189702290) et [main 42189888211](https://github.com/fchautems/Hue/actions/runs/42189888211) completed/success. Annulation/application, erreurs et aperçu testés ; capture relue. Aucun essai physique ni déploiement Raspberry.
- **Suite :** installer depuis Mises à jour et tester le brouillon. Évolution future : recalcul solaire quotidien configurable. Automatisation de développement toujours en pause.

# v0.7.0 — 6 novembre 2026 — PUBLIÉE SUR MAIN

- **Code concret :** aperçu solaire visible dans Horloge & lumières : lieu/date, lever et coucher du soleil, durée du jour, frise jour/nuit et comparaison avec tes heures de réveil/coucher. Calcul hors ligne ; préférences d’aperçu locales au navigateur.
- **Publication :** [PR #13](https://github.com/fchautems/Hue/pull/13), commit [fc9f8d1](https://github.com/fchautems/Hue/commit/fc9f8d1c173207ed4d27f722cdba8361d47f7457).
- **Tests :** 177 tests Python locaux réussis ; suites Python/Node et navigateur Chromium 320/390/1320 px réussies en [CI PR](https://github.com/fchautems/Hue/actions/runs/42186168064) et [CI main](https://github.com/fchautems/Hue/actions/runs/42186352053), toutes deux completed/success. Captures mobile et PC relues.
- **Matériel :** installation sur Raspberry et essais avec ampoules non effectués. L’aperçu ne commande aucune lampe et ne modifie aucun profil.
- **Décision :** tâche toutes les quatre heures mise en pause à la demande de Fréd. Aucune reprise automatique prévue. Autorisation de publication confirmée, blocage précédent résolu.
- **Suite :** installer depuis Mises à jour, puis lors d’une prochaine session proposer un brouillon de profil solaire luminosité/couleur avec activation explicite.

# Hue Lab — journal des cycles et des publications

## 6 novembre 2026 — correction visible des mises à jour (Europe/Zurich)

**Correctif PUBLIÉ sur main — commit bb36b475.** Il ne modifie pas les commandes des lampes.

- **Problème corrigé :** bandeau affichant toujours v0.6.4, même après une mise à jour réelle ; différences non expliquées ; ressources CSS/JS pouvant rester en cache.
- **Code concret :** affichage de la véritable révision Git installée, ressources CSS/JS versionnées automatiquement par commit et HTML non mis en cache ; nouveau bloc « Quoi de neuf ? » indiquant les commits d'une mise à jour et distinguant les changements visuels des changements internes. Dernier journal de release affiché en secours après la première installation depuis l'ancien moteur de mise à jour.
- **Tests :** PR [#12](https://github.com/fchautems/Hue/pull/12) : GitHub Actions [42178779968](https://github.com/fchautems/Hue/actions/runs/42178779968), **completed/success** (suite Python complète et vérification JavaScript). Contrôle post-fusion de main non confirmé au moment de cette note.
- **Publication :** [commit bb36b475](https://github.com/fchautems/Hue/commit/bb36b475a80c5323c63ddb3abb3b313bfe49b3c8). Aucune installation ni vérification sur le Raspberry, aucun test Hue physique.
- **Limites :** la première installation avec l'ancien worker ne dispose pas de liste comparative rétroactive ; la page affiche alors le dernier cycle du journal. Par la suite, les titres des commits installés sont conservés pour consultation.
- **Suite :** vérifier après mise à jour Raspberry que la révision affichée correspond au commit Git ; tester l'affichage « Quoi de neuf ? » pour une version interne puis une version d'interface. Reprendre la prévisualisation solaire non pilotante dans la session de développement suivante.

## 6 novembre 2026 — cycle de 08 h (Europe/Zurich ; démarré avant 08 h)

**v0.6.13 — PUBLIÉE sur main (commit 0aa089d).**

- **Code concret :** test de progression des horaires solaires autour de l'équinoxe à Nyon dans `tests/test_solar.py` : dates locales, lever avançant, coucher reculant et absence de saut de plusieurs heures. Aucune commande Hue, migration ou donnée locale modifiée.
- **Tests :** GitHub Actions de PR #11 [42177638803](https://github.com/fchautems/Hue/actions/runs/42177638803) completed/success ; CI initiale [42177586752](https://github.com/fchautems/Hue/actions/runs/42177586752) completed/success. CI post-fusion à vérifier ; aucun test réel Raspberry/ampoules. Clone local impossible : DNS github.com indisponible dans le conteneur.
- **Publication :** [PR #11](https://github.com/fchautems/Hue/pull/11) fusionnée, [commit main 0aa089d](https://github.com/fchautems/Hue/commit/0aa089de08c317850cf28f2a4e183615954f1a8b). Pas de GitHub Release dédiée.
- **Blocage :** aucun pour fusion ; validation post-fusion à confirmer.
- **Plan du 6 novembre à 12 h :** commencer par `templates/index.html` et `static/v061.js` ; préparer un aperçu en lecture seule des heures solaires calculées, adapté téléphone et PC, sans modifier Manuel/Auto, les profils ni envoyer de commandes. Ajouter un test de contrat UI/serveur et vérifier la CI avant fusion. Risque : complexité de l'interface ; limiter l'incrément à l'affichage.


## 6 novembre 2026 — cycle de 04 h (Europe/Zurich)

**v0.6.12 — PUBLIÉE sur `main` (commit c3eda0f).**

- **Code concret :** `tests/test_solar.py` vérifie la reproductibilité des heures solaires à quatre dates (dont les deux changements d'heure suisses) et l'invariance des instants UTC entre fuseaux Europe/Zurich et UTC sur trois dates. Aucun changement du pilotage Hue, des profils, des réglages ou du Raspberry.
- **Tests :** GitHub Actions PR #10 [42153467048](https://github.com/fchautems/Hue/actions/runs/42153467048) **completed/success** ; CI post-fusion [42153532541](https://github.com/fchautems/Hue/actions/runs/42153532541) **completed/success**. Aucun test matériel.
- **Publication :** [PR #10](https://github.com/fchautems/Hue/pull/10) fusionnée ; [commit main c3eda0f](https://github.com/fchautems/Hue/commit/c3eda0f7b7bdbdf26ad48a9736b4df2b2347504a). Pas de GitHub Release dédiée.
- **Blocages :** aucun pour la fusion ; précision astronomique approximative et absence de tests physiques demeurent.
- **Plan du 6 novembre à 08 h (jour) :** commencer par `tests/test_solar.py` pour ajouter un test de progression des horaires solaires autour de l'équinoxe à Nyon ; corriger `hue_solar.py` seulement en cas d'écart. Critère : dates locales et suite CI verte, aucune commande de lampe. Ensuite préparer un aperçu ergonomique non pilotant des heures solaires.


## 6 novembre 2026 — cycle de 00 h (Europe/Zurich)

**v0.6.11 — PUBLIÉE sur `main` (commit 81bc94f).**

- **Code concret :** 8 scénarios de dates civiles 31 décembre / 1er janvier (2025–2027) à Kiritimati et Pago Pago dans `tests/test_solar_dateline.py`, avec vérification du jour local et de l'ordre lever/coucher. Aucun changement de pilotage Hue, données locales ni Raspberry.
- **Tests :** GitHub Actions PR #9 run [42126332719](https://github.com/fchautems/Hue/actions/runs/42126332719) **completed/success**. CI sur la tête finale de PR [42126379228](https://github.com/fchautems/Hue/actions/runs/42126379228) **completed/success** et post-fusion [42126397135](https://github.com/fchautems/Hue/actions/runs/42126397135) **completed/success**. Aucun test matériel.
- **Publication :** [PR #9](https://github.com/fchautems/Hue/pull/9) fusionnée, [commit main 81bc94f](https://github.com/fchautems/Hue/commit/81bc94f52b83079a6d5a92f6c505c3a2238bb84d). Pas de GitHub Release dédiée.
- **Blocage :** aucun ; CI complète réussie avant et après fusion.
- **Plan du 6 novembre à 04 h (nuit) :** commencer par `tests/test_solar.py` : tester la reproductibilité des horaires solaires et les conversions de fuseaux à date fixe ; n'ajuster `hue_solar.py` qu'en cas d'échec. Critère : suite complète verte ; aucun changement de commandes Hue ni des réglages.


## 5 novembre 2026 — cycle de 20 h (Europe/Zurich)

**v0.6.10 — PUBLIÉE sur `main`.**

- **Code concret :** `hue_solar.py` choisit le bon jour UTC pour que lever et coucher correspondent à la date civile locale demandée, même près de la ligne internationale de changement de date. Nouveau `tests/test_solar_dateline.py` : Kiritimati, Pago Pago, Tokyo, Zurich, solstices et ordre des événements. Aucune commande Hue ni donnée locale modifiée.
- **Tests :** simulation Python isolée sur 8 combinaisons lieu/date réussie ; GitHub Actions PR #8 [42089869262](https://github.com/fchautems/Hue/actions/runs/42089869262) **completed/success** ; post-fusion [42089947588](https://github.com/fchautems/Hue/actions/runs/42089947588) **completed/success**.
- **Publication :** [PR #8](https://github.com/fchautems/Hue/pull/8), [commit main 15a91fa](https://github.com/fchautems/Hue/commit/15a91fa3eb5fa282125d650bda8afd2168a2e985). Pas de GitHub Release dédiée, pas de déploiement Raspberry.
- **Limites :** précision astronomique approximative, aucune validation matérielle. Aucun blocage de publication.
- **Plan du 6 novembre à 00 h (nuit) :** commencer par `tests/test_solar_dateline.py` : ajouter les cas 31 décembre/1er janvier à Kiritimati et Pago Pago, puis corriger `hue_solar.py` seulement si un test échoue. Critère : dates locales et ordre des événements corrects, CI complète verte ; aucun changement de commande Hue ou de stockage.

Ce fichier est le **point de consultation permanent des comptes rendus**. Il doit être enrichi **après chaque exécution automatisée, toutes les quatre heures**, même si la version n'est pas publiée. Les informations les plus récentes figurent en premier.

**Attention :** une version indiquée « publiée » signifie **fusionnée dans la branche `main` sur GitHub**, pas installée ni vérifiée sur le Raspberry. Les notifications mobiles dépendent des réglages ChatGPT ; ce fichier permet de retrouver les résultats indépendamment de leur livraison.

## 5 novembre 2026 — cycle de 16 h (Europe/Zurich)

**v0.6.9 — PUBLIÉE sur `main`.**

- **Code concret :** ajout de `tests/test_solar_reference.py` pour contrôler les horaires locaux approximatifs des solstices à Lausanne et les dates locales des transitions DST à Nyon. Aucune commande Hue, donnée locale ou profil modifié.
- **Tests :** CI PR #7 [42051357603](https://github.com/fchautems/Hue/actions/runs/42051357603) **completed/success** ; CI post-fusion [42051449446](https://github.com/fchautems/Hue/actions/runs/42051449446) **completed/success**. Les valeurs de référence sont arrondies avec une tolérance de 20 minutes ; ce n'est pas une certification astronomique.
- **PR :** [#7](https://github.com/fchautems/Hue/pull/7). Fusion squash sur main : [113fca8](https://github.com/fchautems/Hue/commit/113fca8d3c6db1a9d1bca2aba11f3981c3baf503).
- **Blocage :** PR fusionnée après CI verte ; CI post-fusion réussie ; aucun essai physique.
- **Plan à 20 h :** corriger dans `hue_solar.py` les franchissements de minuit UTC aux longitudes extrêmes, puis ajouter `tests/test_solar_dateline.py`. Critère : dates locales exactes et CI verte, sans modifier le pilotage des lampes.

## 5 novembre 2026 — cycle de 12 h (Europe/Zurich)

**v0.6.8 — PUBLIÉE sur `main`.**

- **Code concret :** `hue_solar.py` rejette NaN, infinis et types invalides pour les coordonnées ; `tests/test_solar.py` ajoute les tests d'heure d'hiver suisse, dates locales et entrées invalides. Aucune activation du contrôle solaire, aucune commande Hue modifiée.
- **Tests :** CI PR #6 [42016086337](https://github.com/fchautems/Hue/actions/runs/42016086337) **completed/success** ; CI post-fusion [42016159059](https://github.com/fchautems/Hue/actions/runs/42016159059) **completed/success**. Aucun test sur Raspberry ou ampoules réelles.
- **Publication :** [PR #6](https://github.com/fchautems/Hue/pull/6) fusionnée, [commit main 0ab06fb](https://github.com/fchautems/Hue/commit/0ab06fb9760b712fdd335dfeffd8b8f1a80da90f). Pas de GitHub Release dédiée ni installation Raspberry.
- **Limites :** calcul astronomique encore approximatif ; pas de profil intelligent activé.
- **Plan précis à 16 h :** commencer par `tests/test_solar.py` : ajouter une comparaison avec heures solaires de référence à Nyon/Lausanne, avec tolérance documentée ; corriger `hue_solar.py` seulement si nécessaire. Critère : tests saisons, DST et référence verts en CI, aucune modification du moteur de lampes.


## 5 novembre 2026 — cycle de 08 h (Europe/Zurich ; démarré à 07 h 55)

**v0.6.7 — PUBLIÉE sur `main`.**

- **Code concret :** nouveau module indépendant `hue_solar.py` calculant approximativement lever/coucher astronomiques hors ligne ; `tests/test_solar.py` vérifie saisons, passage à l'heure d'été et cas polaires. Aucun branchement sur le moteur Hue, les profils, les données locales ou les lampes.
- **Tests :** 3 tests unitaires exécutés localement avec succès après correction d'un problème de passage de date UTC. CI de PR #5 [41983753042](https://github.com/fchautems/Hue/actions/runs/41983753042) terminée avec succès ; fusion squash effectuée sur `main` au [commit fcc336d](https://github.com/fchautems/Hue/commit/fcc336df27bf774605e3c75843b0ef6c0f1b4b12). CI post-fusion [41983798530](https://github.com/fchautems/Hue/actions/runs/41983798530) **terminée avec succès**.
- **PR :** [#5](https://github.com/fchautems/Hue/pull/5) ; [branche de travail](https://github.com/fchautems/Hue/tree/feature/v067-solar-calculation). CI précédente sur main : [41969707759](https://github.com/fchautems/Hue/actions/runs/41969707759), réussite pour v0.6.6.
- **Limites :** précision astronomique approximative et cas extrêmes à approfondir. Aucune GitHub Release dédiée ni déploiement Raspberry.
- **Plan précis à 12 h :** commencer par `hue_solar.py` et `tests/test_solar.py` : renforcer les tests de dates locales, passage à l'heure d'hiver, précision face à une référence connue et limites polaires. La PR #5 étant déjà fusionnée avec CI verte, préparer une petite PR de robustesse solaire et la fusionner uniquement après CI réussie ; préserver strictement les réglages et le pilotage actuel.

## 5 novembre 2026 — correction après le cycle de 04 h (intervention demandée par l'utilisateur)

**Version : v0.6.6 — PUBLIÉE sur `main` par intervention immédiate après le cycle.**

- **Code livré :** cibles tactiles de 48 px pour la copie de profils, libellé plus lisible et focus clavier visible. Aucun changement de commande des lampes.
- **Tests :** GitHub Actions de la PR #4 terminée avec succès, comprenant tests Python et Node d'accessibilité : [exécution 41958392901](https://github.com/fchautems/Hue/actions/runs/41958392901). Contrôle CI de `main` déclenché après fusion : [exécution 41969707759](https://github.com/fchautems/Hue/actions/runs/41969707759) (**terminée avec succès**).
- **Publication :** [commit v0.6.6](https://github.com/fchautems/Hue/commit/cfd777040c2c416cc62311e656b2b638a00bd019) et [PR #4](https://github.com/fchautems/Hue/pull/4).
- **Blocage restant :** le Raspberry et les lampes réelles n'ont pas été vérifiés.
- **Prochaine session à 08 h :** lire le plan de projet, vérifier la CI de `main` et commencer un calcul local du lever/coucher du soleil isolé dans `hue_solar.py`, avec tests des saisons et du changement d'heure Europe/Zurich ; sans modifier le comportement des lampes.
- **Correction de procédure :** la tâche doit désormais consulter la CI jusqu'au résultat final avant de conclure et écrire **chaque compte rendu dans ce fichier**, même en l'absence de version, puis fournir son lien.

## 5 novembre 2026 — cycle de 04 h (Europe/Zurich)

**v0.6.5 — PUBLIÉE ; v0.6.6 — NON PUBLIÉE pendant le cycle.**

- **Code livré :** correctif de la copie de courbe empêchant l'écrasement d'un mauvais profil si la lampe source change en cours de chargement.
- **Publication :** [commit v0.6.5](https://github.com/fchautems/Hue/commit/5addabfd44c561bff9f1f1cfea4c9a2ae3436b8f).
- **Code préparé pour la v0.6.6 :** boutons de copie et sélecteur agrandis à 48 px, focus au clavier et nouveaux tests, dans la PR #4.
- **Tests :** ceux de v0.6.5 réussis ; la tâche s'est terminée avant le résultat final de la CI v0.6.6. [CI v0.6.6](https://github.com/fchautems/Hue/actions/runs/41958392901) réussie peu après la fin du cycle.
- **Blocage de publication :** la tâche a arrêté son exécution pendant que la CI de la PR #4 était encore en cours ; publication effectuée ultérieurement à la demande de l'utilisateur.
- **Plan initial pour 08 h :** valider/fusionner la v0.6.6, puis développer le calcul solaire local, avec tests de changement d'heure.

## 5 novembre 2026 — cycle de 00 h (Europe/Zurich)

**v0.6.5 — NON PUBLIÉE durant ce cycle.**

- **Code préparé :** vérification de la lampe source pendant la lecture asynchrone d'une courbe et test de non-régression ; [PR #3](https://github.com/fchautems/Hue/pull/3).
- **Tests :** test ciblé ajouté ; validation CI complète alors en attente. [CI de PR](https://github.com/fchautems/Hue/actions/runs/41930200673) finalement réussie.
- **Blocage :** attente du verdict GitHub Actions ; pas de fusion pendant le cycle.
- **Plan pour 04 h :** fusionner la PR après tests concluants ; puis améliorer l'ergonomie de copie des profils en CSS et ajouter des tests de taille tactile.

---

Les prochaines entrées devront être **ajoutées ici en tête** à chaque exécution, qu'une release soit disponible ou non.
