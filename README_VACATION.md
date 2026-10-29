# Hue Lab — Mode Vacances (2026-10-28)

## Utilisation

Dans **Tableau de bord → Mode Vacances**, sélectionner les ampoules qui doivent
simuler une présence puis choisir **Activer Vacances**. Les prochains événements
(allumage / extinction) s'affichent immédiatement. Le programme fonctionne
localement dans le service Hue Lab sur le Raspberry, sans IA ni cloud, même si
l'interface Web est fermée. Le même bouton permet de désactiver le mode.

**Important :** les interrupteurs muraux des ampoules sélectionnées doivent
rester sous tension, sinon aucun logiciel ne peut les allumer.

## Planification

Le moteur `hue_vacation.py` lit les séquences logiques `light_on` →
`light_off` dans `logs/presence_events.csv`. Il ignore les événements de
connexion Zigbee comme preuve d'une action humaine et les séquences
incomplètes ou anormalement longues. Avec au moins deux sessions de soirée
pour une ampoule, il combine leurs heures médianes aux horaires de référence.
Sinon, il utilise directement un planning de secours matin / soir. La durée et
l'heure sont légèrement décalées de manière reproductible par jour et par
ampoule ; aucune IA n'est requise.

La planification des sept jours à venir, le choix des ampoules, le mode actif
et les priorités manuelles sont conservés dans `hue_settings.json`, qui
reste sur le Raspberry. Le programme se régénère à chaque nouvelle journée
en incorporant l'historique disponible. Au redémarrage du service, il récupère
l'état prévu à l'heure réelle.

## Priorité au voisin — 10 minutes

Quand le pont Hue signale qu'une ampoule sélectionnée passe **de OFF à ON**
sans commande ON du simulateur, ce changement est interprété comme une
commande externe (notamment télécommande Hue ou application Hue).
L'ampoule reste **allumée pendant dix minutes complètes** à partir de
l'observation, même si le programme prévoyait de l'éteindre entre-temps.
Une autre commande externe renouvelle la priorité. À l'expiration, le
simulateur applique à nouveau l'état prévu par son planning.

Une commande externe **OFF** reçoit aussi dix minutes de priorité OFF,
afin de respecter l'extinction volontaire. Ce choix évite qu'une lampe
s'éclaire immédiatement après un ordre manuel d'extinction.

La priorité est individuelle : les autres lampes poursuivent leur scénario.
Elle survit au redémarrage du service. Les commandes envoyées par le
simulateur sont reconnues et ne déclenchent pas de priorité manuelle ni de
nouveaux « exemples d'habitudes » dans l'historique.

**Limites :** l'API v2 ne nous dit pas quelle personne a agi. On détecte
l'effet sur l'ampoule, pas l'identité du voisin. Si la télécommande est
pressée alors qu'une ampoule était déjà ON et que son état logique ne
change pas, cela ne peut pas relancer le minuteur dans cette version.
Les coupures de courant physiques ne sont pas considérées comme des
commandes manuelles ON ; les lampes hors ligne sont ignorées. Le mode
Vacances exige l'horloge **Heure réelle** pour éviter les conflits avec
la simulation accélérée.

## Vérifications

Tests ajoutés dans `tests/test_vacation.py` : planning sans logs, usage des
logs, isolation par lampe, interruption de 10 minutes, reprise après
redémarrage, absence d'apprentissage des commandes du simulateur, API
GET/POST et validations. Des vérifications statiques du JavaScript et de
l'intégration HTML ↔ API ont été effectuées.

Commandes à exécuter avant déploiement :
`python -m unittest discover -s tests -p 'test_vacation.py' -v`
puis `python -m unittest discover -s tests -v`.

**Non vérifié** : tests d'intégration complets sur Raspberry et télécommande
Hue physique. Avant de partir, vérifier une commande avec la télécommande
et observer le maintien ON pendant 10 minutes.

## Test rapide de 60 secondes (2026-10-28)

Une fois **Vacances activé**, appuyer sur **▶ Tester 60 s** dans la carte
Mode Vacances du Tableau de bord. Le test utilise les **vraies ampoules**
sélectionnées et fait défiler un intervalle de **24 heures simulées** en
**environ 60 secondes** ; l'éclairage doit donc se voir réellement.

