# Hue Lab v0.6.1 — Un seul onglet, horloge conservée

Cette mise à jour corrige la redondance entre les anciens onglets **Courbes horaires** et **Couleurs RGB**. Tous les calculs, API et paramètres privés restent ceux de la v0.6.

## Interface unifiée

- Un seul onglet **Horloge & lumières** dans la barre de navigation.
- L'**horloge analogique 24 heures est visible sur mobile** (elle était masquée par défaut dans les anciennes versions).
- Les **commandes de simulation** restent accessibles dans un panneau repliable sous l'horloge ; le sélecteur global d'heure réelle/accélérée est maintenu.
- Un **sélecteur de lampe commun** pilote l'éditeur de courbe et l'éditeur de couleurs ; le sélecteur RGB précédent existe toujours dans le DOM pour compatibilité mais n'est plus affiché.
- La roue RGB, les quatre couleurs Matin/Journée/Soir/Nuit, leur aperçu et les horaires repliables sont affichés directement.
- L'éditeur historique des courbes de luminosité Simple/Personnalisée reste accessible via **Éditeur de courbe avancé**, replié initialement pour éviter les réglages dupliqués à l'écran.
- Les raccourcis « Courbe » et « Couleurs » sur chaque carte continuent d'ouvrir la bonne lampe et la bonne section.
- Les avertissements de modifications non enregistrées restent actifs lorsque tu changes de lampe, quittes la page ou fermes le navigateur.

## Données et sécurité

Aucun changement dans `hue_web.py`, `hue_rgb.py`, les endpoints, `hue_settings.json` ou la configuration du pont. Aucun profil n'est effacé. Aucun clic dans le sélecteur ni déplacement sur la roue ne pilote une lampe avant l'enregistrement.

Les lampes non RGB restent sélectionnables pour éditer la courbe ; la roue indique que RGB est indisponible.

## Installer depuis le Raspberry

Depuis le même réseau : Hue Lab → **Mises à jour** → **Vérifier GitHub** → **Installer et redémarrer**. Le mécanisme de sauvegarde et retour arrière existant est conservé. Le navigateur peut nécessiter un rechargement après la mise à jour.

Tests statiques ajoutés dans `tests/test_v061_navigation.py` (navigation unique, horloge et simulation conservées, structure fusionnée, références JavaScript et protections de navigation). L'intégration avec de vraies lampes devra être vérifiée après installation.
