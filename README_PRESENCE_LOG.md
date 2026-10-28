# Historique d'éclairage — simulateur de présence (2026-10-28)

Le Raspberry enregistre les changements **observés** des ampoules dans
`logs/presence_events.csv`, automatiquement, dès que Hue Lab tourne et que
le pont est associé. Aucune action ni activation manuelle n'est requise.

Format CSV UTF-8, séparateur `;` :

| Colonne | Sens |
| --- | --- |
| `detected_at` | Date et heure locale avec fuseau (observation, pas instant électrique) |
| `light_id` | Identifiant stable de l'ampoule |
| `light_name` | Nom donné dans Hue |
| `event` | `zigbee_connected`, `zigbee_disconnected`, `light_on`, `light_off` |

**Important :** couper l'interrupteur mural supprime l'alimentation et peut
provoquer une perte de connexion Zigbee détectée tardivement. Une ampoule peut
rester déclarée connectée pendant un certain temps ; une coupure et un retour
rapides peuvent ne pas apparaître du tout. Les événements Zigbee ne prouvent
donc pas une coupure de courant, et les champs `on`/`off` de l'API ne
représentent pas nécessairement la position physique de l'interrupteur.

Le journal distingue volontairement les observations de connectivité
(`zigbee_*`) des changements logiques d'allumage (`light_*`). Les premières
observations au démarrage établissent une référence, sans créer de faux
événement. Les changements répétés identiques ne sont pas dupliqués. Hue Lab
ne commande aucune lumière pour remplir cet historique.

Les données restent uniquement sur le Raspberry : `logs/` est exclu de Git.
Le fichier n'est pas écrasé lors des redémarrages de Hue Lab ; il est conservé
pendant les mises à jour normales de l'application. Il peut être consulté avec
un éditeur de texte ou un tableur.

## Vérification rapide

1. Mettre à jour Hue Lab depuis l'onglet **Mises à jour** et attendre son redémarrage.
2. Laisser Hue Lab allumé sur le Raspberry ; couper l'interrupteur d'une lampe
   assez longtemps pour que le pont constate sa déconnexion, puis le rallumer.
3. Vérifier `logs/presence_events.csv` sur le Raspberry, en comparant
   les timestamps à l'heure réelle des manipulations.

Tests logiciels à lancer sur un PC ou sur le Raspberry :
`python -m unittest discover -s tests -p 'test_presence_log.py' -v`.

Aucun test matériel ni exécution de la suite complète n'est revendiqué
pour ce changement. Cet historique pourra servir à concevoir ultérieurement
un simulateur de présence, sans activer un tel simulateur aujourd'hui.