- Le test choisit un scénario du lendemain (pas l'heure du lancement),
  et démarre 72 minutes simulées avant le premier événement :
  la première commande d'allumage arrive généralement autour de **3 s**.
- Au démarrage, les ampoules sélectionnées sont éteintes pour partir
  d'un logement « vide » ; les autres ampoules ne sont pas affectées.
- Un minimum de deux secondes est laissé aux plages d'allumage courtes
  pour rester visibles dans le test. Le débit des commandes et les temps
  de réponse du pont peuvent allonger légèrement certains enchaînements.
- La progression indique le temps restant, l'heure simulée et le nombre
  d'événements parcourus. Le bouton devient **■ Arrêter le test**.
- Après les 60 secondes, ou sur arrêt manuel, la journée accélérée
  s'interrompt et **le planning Vacances à l'heure réelle reprend**.
  Si le programme réel prévoit une ampoule éteinte, elle pourra
  donc s'éteindre immédiatement à la fin du test.
- Le **mode Vacances doit déjà être actif** ; le test ne l'active ni ne le
  désactive lui-même. Le planning réel, les paramètres et les historiques
  sont conservés ; la simulation accélérée elle-même n'est pas sauvegardée.
  Si le Raspberry redémarre pendant le test, il retrouve normalement
  son programme Vacances réel.
- La détection des priorités du voisin est suspendue durant le test,
  pour éviter qu'une commande artificielle soit prise pour une visite
  réelle. **Le test de la télécommande Hue et des dix minutes de priorité
  reste à faire séparément, en temps réel.**

Les ampoules doivent rester **sous tension électrique** pendant tout le test.
Les tests logiciels avec un faux pont et la validation physique sur le
Raspberry restent à réaliser avant de considérer ce mode comme fiabilisé.

## Historique d'apprentissage et mode Vacances (2026-10-28)

Le fichier `logs/presence_events.csv` mémorise les habitudes observées
**uniquement pendant l'utilisation normale**.

- **Mode Vacances actif** : toutes les écritures dans cet historique sont
  suspendues, pour **toutes les lampes**, y compris les commandes du simulateur,
  les changements via télécommande Hue, et les événements de connexion Zigbee.
  L'analyse du planning continue à exploiter les données récoltées avant
  l'activation, sans les modifier.
- **Test rapide Vacances** : même exclusion ; les retours tardifs du pont Hue
  concernant les lampes testées restent ignorés pendant 45 s après le test.
- **Fin du mode Vacances** : l'enregistrement normal reprend après une marge
  de sécurité de 45 s pour absorber les éventuelles notifications tardives
  du pont. Rien n'est effacé ni ajouté rétroactivement.
- **Simulation générale de l'horloge accélérée** : apprentissage suspendu
  pendant son fonctionnement, puis également 45 s au retour en temps réel.

La **priorité de 10 minutes** d'une télécommande extérieure continue de
fonctionner pendant Vacances : cette priorité se base sur l'état actuel des
ampoules, indépendamment de l'historique d'apprentissage. Elle reste
suspendue pendant le test rapide pour ne pas confondre les actions artificielles
avec celles du voisin.

Le fichier `logs/hue.log` continue, lui, à enregistrer les diagnostics
techniques pendant Vacances et les tests. Le tableau « Historique » présente
toujours les anciennes données, mais ne reçoit aucune nouvelle ligne durant
ces phases. Les actions réellement effectuées pendant ces périodes
d'exclusion ne sont volontairement pas apprises.

Tests de non-régression ajoutés pour l'arrêt global de l'apprentissage, les
événements de télécommande, le redémarrage du service, la reprise différée
de l'historique, les tests rapides et l'horloge accélérée. Leur exécution
sur le Raspberry reste à confirmer.

## Planning graphique par lampe (2026-10-29)

La carte **Mode Vacances** affiche un mini-planning des lumières, en lecture
seule : une barre de **24 heures par lampe**, segments dorés pour les plages
ON et horaires précis au-dessus. Deux flèches permettent de regarder
**aujourd'hui et les six jours suivants**. En l'absence de programmation,
le texte indique simplement d'activer Vacances.

Le serveur fournit le programme existant par
`GET /api/vacation/schedule` (date initiale, liste de lampes et transitions
horodatées pour sept jours). Le navigateur charge ces données une seule fois
par génération du planning, puis change de journée localement, sans envoyer
de commande à Hue. À la régénération quotidienne du plan, le navigateur
charge le nouveau programme et revient sur le jour courant.

Aucune nouvelle donnée persistante, aucun nouveau calcul de simulation,
aucune bibliothèque JavaScript et aucune modification des automatismes.
Les changements temporaires dus à la télécommande (priorité dix minutes)
ne changent pas la **prévision affichée**, qui reste le programme de base.

Tests : contrôle de la route en lecture seule et de la couverture des sept
jours ajouté dans `tests/test_vacation.py`. Syntaxe JavaScript et contrats
HTML/JS/API à contrôler avant déploiement ; test visuel sur Raspberry à faire.
