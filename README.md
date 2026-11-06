# Hue Lab — Interface Web Philips Hue (v0.8.0)

Application locale Python + HTML permettant de piloter des ampoules Hue, simuler 24 h en accéléré, adapter leur luminosité et diagnostiquer leur comportement après une coupure de courant.

## Navigation actuelle

- **Lampes & vacances** : marche/arrêt, luminosité, Manuel/Auto par lampe, raccourcis courbe/couleur, Vacances avec planning et test 60 s.
- **Profils & simulation** : lampe choisie en premier ; horloge et courbe rapprochées ; source réel/accéléré unique ; commandes repliables. Couleurs et profil solaire restent accessibles dans deux sections repliables. Les copies « courbe seule » et « profil complet » sont regroupées sous le sélecteur de lampe.
- **Historique** : allumages/extinctions et observations Zigbee, pagination conservée.
- **Paramètres** : Pont Hue, Avancé (démarrage après coupure, capacités, latences, tests secteur, export et logs), Mises à jour.
- **Mises à jour** : raccourci permanent avec badge si une nouvelle version est disponible ; statut local relu chaque minute, sans installation automatique.

Les profils, couleurs, modes par lampe, données Vacances et clés locales sont conservés sans migration. La découverte utilise le service Hue puis une recherche SSDP locale bornée si nécessaire. Le multicast peut être filtré : l’IP manuelle reste disponible et n’est jamais écrasée par une recherche. Les données enregistrées sont prioritaires au démarrage.

Le test Vacances de 60 s et la simulation des profils sont distincts : le premier teste les allumages de présence puis reprend le programme ; la seconde accélère les courbes des lampes en Auto.

Les sections v0.3–v0.7 ci-dessous décrivent l’historique ; les emplacements actuels sont ceux de cette section.

## Installation Windows — tout depuis l'interface

1. Récupérer la dernière version du dépôt dans `F:\_Projets\Hue` et conserver les fichiers existants du dossier, notamment `hue.py` (prototype CLI). Si le dossier est déjà un clone Git, `git pull` récupère les mises à jour du code ; cette commande **n'est pas nécessaire pour l'appairage**.
2. Double-cliquer sur `demarrer_hue.bat` : les dépendances manquantes sont installées automatiquement, puis le serveur est lancé.
3. Ouvrir `http://127.0.0.1:8765` dans le navigateur. Au premier lancement, **Paramètres → Pont Hue** s'affiche automatiquement :
   - Cliquer sur **Rechercher le pont**, ou saisir son IP locale (par exemple `10.0.0.12`). Aucune adresse fictive n’est proposée. La recherche conserve toute IP saisie ; un choix ne s’affiche que si plusieurs ponts sont détectés.
   - Cliquer sur **Démarrer l'association** et appuyer sur le gros bouton du pont Hue.
   - Le programme retente automatiquement pendant 45 secondes, vérifie la clé, crée la configuration locale et affiche les ampoules.

**Aucune édition de fichier ni appel à `python hue.py connect` n'est nécessaire.** L'association physique au pont reste obligatoire une seule fois pour autoriser l'application.

## Configuration et sécurité

- `hue_config.example.json` est **versionné sur GitHub**. Il contient une adresse vide, sans clé secrète. Une installation existante conserve son adresse et sa clé. Il sert de modèle au premier démarrage.
- `.hue_config.json` est **créé automatiquement sur le PC** et contient ensuite la clé d'application fournie par le pont. **Il est exclu de GitHub** via `.gitignore` pour ne pas rendre publiques les commandes de tes lampes.
- Quand une clé est absente, vide ou refusée, ouvrir **Paramètres → Pont Hue** et refaire l'association directement dans la page.
- `hue_settings.json` (courbes personnalisées) et `logs/hue.log` (journal) restent aussi locaux.
- Le serveur écoute par défaut uniquement sur `127.0.0.1` et refuse les adresses externes pour l'association. Les requêtes vers le pont utilisent son HTTPS local sans validation du certificat pour ce prototype.

## Fonctions

