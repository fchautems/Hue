# APK de test : prochain réveil Android

APK indépendante de Hue Lab (`ch.huelab.alarmprobe`). Aucune connexion au Raspberry,
aucune modification des lampes. Objectif : **mesurer**, pas supposer, les événements
Android lorsque l'application n'est plus ouverte.

## Test sur Pixel

1. Installer l'APK, ouvrir, cliquer « Activer une vérification ~15 min ».
2. Dans Horloge Google, créer ou modifier un réveil ; revenir à l'APK et contrôler
   la date/heure détectée, ainsi que le journal des diffusions « dynamique ».
3. Swiper l'APK depuis les applications récentes (ne pas utiliser « Forcer l'arrêt »).
4. Modifier à nouveau le réveil sans ouvrir l'APK. Attendre 20 à 40 minutes,
   puis ouvrir l'APK et cliquer « Copier le journal ». L'entrée « ouverture » est
   attendue ; vérifier si « diffusion statique » et/ou « vérification périodique »
   sont apparues **avant** l'ouverture, avec l'heure correcte.
5. Refaire un essai écran verrouillé, un essai après redémarrage, puis un essai
   avec « Forcer l'arrêt » pour distinguer les limitations. Ne pas modifier de
   réveil important sans le remettre à son heure ensuite.
6. Supposer le Wi-Fi désactivé en mode avion : l'heure devra à terme avoir été
   envoyée **avant** le mode avion ; cette APK ne transmet encore aucune donnée.

Un « aucun réveil » est possible si l'application Horloge ne publie pas l'alarme
par le mécanisme standard Android (`getNextAlarmClock`).

## Limites attendues

Le broadcast `ACTION_NEXT_ALARM_CLOCK_CHANGED` est documenté comme envoyé
seulement aux receveurs enregistrés. Son réveil d'un processus fermé par un
receiver déclaré dans le manifeste n'est **pas** garanti, d'où ce test.
`JobScheduler` permet une récurrence de 15 minutes mais Android reporte l'exécution
selon batterie, veille et restrictions. Cette APK de test ne maintient aucun
service permanent en arrière-plan.

Build JDK 17 + Android SDK 35, build tools 35.0.0 :
`HUE_ANDROID_KEYSTORE=/chemin/keystore bash android/probe/build.sh /chemin/Hue-Reveil-Test.apk`
L'artefact CI est signé avec une clé temporaire et peut nécessiter désinstallation
avant une future APK de test. Il ne remplace pas Hue Lab.

Docs Android :
- https://developer.android.com/reference/android/app/AlarmManager#getNextAlarmClock()
- https://developer.android.com/reference/android/app/AlarmManager#ACTION_NEXT_ALARM_CLOCK_CHANGED
- https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work
