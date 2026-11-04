# Hue Lab v0.6.3 — Copie de profil complet

Dans **Horloge & lumières**, sélectionne la lampe de destination, puis la lampe source.

- **Copier vers cette lampe** reprend uniquement la courbe de luminosité active (fonction v0.6.2).
- **Copier le profil complet** reprend les courbes Simple et Personnalisée enregistrées, le type actif, les couleurs automatiques et leur activation uniquement si la cible est compatible RGB.
- Le mode Manuel/Auto, l'état allumé/éteint, la luminosité manuelle et les règles Vacances ne changent pas.
- Une confirmation explicite est nécessaire. Si la lampe cible est déjà en Auto, le nouveau profil peut avoir un effet sur sa lumière dès le prochain cycle.
- Les changements non enregistrés empêchent la copie. Aucune commande directe au pont n'est émise par l'action de copie ; les réglages locaux sont enregistrés.

## Contrôles
- Tests Python de copie et de non-régression via GitHub Actions (inclut les tests de la PR de préparation).
- Tests Node des deux boutons et vérification syntaxique JavaScript via GitHub Actions.
- Les vraies lampes Hue et le Raspberry ne sont pas accessibles depuis l'environnement de développement.

## Essai sur Raspberry
Installer la nouvelle version depuis **Mises à jour**. Tester d'abord une destination en mode Manuel, copier un profil depuis une lampe RGB, vérifier que courbe et couleurs sont reprises sans changer l'état ON/OFF. Tester ensuite une destination en Auto en observant les transitions.
