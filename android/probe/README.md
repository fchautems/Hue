# APK de test : prochain réveil Android — vérification chaque minute

Application indépendante de Hue Lab (`ch.huelab.alarmprobe`). Aucune connexion au Raspberry,
aucune commande envoyée aux lampes.

## Test Pixel

1. **Désinstaller l'ancienne APK « Hue – test réveil »**, puis installer la nouvelle
   « Hue – réveil 1 min ». La signature de CI change à chaque compilation ;
   conserver l'ancien journal au préalable si besoin.
2. Ouvrir, autoriser les notifications si demandé et choisir
   « Démarrer test 1 min (45 min) ». Une notification persistante apparaît.
3. Balayer l'application hors des applications récentes. Ne pas toucher à « Forcer l'arrêt ».
4. Modifier le prochain réveil dans Horloge Google, puis verrouiller le téléphone.
   Attendre quelques minutes sans rouvrir l'APK.
5. Rouvrir l'APK, copier le journal. Chercher, **avant la ligne d'ouverture**,
   « swipe applications récentes », « vérification 1 min (service) »,
   puis le nouveau réveil et l'heure de la première détection.
6. Arrêter le test via le bouton ou la notification. Il s'arrête de lui-même
   **au plus tard après 45 minutes**, si le service fonctionne normalement.

Le service relève l'alarme immédiatement, puis environ toutes les 60 secondes ;
il utilise une notification visible et un verrou de réveil CPU (`PARTIAL_WAKE_LOCK`)
pour permettre le test écran éteint. **C'est un outil de diagnostic temporaire** :
la consommation de batterie est supérieure à celle d'une application normale.
L'exécution peut malgré tout être interrompue par Android ; le journal sert à le constater.

Le receiver expérimental déclaré dans le manifeste reste actif afin de comparer
les événements Android et la lecture minute. Le `JobScheduler` de 15 min de la
version précédente est désactivé au lancement de l'APK 0.2.

Sur certains Android, les services `specialUse` peuvent être restreints ;
un refus de démarrage est journalisé. L'absence de ligne pendant une période
verrouillée signifie que le service n'a pas pu assurer le rythme attendu.

## Limitations et suite

Aucun envoi réseau n'est fait : même si le test réussit, synchroniser le Raspberry
nécessitera une évolution distincte, avant le mode avion coupant le Wi-Fi.
L'application ne doit pas tourner toute la nuit sous verrou de réveil permanent
pour le fonctionnement définitif.

Build JDK 17 + Android SDK 35, build tools 35.0.0 :
`HUE_ANDROID_KEYSTORE=/chemin/keystore bash android/probe/build.sh /chemin/Hue-Reveil-1min.apk`.

Documentation Android :
- https://developer.android.com/reference/android/app/job/JobInfo#getMinPeriodMillis()
- https://developer.android.com/develop/background-work/services/fgs/service-types
- https://developer.android.com/reference/android/app/AlarmManager#getNextAlarmClock()
- https://developer.android.com/topic/performance/vitals/stuck-wakelock
