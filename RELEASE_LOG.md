# Hue Lab — journal des cycles et des publications

Ce fichier est le **point de consultation permanent des comptes rendus**. Il doit être enrichi **après chaque exécution automatisée, toutes les quatre heures**, même si la version n'est pas publiée. Les informations les plus récentes figurent en premier.

**Attention :** une version indiquée « publiée » signifie **fusionnée dans la branche `main` sur GitHub**, pas installée ni vérifiée sur le Raspberry. Les notifications mobiles dépendent des réglages ChatGPT ; ce fichier permet de retrouver les résultats indépendamment de leur livraison.

## 5 novembre 2026 — cycle de 08 h (Europe/Zurich ; démarré à 07 h 55)

**v0.6.7 — PUBLIÉE sur `main`.**

- **Code concret :** nouveau module indépendant `hue_solar.py` calculant approximativement lever/coucher astronomiques hors ligne ; `tests/test_solar.py` vérifie saisons, passage à l'heure d'été et cas polaires. Aucun branchement sur le moteur Hue, les profils, les données locales ou les lampes.
- **Tests :** 3 tests unitaires exécutés localement avec succès après correction d'un problème de passage de date UTC. CI de PR #5 [41983753042](https://github.com/fchautems/Hue/actions/runs/41983753042) terminée avec succès ; fusion squash effectuée sur `main` au [commit fcc336d](https://github.com/fchautems/Hue/commit/fcc336df27bf774605e3c75843b0ef6c0f1b4b12). CI post-fusion [41983798530](https://github.com/fchautems/Hue/actions/runs/41983798530) **terminée avec succès**.
- **PR :** [#5](https://github.com/fchautems/Hue/pull/5) ; [branche de travail](https://github.com/fchautems/Hue/tree/feature/v067-solar-calculation). Dernière CI vérifiée sur main : [41969707759](https://github.com/fchautems/Hue/actions/runs/41969707759), réussite pour v0.6.6.
- **Limites :** précision astronomique approximative et cas extrêmes à approfondir. Aucune GitHub Release dédiée ni déploiement Raspberry.
- **Plan précis à 12 h :** commencer par `hue_solar.py` et `tests/test_solar.py` : renforcer les tests de dates locales, passage à l'heure d'hiver, précision face à une référence connue et limites polaires. Vérifier/fusionner PR #5 uniquement si CI réussie et calcul suffisamment fiable ; préserver strictement les réglages et le pilotage actuel.

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
