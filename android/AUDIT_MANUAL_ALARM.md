# Audit du réveil manuel — 2026-11-18

## Périmètre et reprise

PR #37, branche `fix/reveil-manuel-sans-boucle-20261118`, tête initiale
`5526b84acf13b478878c805c5800305a2f85032d`. Diff complet contre `main`
`ce408d6a388de48fa1a6a46ac63090d1a56b9a5f` examiné, sources Android,
script de build, manifeste, workflows, `static/dawn.js`, API et tests Réveil lus.
PROJECT_STATE et Brain `projects/hue-lab.md`, MODEL_GUIDE lus.
Les runs 44252504353 / 44252504349 validaient exactement `866e91254348afa43dc7eecc030553a73d666b4a`,
pas la tête initiale documentaire. Les résultats de cette nouvelle révision sont consignés dans PROJECT_STATE.

Retour utilisateur : Test 0.3 installée ; seules ouvertures observées à 07:49:26 et
07:52:14 le 18 novembre. Aucun envoi manuel matériel validé. Le lien entre les
anciens redémarrages et Hue Lab reste inconnu.

## Constats et corrections 0.3.1

- La file ExecutorService acceptait tous les appuis : remplacée par un verrou
  commun au processus, sans file, et une protection d'une seconde après la fin.
  Un thread ponctuel finit après la demande ; aucun exécuteur inactif permanent.
- HTTP 200 / ok ne prouvait pas l'acceptation : vérification de `enabled`,
  `observed_at` et `alarm_at` retournés, tous identiques à l'envoi attendu.
  Une réponse perdue ou discordante reste non confirmée ; aucun réessai applicatif.
- L'ancienne page Raspberry appelle encore `huelab://sync-alarm` après Enregistrer.
  Le lien ouvre maintenant seulement une confirmation Android. Seul le bouton
  natif « Synchroniser maintenant » lit l'alarme. Ne pas se fier à `hasGesture`
  pour distinguer un clic Synchroniser d'une navigation issue d'Enregistrer.
  Retour → Synchroniser maintenant offre un accès natif direct, y compris hors ligne
  (l'échec réseau se produit avant la lecture d'alarme).
- Journal limité à 10 000 caractères, rotation sur une ligne complète vers 8 000 :
  date, millisecondes, fuseau ; appui accepté/ignoré ; lecture et heure exacte ;
  envoi avec les deux timestamps ; statut HTTP ; état retourné ; erreur précise.
  Consultation et ACTION_SEND uniquement sur demande, données privées locales.
- Délais connexion et lecture de 1 600 ms ; réponse plafonnée à 8 Kio ; budget de
  lecture de réponse de 5 s par échange, redirections/cache désactivés, connexion
  non réutilisée. Ce ne sont pas des garanties de délai temps réel du système.
- Variante `ch.huelab.mobile.test031`, nom « Hue Lab Test 0.3.1 », versionCode 5.
  Ni sharedUserId, fournisseur partagé, stockage externe ni sauvegarde Android.
  Préférences et données WebView distinctes des packages normal et Test 0.3.
  L'adresse Raspberry peut être commune : les réglages serveur sont alors partagés.

## Entrées et cycle de vie

| Événement | Résultat vérifié dans les sources | Limite matérielle |
|---|---|---|
| Ouverture / recréation Activity | Annule job 271 de son package, journalise, charge la WebView ; aucun appel de lecture d'alarme | À observer sur Pixel |
| Reprise / déverrouillage | Aucun hook de synchronisation | À observer sur Pixel |
| Fermeture / verrouillage | Aucun nouveau travail ; une demande explicitement lancée peut encore se terminer | Pas de wake lock ni garantie de fin si Android tue le processus |
| Redémarrage Android | Aucun receiver, service, permission de boot ni Application personnalisée | Aucune validation sur Pixel redémarré |
| Changement / suppression d'alarme | Aucun listener, callback, receiver ou tâche ; nécessite nouveau geste manuel | À observer sur Pixel |
| Enregistrer / changer d'adresse | Aucun accès aux alarmes ; une ancienne page peut seulement afficher la confirmation native | Annuler cette confirmation ne lit rien |
| Double appui / recréation pendant un envoi | Verrou statique commun au processus, aucun empilement | Réseau Android réel à essayer |

Le manifeste ne déclare qu'une Activity et INTERNET. Sources supprimées pour
AlarmChangedReceiver / AlarmSyncJob. Aucun AlarmManager.set, JobScheduler.schedule,
WorkManager, timer, alarm listener, boucle de polling d'alarme ni JavaScriptInterface.
Le rafraîchissement web de l'état du Raspberry est conservé ; il ne consulte pas Android.
Le seul accès à getNextAlarmClock est dans la chaîne d'envoi manuel.

## Migration future de l'APK normale

Historique vérifié : job intégré ID 271, namespace par défaut, package
`ch.huelab.mobile`. À la première ouverture de la mise à jour de ce même package,
`cancel(271)` est appelé puis `getPendingJob(271)` est journalisé. Aucun job nouveau
n'est créé. Le service et le receiver historiques sont absents du manifeste.
Il n'y a volontairement aucun receiver de remplacement de package : ne pas confondre
installation et première ouverture. Test 0.3.1 ne peut annuler les jobs d'un autre package.
Les anciens prototypes `android/probe` étaient séparés et ne sont pas inclus au build.