- Tableau de bord : on/off, luminosité et connexion Zigbee déclarée par le pont.
- Courbes individuelles avec interpolation douce et continuité à minuit.
- Manuel/Auto par lampe. Dans **Profils & simulation**, une seule référence horaire réelle/accélérée, horloge 24 h, vitesse, pause et curseur. La simulation agit sur les vraies lampes en Auto.
- Temps réel : suivi continu de la courbe locale, sans rallumer les ampoules volontairement éteintes par logiciel.
- Démarrage sur valeur fixe 10 % proposé pour chaque ampoule compatible via `powerup.custom` : écriture uniquement sur clic, puis relecture du réglage.
- Reconnexion : SSE Hue v2 et secours par sondage 2 s, transition adaptative 500–2 000 ms ; animation quotidienne par `dynamics.duration` si disponible.
- Diagnostics `dimming`, `dynamics`, `powerup`, statut SSE, délai observé de correction, modèle, Zigbee, logs et export JSON sans secret.
- Tests de remise sous tension : mesures du temps entre les observations de connectivité Zigbee.

## Limitation physique importante

Un interrupteur classique coupe totalement l'alimentation de l'ampoule. Elle ne peut pas interroger le PC avant de se reconnecter. Le comportement initial dépend de son paramètre `powerup` embarqué. L'application peut corriger la luminosité après reconnexion, mais ne peut pas garantir qu'elle sera exacte dès la première milliseconde.

## Dépannage

- Si aucun pont n'est détecté, saisir une adresse locale valide (par exemple `10.0.0.12`) sur la page de connexion.
- Si le pont refuse l'association, appuyer sur son bouton pendant la phase d'attente, puis relancer si nécessaire.
- Le lanceur Windows indique les erreurs d'installation éventuelles et conserve la fenêtre ouverte en cas d'échec.
- Les logs sont dans `logs/hue.log` ; ne pas publier les logs sans les relire.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Les tests de l'appairage sont effectués avec un faux pont. L'appairage sur le matériel réel reste à valider.

## Fichiers

- `hue_web.py` : serveur Web FastAPI, appairage, supervision, diagnostics.
- `hue_core.py` : logique de courbe et de temps virtuel.
- `templates/index.html`, `static/app.js`, `static/style.css` : interface Web.
- `hue_config.example.json` : modèle de configuration versionné sans secret.
- `.hue_config.json` : configuration privée créée automatiquement et ignorée par Git.
- `tests/` : tests unitaires et des routes HTTP.
- `PROJECT_STATE.md` : état vérifié du projet et prochaines actions.

## Hue Lab v0.3 — Utilisation

1. Depuis le clone Git, effectuer `git pull`, puis relancer `demarrer_hue.bat`. La configuration locale de v0.2 est préservée.
2. Choisir le mode depuis le sélecteur en haut de page : **Manuel** (aucune courbe appliquée), **Temps réel** (courbes sur l'heure du PC), **Accéléré** (courbes sur l'horloge virtuelle, commande PHYSIQUE des ampoules).
3. Dans **Diagnostics**, pour une ampoule annonçant `powerup`, cliquer sur **Démarrage / powerup**, choisir **Luminosité fixe personnalisée**, 10 %, puis **Appliquer au matériel**. Lire le résultat de la vérification par relecture et tester une coupure avec l'interrupteur.
4. En Temps réel, à la reconnexion, la consigne de la courbe est appliquée par une transition courte et douce. La première lumière dépend de la mémoire et du firmware de l'ampoule.
5. Les diagnostics donnent le statut des événements SSE et la latence entre observation et envoi de commande ; ils ne mesurent pas le délai optique réel.

Manuel et Temps réel sont mémorisés. Accéléré est réinitialisé en Manuel au redémarrage pour éviter un pilotage intempestif. Le double allumage à 100 % est reporté à une éventuelle v0.4.

**Tests :** 27 tests Python hors réseau sur moteur v0.3 adapté et routes API, et `node --check` sur le JavaScript ; intégration textuelle avec la source v0.2 vérifiée. Pas de test avec tes trois ampoules ni de test complet du projet sur Windows dans cet environnement.

