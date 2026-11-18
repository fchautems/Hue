"""Régression : la lecture des alarmes Android reste exclusivement manuelle."""
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class AndroidManualAlarmTests(TestCase):
    def test_no_automatic_alarm_triggers(self):
        manifest = (ROOT / "android/AndroidManifest.xml").read_text(encoding="utf-8")
        activity = (ROOT / "android/src/ch/huelab/mobile/MainActivity.java").read_text(encoding="utf-8")
        alarm = (ROOT / "android/src/ch/huelab/mobile/AlarmSync.java").read_text(encoding="utf-8")
        self.assertNotIn("NEXT_ALARM_CLOCK_CHANGED", manifest)
        self.assertNotIn("RECEIVE_BOOT_COMPLETED", manifest)
        self.assertNotIn("AlarmChangedReceiver", manifest)
        self.assertNotIn("AlarmSyncJob", manifest)
        self.assertNotIn("registerReceiver(", activity)
        self.assertNotIn("onResume()", activity)
        self.assertNotIn("syncAlarm(false)", activity)
        self.assertNotIn("setPeriodic(", alarm)
        self.assertNotIn("jobs.schedule(", alarm)
        self.assertIn("jobs.cancel(271)", activity)

    def test_explicit_button_is_the_only_alarm_read_trigger(self):
        activity = (ROOT / "android/src/ch/huelab/mobile/MainActivity.java").read_text(encoding="utf-8")
        alarm = (ROOT / "android/src/ch/huelab/mobile/AlarmSync.java").read_text(encoding="utf-8")
        ui = (ROOT / "static/dawn.js").read_text(encoding="utf-8")
        self.assertEqual(activity.count("syncAlarm(true)"), 2)
        self.assertIn('"huelab://sync-alarm".equals(url.toString())', activity)
        self.assertIn("getNextAlarmClock()", alarm)
        self.assertIn('sync.addEventListener("click", askAndroid);', ui)
        self.assertNotIn("askAndroid();", ui)
        self.assertIn("sync.hidden = !native || !data.enabled;", ui)

    def test_local_diagnostics_and_separate_test_apk(self):
        activity = (ROOT / "android/src/ch/huelab/mobile/MainActivity.java").read_text(encoding="utf-8")
        alarm = (ROOT / "android/src/ch/huelab/mobile/AlarmSync.java").read_text(encoding="utf-8")
        build = (ROOT / "android/build.sh").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/android.yml").read_text(encoding="utf-8")
        self.assertIn("AlarmSync.diagnosticLog(this)", activity)
        self.assertIn("Journal du réveil", activity)
        self.assertIn("Intent.ACTION_SEND", activity)
        self.assertIn("DIAGNOSTICS_KEY", alarm)
        self.assertIn("Prochaine alarme détectée", alarm)
        self.assertIn("Synchronisation confirmée par le Raspberry", alarm)
        self.assertIn("HUE_ANDROID_TEST_VARIANT", build)
        self.assertIn('package="ch.huelab.mobile.test031"', build)
        self.assertIn("Hue-Lab-Test-0.3.1.apk", workflow)

    def test_legacy_web_page_cannot_trigger_automatic_sync(self):
        activity = (ROOT / "android/src/ch/huelab/mobile/MainActivity.java").read_text(encoding="utf-8")
        self.assertIn('setPositiveButton("Synchroniser maintenant", (dialog, which) -> syncAlarm(true))', activity)
        route = activity.split('"huelab://sync-alarm".equals(url.toString())')[1].split("return true;")[0]
        self.assertIn("confirmManualSync();", route)
        self.assertNotIn("syncAlarm(true)", route)
        self.assertIn("else if (index == 2) syncAlarm(true);", activity)
        self.assertNotIn("addJavascriptInterface", activity)

    def test_no_remaining_android_entry_points(self):
        import xml.etree.ElementTree as ET
        manifest = ET.parse(ROOT / "android/AndroidManifest.xml").getroot()
        app = manifest.find("application")
        self.assertEqual([child.tag for child in app], ["activity"])
        java = "\n".join(p.read_text() for p in (ROOT / "android/src").rglob("*.java"))
        for forbidden in ("BroadcastReceiver", "JobService", "registerReceiver(", "setPeriodic(",
                          "scheduleAtFixedRate", "postDelayed(", "addJavascriptInterface", "WorkManager"):
            self.assertNotIn(forbidden, java)
        self.assertEqual(java.count("getNextAlarmClock()"), 1)
