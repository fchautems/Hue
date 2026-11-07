# Hue Lab pour Android

Prototype WebView. L’icône Hue Lab ouvre la page du serveur sur le Wi-Fi local.
L’adresse initiale est `10.0.0.12:8765`. Depuis l’écran de connexion ou le bouton
Retour d’Android, « Changer l’adresse du serveur » permet de saisir un autre
IPv4 privé avec son port. Le port par défaut est 8765. Les mises à jour du serveur
apparaissent dans cette même application. Les liens externes s’ouvrent dans le
navigateur, qui sert aussi à exporter les diagnostics JSON.

Compilation avec JDK 17, la plateforme Android 35 et les build-tools 35.0.0.
`HUE_ANDROID_KEYSTORE` doit pointer vers une clé de test Android conservée en
privé. Lance `bash android/build.sh /chemin/absolu/Hue-Lab.apk`.
Le build CI produit un APK de prototype signé avec une clé de test éphémère.
