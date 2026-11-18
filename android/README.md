# Hue Lab pour Android

Prototype WebView. L’icône Hue Lab ouvre la page du serveur sur le Wi-Fi local.
L’adresse initiale est `10.0.0.12:8765`. Depuis l’écran de connexion ou le bouton
Retour d’Android, « Changer l’adresse du serveur » permet de saisir un autre
IPv4 privé avec son port. Le port par défaut est 8765. Les mises à jour du serveur
apparaissent dans cette même application. Les liens externes s’ouvrent dans le
navigateur, qui sert aussi à exporter les diagnostics JSON.

## Réveil lumineux

Sur la page **Automatisations**, active **Réveil lumineux**, choisis une
lampe couleur, sa teinte, les minutes d’avance et la luminosité finale. La
carte affiche l’alarme reçue par le Raspberry et l’heure de synchronisation.
Avant le mode avion, vérifie l’heure affichée. Depuis l’app Android, le bouton
**Synchroniser maintenant** permet de confirmer immédiatement l’envoi sur le
Wi-Fi local. Le Raspberry programme la montée avec l’heure reçue, même si le
téléphone est ensuite hors ligne. Un changement hors ligne ne parvient au
Raspberry qu’après un nouvel appui manuel sur le réseau local.

Depuis la version 0.3, Android lit la prochaine alarme **uniquement** après un appui
sur **Synchroniser maintenant** lorsque le réveil lumineux est activé. Modifier
les réglages ou rouvrir l’application ne lance aucune lecture ni tâche périodique.
Après une modification ou une annulation de l’alarme Android, appuie de nouveau
sur Synchroniser pour mettre le Raspberry à jour. L’ancienne tâche planifiée
est annulée au lancement de la nouvelle APK. Le niveau final est maintenu cinq minutes avant de rendre la
main au mode précédent. Un arrêt manuel pendant la montée annule l’aube en
cours pour cette lampe.

## Essai sans remplacer l'application existante

La CI de la PR produit aussi **Hue-Lab-Test-0.3.1.apk** : application séparée « Hue Lab Test 0.3.1 »
(package `ch.huelab.mobile.test031`) avec ses propres préférences et données. Elle n'écrase
pas Hue Lab, mais partage les mêmes services Raspberry si elle est configurée sur la
même adresse : un réveil envoyé au Raspberry peut donc piloter les vraies lampes.
Ce prototype ne doit être installé que pour un essai volontaire.
**Important :** l'APK normale déjà installée peut encore exécuter son ancien suivi
automatique ; installer l'APK Test ne l'arrête pas. Avant l'essai, dans Android,
ouvre **Paramètres → Applications → Hue Lab → Forcer l'arrêt** pour suspendre
la version normale, puis n'ouvre que **Hue Lab Test 0.3.1**. Ne réutilise pas la version
normale pour tester l'absence de surveillance.

Pour lire le journal, ouvre **Hue Lab Test 0.3.1**, utilise le bouton Retour Android,
puis **Journal du réveil**. Le menu permet aussi **Partager le journal** vers une
application de ton choix. Les dernières lignes horodatées sont conservées localement,
sans surveillance en arrière-plan : ouverture, appui manuel, heure d'alarme lue,
succès ou échec de l'envoi. Ne partage le journal qu'avec une personne de confiance,
car il contient l'heure de tes alarmes. Les logs seuls ne démontrent pas l'absence
absolue de toute activité, qui est aussi contrôlée dans le code.

Compilation avec JDK 17, la plateforme Android 35 et les build-tools 35.0.0.
`HUE_ANDROID_KEYSTORE` doit pointer vers une clé de test Android conservée en
privé. Lance `bash android/build.sh /chemin/absolu/Hue-Lab.apk`.
Le build CI produit un APK de prototype signé avec une clé de test éphémère.

## Correctif 0.3.1 et validation

L'envoi depuis la carte web exige maintenant une confirmation native Android :
appuyer sur « Synchroniser maintenant » dans cette confirmation. Cela bloque les
anciennes pages Raspberry qui demandent encore un envoi après Enregistrer.
Le menu Retour → Synchroniser maintenant offre également un accès manuel direct.
Aucune lecture d'alarme avant cette action native. Les doubles appuis sont ignorés,
la réponse doit confirmer exactement l'alarme et l'observation envoyées.

La nouvelle variante s'installe à côté de Test 0.3, sans la remplacer. La CI utilise
une signature éphémère : la future mise à jour de l'APK normale nécessite une stratégie
de signature compatible ; ne pas désinstaller l'APK normale pour cet essai.
Voir [l'audit et le protocole progressif](AUDIT_MANUAL_ALARM.md).

Tests JVM hors appareil : `bash android/test.sh` (JDK, curl ; org.json épinglé).