## Raspberry Pi — mises à jour autonomes (v0.4)

Voir [README_V04.md](README_V04.md) pour la migration initiale via Termux, le bouton de mise à jour GitHub, les sauvegardes et le retour arrière.

## Hue Lab v0.5 — Manuel / Auto par lampe

Chaque lampe possède son propre mode **Manuel** ou **Auto**. Le choix de l'heure réelle ou de la simulation accélérée ne s'applique qu'aux lampes en Auto. Les courbes existantes sont conservées à l'installation et les réglages individuels restent locaux.

Consulte [README_V05.md](README_V05.md) pour les étapes de mise à jour depuis l'interface du Raspberry et les limites des transitions selon les ampoules.

## v0.5.1 — Ergonomie mobile des courbes

L’éditeur présente une courbe interactive et des pastilles horaires accessibles au doigt, avec des réglages précis HH:MM / luminosité, l’ajout et la suppression de points, ainsi qu’une sauvegarde et une annulation explicites. La simulation est repliable sur téléphone. Aucune modification du moteur Hue ou des profils enregistrés n’est nécessaire. Détails dans [README_V051.md](README_V051.md).

## v0.5.2 — Courbe simple progressive

L’onglet **Courbes horaires** permet de choisir entre la courbe personnalisée à points et une **courbe simple** : début/fin de montée, début/fin de descente, luminosités minimale et maximale. Les rampes sont monotones, arrondies et continues, avec un plateau de jour et un minimum nocturne. La courbe personnalisée existante n’est jamais écrasée. [Détails](README_V052.md).

## v0.6 — Couleurs RGB et profils horaires

Depuis **Couleurs RGB** ou le raccourci sur chaque carte, on choisit une lampe, sa couleur et son mode : **Manuel** (roue + saturation + luminosité) ou **Auto** (4 couleurs Matin/Journée/Soir/Nuit, transitions continues et horaires repliables). Les six couleurs rapides et la prévisualisation n'agissent jamais sur le pont avant l'enregistrement. Le mode Auto de cet écran active la courbe **Simple** sans effacer les anciennes courbes personnalisées. [Guide et limites](README_V06.md).

## v0.6.1 — Interface unifiée avec horloge

Les anciens onglets **Courbes horaires** et **Couleurs RGB** ne font plus qu'un : **Horloge & lumières**. L'horloge 24 h est visible sur téléphone ; la roue RGB est en accès direct ; l'éditeur de courbe historique est replié sous « Éditeur de courbe avancé ». Un seul sélecteur choisit l'ampoule pour les deux éditeurs. Aucun changement du pilotage ni des paramètres privés. [Documentation](README_V061.md).

## Aperçu solaire (v0.7.0)

Dans **Horloge & lumières**, le panneau « La lumière au fil des saisons » affiche le lever et le coucher du soleil, la durée du jour et une frise. Choisir Le Muids/Arzier, Nyon, Lausanne, ou saisir les coordonnées et un fuseau IANA dans « Autre lieu ». La date est libre ; « Aujourd’hui » utilise le fuseau choisi.

Les repères « Mon réveil » et « Mon coucher » comparent ton rythme aux heures solaires. Les préférences d’aperçu sont mémorisées dans ce navigateur. Cet aperçu fonctionne sans Internet ni pont associé, ne sauvegarde aucun profil de lampe et n’envoie aucune commande Hue. Les horaires sont approximatifs (sans relief/météo) ; aux latitudes polaires, un événement peut être absent.

## Brouillon solaire complet (v0.7.1)

Dans le panneau solaire, règle ton réveil/coucher et les luminosités minimale/maximale, puis choisis **Préparer un profil pour cette date**. La courbe et le curseur montrent luminosité et couleurs au cours de la journée. Le rythme personnel reste prioritaire : le soleil module la fin de montée et le début de descente dans des limites explicites. Le générateur accepte une journée sans passage de minuit d'au moins trois heures.

