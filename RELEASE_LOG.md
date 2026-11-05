# Hue Lab — journal des cycles et des publications

## 6 novembre 2026 — cycle de 00 h (Europe/Zurich)

**v0.6.11 — PUBLIÉE sur `main` (commit 81bc94f).**

- **Code concret :** 8 scénarios de dates civiles 31 décembre / 1er janvier (2025–2027) à Kiritimati et Pago Pago dans `tests/test_solar_dateline.py`, avec vérification du jour local et de l'ordre lever/coucher. Aucun changement de pilotage Hue, données locales ni Raspberry.
- **Tests :** GitHub Actions PR #9 run [42126332719](https://github.com/fchautems/Hue/actions/runs/42126332719) **completed/success**. CI sur la tête finale de PR [42126379228](https://github.com/fchautems/Hue/actions/runs/42126379228) et post-fusion [42126397135](https://github.com/fchautems/Hue/actions/runs/42126397135) déclenchées, verdict à compléter après leur terminaison. Aucun test matériel.
- **Publication :** [PR #9](https://github.com/fchautems/Hue/pull/9) fusionnée, [commit main 81bc94f](https://github.com/fchautems/Hue/commit/81bc94f52b83079a6d5a92f6c505c3a2238bb84d). Pas de GitHub Release dédiée.
- **Blocage :** aucun pour la fusion initiale ; vérification CI post-fusion en cours au moment de la rédaction.
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