**Blocage connu pour la distribution normale :** la CI génère une clé de test
éphémère à chaque run. La nouvelle signature ne permet pas une mise à jour sur place
d'une APK signée avec une autre clé. La future livraison normale doit retrouver la
clé installée, ou définir une migration explicite après sauvegarde des données utiles.
Aucune désinstallation, modification de paramètres Pixel ni installation normale faite ici.
Le nouveau package Test 0.3.1 évite ce conflit sans remplacer les APK existantes.
Garder l'ancienne version normale arrêtée pendant l'essai, comme dans le protocole initial.

## Vérifications et limites

- 19 scénarios JVM exécutent le vrai AlarmSync avec services Android et transport HTTP
  simulés : ouverture/journal sans accès, succès, doubles appuis pendant/après envoi,
  désactivation, absence d'alarme, Wi-Fi coupé, timeout, JSON invalide, réponse trop grande,
  ok faux, HTTP 302/400/500, observation différente, alarme différente, désactivation
  concurrente, réponse PUT perdue, changement d'adresse, rotation/isolation du journal.
  Les scénarios de données privées simulés complètent le contrôle des packages ; ils ne
  remplacent pas le sandbox Android réel. Les simulations ne testent pas les internals
  réseau ni le cycle de vie du système Android.
- Régression Python sur manifeste et points d'entrée ; test serveur supplémentaire :
  alarme persistée, serveur recréé, progression complète jusqu'au réveil puis maintien,
  sans aucun nouvel envoi téléphone. Les tests existants couvrent Vacances et arrêt manuel.
- Aucun code de lampes, profils, commandes ou Vacances modifié. Aucun déploiement Raspberry.
- Les tests JVM ne sont pas une exécution d'Android et ne démontrent pas la stabilité
  du Pixel. CI et signature ne sont pas une preuve de sécurité absolue.

## Livraison vérifiée

Code : `445fb1a60248a969f3ae88a4ef9d2d02d1725a60`. CI checkout synthétique
`8aa987f914ecedee451fd8433acfaa674c05c8e4`, arbre identique à celui de la branche.
[Compilation, 19 simulations JVM, signature et package](https://github.com/fchautems/Hue/actions/runs/44261711295) : réussis.
[230 tests Python, parité, six suites Node et deux parcours Chromium](https://github.com/fchautems/Hue/actions/runs/44261711326) : réussis.
Les changements de livraison postérieurs à ce code sont uniquement documentaires.

APK : `Hue-Lab-Test-0.3.1.apk`, 20 977 octets. Signatures v2/v3 valides dans le run.
SHA-256 : `30086744d1ae11bd43eed430968a56c817252852c80018b5c51330aa6b097dcc`.
[Télécharger l'APK Test](https://chatgpt.com/library?file_id=libfile_733be41c49dc8191a650d4f02118fedf&account_id=personal).
ZIP artefact ID 14408905508, empreinte vérifiée après téléchargement :
`f2fd9a785776a2f4303931deb19130d9ae41070147174c50337bdbd87b047e17`.

## Essai matériel progressif

1. Installer uniquement Hue-Lab-Test-0.3.1.apk. Garder la version normale arrêtée.
   Ouvrir Test 0.3.1 et vérifier l'adresse du Raspberry. Ne modifier aucun paramètre Android
   pour l'audit ; aucun ADB, reset ni permission particulière requis par la nouvelle APK.
2. Ouvrir Retour → Journal du réveil. Sans Synchroniser, seules ouverture/annulation
   de tâche doivent apparaître. Fermer/rouvrir, verrouiller/déverrouiller, puis recontrôler.
3. Avec le réveil lumineux déjà enregistré comme actif, vérifier l'alarme Android voulue,
   sur un horaire non critique avec assez de marge pour la rampe configurée. Sur le Wi-Fi,
   Retour → Synchroniser maintenant. Le journal doit montrer **une** lecture et **un** envoi,
   l'heure exacte, HTTP 200, l'état retourné identique et la confirmation. La même action
   depuis la carte web demande d'abord la confirmation native. Une double pression doit
   être ignorée. En cas de non-confirmation, consulter le journal avant un nouvel appui.
4. Seulement après confirmation, passer le téléphone hors ligne / en mode avion selon
   l'usage habituel ; vérifier que le Raspberry conserve l'heure et exécute la rampe.
   Aucun nouvel événement de synchronisation ne doit apparaître. Le retour sur le Wi-Fi
   et la réouverture ne doivent rien renvoyer.
5. Essais secondaires séparés : aucune alarme (efface explicitement le réveil reçu),
   réveil désactivé, Wi-Fi coupé, changement d'alarme sans appui puis avec appui.
   Exporter le journal via Retour → Journal du réveil → Partager le journal.

Le téléphone et le Raspberry réels restent à valider par Fréd. Garder PR #37 en
brouillon ; aucune fusion sur main avant son retour fonctionnel.

Références Android :
- https://developer.android.com/reference/android/app/job/JobScheduler
- https://developer.android.com/reference/android/webkit/WebResourceRequest
- https://developer.android.com/reference/android/app/AlarmManager#getNextAlarmClock()
