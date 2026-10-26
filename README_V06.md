# Hue Lab v0.6 — Couleurs RGB et horaires intégrés

## Ce qui change

L'onglet **Couleurs RGB** et le bouton **Couleurs →** sur chaque carte RGB permettent de configurer indépendamment chacune des lampes prises en charge par le pont Philips Hue v2.

- **Manuel** : roue de couleur tactile, saturation, luminosité, six couleurs rapides. Les modifications sont prévisualisées seulement dans le navigateur. Le bouton « Appliquer et enregistrer » applique la couleur au pont si l'ampoule est allumée ; une ampoule éteinte reste éteinte et conserve sa couleur pour son prochain allumage via Hue Lab.
- **Auto** : couleurs distinctes Matin, Journée, Soir, Nuit et transitions douces, synchronisées avec la courbe simple v0.5.2. La luminosité garde la forme `smootherstep` à montée monotone / plateau / descente monotone. Le panneau **Horaires de la courbe** dépliable réunit les quatre heures (début du réveil, fin de montée, début du soir, heure du coucher) et luminosités min/max.
- **Préréglages** : Chaud, Neutre, Ambre, Rouge, Bleu, Violet ; modifiables à la roue.
- **Validation explicite** : aucun appel Hue ou API d'enregistrement pendant qu'on manipule la roue, les couleurs, les curseurs ou les horaires. Boutons « Annuler » et « Enregistrer et activer Auto ».
- **Transitions** : interpolation HSV le long de l'arc le plus court, avec adoucissement `smootherstep`. Les quatre couleurs sont des jalons : milieu de la montée matinale, journée stable, milieu de la descente, nuit stable. Le moteur convertit les couleurs en xy CIE compatibles avec l'API Hue v2, écrêtées selon le gamut déclaré par l'ampoule.
- **Compatibilité** : seules les ampoules annonçant `color` et `dimming` sont pilotées en RGB ; celles ne prenant pas en charge les couleurs continuent à fonctionner normalement.

**Important :** en choisissant **Auto** dans l'éditeur RGB puis en enregistrant, on active aussi le **profil Simple** pour cette lampe. Les éventuels points personnalisés restent conservés et peuvent être réactivés dans « Courbes horaires ». Les anciens profils et réglages ne sont jamais réinitialisés automatiquement. Les couleurs ne sont pas encore liées aux points du mode Personnalisé ; cela pourra venir dans une prochaine version.

## Sécurité et comportement physique

- Le moteur ne rallume **jamais** automatiquement une lampe éteinte en mode Auto.
- À la remise de courant par l'interrupteur mural, l'état initial dépend de la préférence `powerup` mémorisée dans l'ampoule ; le serveur ne peut corriger couleur/luminosité qu'après reconnexion Zigbee. Aucune promesse de couleur immédiate avant connexion.
- En mode Manuel, l'éditeur ne modifie pas les autres lampes. Si l'ampoule est éteinte, le choix de couleur n'allume pas la lampe.
- La transition Hue dépend de la capacité `dynamics` déclarée par le modèle. En Auto, le calcul de luminosité reste inchangé si la couleur automatique n'a jamais été explicitement activée pour cette lampe.
- Paramètres locaux `hue_settings.json` : ajout de `rgb_profiles`, `rgb_manual`, `rgb_auto_enabled`. Le système de mise à jour avec sauvegarde garde ses protections existantes.

## Installation

Dans Hue Lab : **Mises à jour → Vérifier GitHub → Installer et redémarrer**. Les fichiers de configuration (`hue_settings.json`, `.hue_config.json`) restent sur le Raspberry. Le navigateur peut nécessiter une actualisation pour charger `v06.js` et `v06.css`.

## Tests

Tests mathématiques de la roue et de la conversion CIE xy (`tests/test_v06_rgb_math.py`) et tests API/contrôleur (`tests/test_v06_rgb_integration.py`). Essais Chromium en largeur 320 px, 390 px et 1320 px : roue, presets, changement de mode, horaires dépliables, enregistrement, navigation sans dépassement horizontal, et aucune erreur JS avec un pont simulé.

**Non testé physiquement :** la teinte exacte et le temps réel de transition dépendent des modèles Hue et doivent être vérifiés sur les ampoules réelles après mise à jour du Raspberry.
