# Hue Lab v0.5.2 — Courbe simple, progressive et sans retour en arrière

## But

Ajout **sans remplacer la courbe personnalisée** d'un type « Simple » pour chaque lampe. Le profil simple se définit par six réglages :

- Début de montée (heure du lever personnel, par défaut 06:15).
- Fin de montée (13:00).
- Début de descente (18:00).
- Fin de descente (heure du coucher personnel, 23:00).
- Luminosité minimale nocturne (10 %).
- Luminosité maximale de journée (85 %).

La courbe suit cinq phases : **nuit basse stable → montée monotone → plateau haut stable → descente monotone → nuit basse stable**. Les rampes utilisent la fonction quintique *smootherstep* (continuité de la pente et de la courbure au raccord des plateaux), sans inversion au sommet. Les rampes durent au moins 30 minutes ; l'heure du lever est **le début**, non la fin de la montée. Les horaires doivent être dans l'ordre sur une même journée. Tous les réglages sont individuels par lampe.

## Interface

Dans « Courbes horaires » : choisir **Simple** ou **Personnalisée**. En mode Simple, régler les six valeurs en observant la prévisualisation, puis cliquer sur **Enregistrer et activer**. Les changements de prévisualisation ne commandent pas les ampoules. Pour retrouver une courbe à points, choisir **Personnalisée** puis **Activer cette courbe** ; ses points n'ont pas été supprimés. Enregistrer des points personnalisés active aussi le type Personnalisée.

## Sécurité et compatibilité

- Le type de courbe est indépendant du mode **Manuel / Auto**. La consigne automatique ne commande que les lampes **allumées et joignables**, et ne force pas le rallumage d'une ampoule éteinte.
- Les réglages `profiles` existants restent inchangés. Deux nouvelles clés, `simple_profiles` et `profile_types`, sont écrites **uniquement dans le fichier privé** `hue_settings.json` sur le Raspberry Pi, sauvegardé par le système de mise à jour.
- Par défaut, **toutes les lampes conservent leur profil Personnalisé** tant que l'utilisateur n'active pas volontairement Simple.
- La luminosité réelle est calculée à chaque application (pas une liste de points approximatifs) et reste cohérente avec l'horloge réelle et le simulateur accéléré.
- Pas de couleur, température, météo, soleil ou nouvelles commandes de pont Hue dans cette version.

## Validation

Tests unitaires : continuité, montée/décroissance monotones, luminosités extrêmes, jour cyclique, paramètres invalides. Tests de serveur et API : migration sans perte, persistance au redémarrage, indépendance de trois lampes, refus de rallumer une lampe éteinte et bascule réversible des types. Vérification syntaxique JS. Essai réel sur Raspberry à effectuer après installation.

### Mise à jour

Via Hue Lab → Mises à jour → Vérifier GitHub → Installer et redémarrer. L'outil actuel teste le nouveau programme avant l'installation et conserve les réglages privés et une sauvegarde du commit précédent.
