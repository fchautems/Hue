# Hue Lab v0.5.1 — Éditeur de courbe adapté au mobile

Cette version porte **uniquement** sur l'ergonomie : elle n'ajoute ni commande de lampe, ni automatisme, ni changement du moteur Hue v0.5.

## Fonctionnement

- La page « Courbes horaires » présente la courbe sur 24 heures, des **pastilles horaires tactiles**, puis les commandes du point sélectionné.
- Tapoter un point dans les pastilles ou sur le graphique ; glisser un point sur le graphique pour changer heure et luminosité (l'heure est arrondie à 5 minutes pendant le déplacement).
- Utiliser les boutons **± 5 minutes** ou saisir l'heure **HH:MM au format 24 h**, avec une précision d'une minute.
- Ajuster la luminosité au curseur, par saisie numérique ou avec les boutons ± 5 %. Les bornes sont de 1 à 100 %.
- Jusqu'à 24 points différents, au moins 2 points, aucun doublon d'heure.
- Sur mobile, l'horloge analogique et la simulation sont derrière le bouton « Afficher la simulation et l'horloge » ; elles restent accessibles.
- **Enregistrer** et **Annuler** sont clairement visibles. Une alerte prévient de la perte des modifications lorsqu'on change de lampe ou d'onglet.
- Les ampoules ne sont jamais commandées pendant la manipulation de la courbe : l'API existante `PUT /api/profile/{uid}` n'est appelée qu'après une validation explicite « Enregistrer ».
- Les boutons Manuel/Auto, la logique des ampoules, les courbes stockées et le système autonome de mises à jour sont inchangés.

## Mise à jour

Depuis Hue Lab → **Mises à jour** → **Vérifier GitHub** → **Installer et redémarrer**. Un rechargement peut être nécessaire afin que le navigateur récupère `v051.js` et `v051.css`.

Les fichiers `.hue_config.json` et `hue_settings.json` ne sont ni présents dans le commit, ni réinitialisés. Le mécanisme v0.4 de sauvegarde et retour arrière reste intact.

## Vérifications

- Syntaxe JavaScript : `node --check static/v051.js`.
- Tests de présence et d'intégration (stdlib) : `python -m unittest tests/test_v051_frontend.py` ou découverte complète.
- Tests interactifs Chromium sur écran mobile 390 px et ordinateur 1320 px : sélection, modification, rejet d'heures en double, ajout, annulation, sauvegarde, navigation non enregistrée, déplacement tactile simulé sur le graphique, absence de défilement horizontal du document. Les appels réseau étaient simulés : **aucune vraie ampoule n'a été pilotée pendant les tests**.

Les fichiers de configuration restent privés. Ne pas exposer le port 8765 directement à Internet.