**Appliquer à la lampe sélectionnée** remplace le profil actif après confirmation. Le mode Manuel/Auto est conservé ; une lampe déjà en Auto peut appliquer le nouveau profil immédiatement. Les lampes sans RGB reçoivent la luminosité seule. ON/OFF, Vacances et courbes personnalisées sauvegardées restent préservés.

Le résultat est un profil fixe pour la date choisie, sans recalcul quotidien ni météo. Le brouillon n'est pas enregistré tant que tu ne l'appliques pas.

## Profil Soleil — v0.9.0

Dans **Profils & simulation**, choisis la lampe, puis **Soleil** dans le choix de profil. Renseigne ton réveil, ton coucher, les niveaux minimum/maximum et le lieu, puis clique **Enregistrer et activer Soleil**. Ces options sont mémorisées sur le serveur pour cette lampe. En **Auto**, les horaires et les couleurs sont recalculés pour chaque date locale du lieu, au fil des saisons et après un redémarrage. En **Manuel**, le suivi est suspendu ; Vacances reste prioritaire et une lampe OFF n’est pas rallumée.

La **date de l’aperçu** sert seulement à explorer une journée : elle n’est jamais enregistrée dans le profil. La simulation accélérée utilise les horaires solaires d’aujourd’hui. Les heures astronomiques restent approximatives, sans météo ni relief ; si un lever/coucher est absent, le rythme personnel sert de repli. Les transitions restent bornées par le réveil/coucher et durent au moins 30 minutes.

Pour quitter Soleil, enregistre un profil Simple ou active Personnalisée ; les options solaires sont conservées. Les anciens profils solaires fixes ne sont pas convertis automatiquement. La copie du **profil complet** inclut les options solaires et les couleurs ; la copie de **luminosité seule** fige la courbe solaire du jour en profil Simple.


## Rythme Soleil — v0.10.0

Dans le profil Soleil, règle une fois par lampe :
- tes heures de réveil et de coucher ;
- la luminosité de confort et la saturation à atteindre à ces deux heures ;
- une durée commune de transition, avant le réveil et après le coucher ;
- la luminosité nocturne et celle de journée ;
- les trois teintes pleines matin/soir/nuit et le blanc de journée.

Exemple de départ ajustable : réveil 05:15, coucher 22:30, durée 30 minutes,
confort 55 % / saturation 45 %, nuit 10 % / saturation 100 %, journée 85 %.
La montée commence à 04:45 et atteint le confort à 05:15 ; elle rejoint ensuite
le niveau de journée au lever solaire (ajusté si nécessaire pour conserver l’ordre).
La soirée part du coucher solaire et rejoint les niveaux de confort à 22:30.
Le minimum nocturne et la saturation 100 % sont atteints à 23:00.
Les transitions suivent des courbes en S asymétriques : montée avancée, baisse retardée.
Les transitions de nuit peuvent traverser minuit ; elles ne peuvent pas se chevaucher.
Le rythme personnel reste limité à un réveil précédant le coucher dans la même journée.

Le blanc de journée utilise une référence CIE D à 5’000 K par défaut,
réglable entre 4’000 et 6’500 K, convertie en xy et limitée au gamut annoncé par la lampe.
C’est une référence de chromaticité : une ampoule ne reproduit pas le spectre du soleil.
L’aperçu écran est indicatif. Les lampes sans RGB suivent seulement la luminosité.
Référence de calcul : https://colour.readthedocs.io/en/master/generated/colour.temperature.CCT_to_xy_CIE_D.html

L’aperçu date/heure reste sans effet sur les lampes. Les deux courbes affichent
luminosité et saturation ; l’enregistrement conserve le recalcul quotidien,
Manuel/OFF/Vacances prioritaires et les réglages après redémarrage.
Les anciens profils Soleil restent inchangés jusqu’au bouton « Adopter ce rythme Soleil ».
Les profils Simple/Personnalisé restent disponibles ; la copie de luminosité seule
reste fixe et conserve les couleurs de destination.
