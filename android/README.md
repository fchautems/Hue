# Hue Lab pour Android

Prototype WebView. L’icône Hue Lab ouvre la page du serveur sur le Wi-Fi local.
L’adresse initiale est `10.0.0.12:8765`. Depuis l’écran de connexion ou le bouton
Retour d’Android, « Changer l’adresse du serveur » permet de saisir un autre
IPv4 privé avec son port. Le port par défaut est 8765. Les mises à jour du serveur
apparaissent dans cette même application. Les liens externes s’ouvrent dans le
navigateur, qui sert aussi à exporter les diagnostics JSON.

## Réveil lumineux

Sur la page **Lampes & vacances**, active **Réveil lumineux**, choisis une
lampe couleur, sa teinte, les minutes d’avance et la luminosité finale. La
carte affiche l’alarme reçue par le Raspberry et l’heure de synchronisation.
Avant le mode avion, vérifie l’heure affichée. Depuis l’app Android, le bouton
**Synchroniser maintenant** permet de confirmer immédiatement l’envoi sur le
Wi-Fi local. Le Raspberry programme la montée avec l’heure reçue, même si le
téléphone est ensuite hors ligne. Un changement hors ligne ne parvient au
Raspberry qu’au retour sur le réseau local.

Android lit aussi l’alarme à l’ouverture de Hue Lab, sur les notifications de
changement reçues et via une tâche périodique de secours dont Android fixe
l’heure réelle. Le niveau final est maintenu cinq minutes avant de rendre la
main au mode précédent. Un arrêt manuel pendant la montée annule l’aube en
cours pour cette lampe.

Compilation avec JDK 17, la plateforme Android 35 et les build-tools 35.0.0.
`HUE_ANDROID_KEYSTORE` doit pointer vers une clé de test Android conservée en
privé. Lance `bash android/build.sh /chemin/absolu/Hue-Lab.apk`.
Le build CI produit un APK de prototype signé avec une clé de test éphémère.
