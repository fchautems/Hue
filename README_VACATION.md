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
