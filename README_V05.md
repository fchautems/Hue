# Hue Lab v0.5 — Pilotage indépendant par lampe

## Principe

Chaque lampe du pont Hue possède maintenant son propre mode **Manuel** ou **Auto**, sélectionnable directement sur sa carte dans l'interface. Le choix n'affecte jamais les autres lampes.

- **Manuel** : commandes ON/OFF et luminosité indépendantes de la courbe. La dernière luminosité demandée et l'état ON/OFF sont enregistrés sur le Raspberry. Lors d'un redémarrage de Hue Lab, l'application restaure une seule fois la préférence de la lampe si elle est connectée. Elle ne force pas le rallumage après une coupure de l'interrupteur mural.
- **Auto** : la courbe de luminosité individuelle est appliquée seulement quand l'ampoule est allumée et connectée. Le passage de Manuel à Auto est animé par une transition de 2 secondes lorsque l'ampoule prend en charge `dynamics.duration`; sinon la transition dépend du firmware Hue.
- **Horloge** : le choix commun « Heure réelle » / « Simulation accélérée » ne concerne **que** les lampes en Auto. La simulation accélérée est désactivée au redémarrage.
- **Courbes** : elles restent éditables pour chaque ampoule indépendamment du mode choisi. Un raccourci « Courbe » figure sur chaque carte.
- **Réglages privés** : les modes individuels et états manuels sont sauvegardés dans `hue_settings.json` avec les courbes déjà présentes. Ce fichier et la clé Hue ne sont jamais envoyés sur GitHub.

## Mise à jour depuis la v0.4.1

Depuis le téléphone connecté au même réseau Wi-Fi, ouvrir l'interface Hue Lab (par défaut `http://10.0.0.12:8765/`), onglet **Mises à jour**, puis **Vérifier GitHub** et **Installer et redémarrer**. Aucun code ni ordinateur n'est nécessaire. La sauvegarde et le mécanisme de restauration v0.4 restent opérationnels.

**Migration des anciens paramètres :** si l'ancien mode global mémorisé était « Temps réel », toutes les lampes démarrent en Auto ; si c'était « Manuel » (ou si la simulation accélérée s'était arrêtée au redémarrage), elles démarrent en Manuel. Le premier chargement depuis le pont mémorise ces modes dans les préférences individuelles. **Aucune courbe existante n'est réinitialisée.**

## Vérifications réalisées

- Tests Python en environnement isolé : **65 tests**, incluant les 17 nouveaux tests v0.5 (3 lampes, indépendance, modes, transitions, préférences, migrations v0.4 et routes HTTP).
- Contrôles de syntaxe : Python et JavaScript.
- Test de présentation dans Chromium sur écrans téléphone et ordinateur, avec trois ampoules simulées, sélection Manuel/Auto et changement d'horloge, sans erreur JavaScript.
- **Non vérifié :** comportement physique des ampoules après installation sur le Raspberry ; la souplesse de la transition dépend aussi du modèle d'ampoule.

La v0.6 est réservée aux couleurs et températures de blanc. Aucune commande de couleur n'est ajoutée en v0.5.
