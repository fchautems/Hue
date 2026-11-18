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
        self.assertEqual(activity.count("syncAlarm(true);"), 1)
        self.assertIn('"huelab://sync-alarm".equals(url.toString())', activity)
        self.assertIn("getNextAlarmClock()", alarm)
        self.assertIn('sync.addEventListener("click", askAndroid);', ui)
        self.assertNotIn("askAndroid();", ui)
        self.assertIn("sync.hidden = !native || !data.enabled;", ui)
