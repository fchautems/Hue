# Hue Lab — interface locale Python + HTML (v0.1)

Cette version **n'écrase pas `hue.py`**, ton prototype CLI existant.

## Installation sur le PC (Windows)

1. Extraire **le contenu** de l'archive dans `F:\_Projets\Hue`. Conserver tes fichiers existants `hue.py` et `.hue_config.json`.
2. Depuis ce répertoire :

   ```powershell
   python -m pip install -r requirements.txt
   python hue_web.py
   ```

3. Ouvrir **http://127.0.0.1:8765** dans le navigateur.

Ou double-cliquer sur `demarrer_hue.bat` après l'installation des dépendances.

Le pont déjà associé est utilisé via `F:\_Projets\Hue\.hue_config.json`, créé par `python hue.py connect`. **Ne partage jamais ce fichier.**

## Possibilités

- Dashboard des lampes : état, Zigbee connecté/déconnecté si rapporté, marche/arrêt, luminosité.
- Profils de luminosité propres à chaque ampoule, avec interpolation `smoothstep` cyclique (sans saut à minuit).
- Horloge analogique 24 h / 2 aiguilles (heure en 24 h, minute en 60 min), défilement accéléré sur 30, 60, 120, 300 ou 600 secondes par jour, pause et déplacement manuel de l'heure.
- Simulation **visuelle par défaut** ; activer explicitement « Appliquer aux vraies ampoules » pour commander les ampoules.
- Automatisation heure réelle **désactivée au démarrage**, réactivable dans Tableau de bord.
- Diagnostics : capacités déclarées (`dimming`, `dynamics`, `powerup`, couleur), fabricant / modèle, état Zigbee, preset de démarrage et export JSON sans clé API.
- Dans Diagnostics : « Armer test secteur » avant de couper puis remettre le courant. Mesure la durée entre **deux observations Zigbee**, pas le délai exact de la première lumière.
- Journaux rotatifs `logs/hue.log` : transitions d'état, connexions, commandes, erreurs, modifications du démarrage.
- Tester des presets de démarrage `powerup` par ampoule quand l'API signale la fonction.

## Test conseillé

1. Tableau de bord : vérifier les 3 noms et les états ; commander brièvement une ampoule.
2. Courbes & simulation : cocher **Activer la simulation**, puis déplacer l'horloge. Vérifier la cible calculée (sans action sur la lumière).
3. Cocher **Appliquer aux vraies ampoules** pour tester la courbe avec l'ampoule réellement allumée.
4. Diagnostics : noter modèle, `powerup`, `dynamics`, Zigbee. Lancer le journal.
5. Faire un test **interrupteur mural** : couper, remettre le courant, vérifier l'heure de la reconnexion dans `logs/hue.log` et observer à l'œil la première lumière. Exporter le diagnostic pour examen.

## Limites et sécurité

- Un interrupteur mural coupant le secteur empêche le serveur de communiquer avec l'ampoule éteinte. Le réglage de démarrage `powerup` est une configuration stockée dans l'ampoule : **elle ne peut pas connaître l'heure du PC hors tension**. Une correction peut être envoyée après reconnexion, mais une luminosité immédiatement parfaite n'est pas garantie.
- `powerup` personnalisé fixe une luminosité de départ **statique**, indépendante de l'heure. Les presets disponibles varient selon les modèles / firmwares.
- La connectivité Zigbee déclarée par le pont n'est pas une mesure électrique de l'interrupteur. L'observation peut être retardée ; un événement "ON" ne prouve pas un retour secteur.
- Les transitions sont adoucies via l'API Hue `dynamics.duration` lorsque l'ampoule l'annonce, mais le matériel peut avoir ses limites, surtout en simulation à forte vitesse.
- La commande n'allume pas automatiquement une ampoule éteinte par logiciel ; elle n'adapte que les ampoules indiquées allumées.
- HTTPS local du pont avec validation du certificat désactivée pour ce POC (comme l'ancien `hue.py`). Le serveur Web n'écoute que sur `127.0.0.1` (pas accessible à distance sans changer volontairement `--host`).
- La clé API demeure en local dans `.hue_config.json`, volontairement exclu du ZIP et des rapports ; ne pas publier le dossier `logs` sans le relire.
- Ce prototype ne fait **aucune écriture `powerup` automatique** pour éviter des écritures non maîtrisées dans la mémoire de l'ampoule. Seule une action explicite dans Diagnostics modifie le preset.
- Quand le programme est fermé, aucune automatisation PC ne tourne. Ne pas exécuter plusieurs instances du serveur en parallèle.

## Tests hors réseau

```powershell
python -m unittest discover -s tests -v
```

## Fichiers importants

- `hue_web.py` : serveur FastAPI, commandes API Hue v2, diagnostics, journal et superviseur.
- `hue_core.py` : courbes horaires, interpolation et horloge accélérée.
- `templates/index.html`, `static/*` : interface HTML/CSS/JS.
- `hue_settings.json` : courbes enregistrées (créé lors du premier enregistrement).
- `logs/hue.log` : journal tournant.
- `PROJECT_STATE.md` : statut de la v0.1, contrôles et prochaine étape.
