"""Réveil lumineux via l'API et la boucle d'automatisation, avec pont simulé."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

import hue_web
from test_v05 import ThreeLamps


class DawnTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "settings.json"
        self.bridge = ThreeLamps()
        self.bridge.lights[0]["on"] = {"on": False}
        self.bridge.lights[0]["color"] = {}
        self.server = hue_web.HueServer(self.bridge, self.path)
        self.server.poll()
        self.client = TestClient(hue_web.app)
        controller = patch.object(hue_web, "controller", self.server)
        controller.start()
        self.addCleanup(controller.stop)
        clock = patch("hue_web.time.time", return_value=1_800_000_000)
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.wake = self.clock.return_value + 1200

    def configure(self, enabled=True, uid="light-0"):
        return self.client.put("/api/dawn", json={
            **hue_web.DAWN_DEFAULTS, "enabled": enabled, "light_id": uid,
        })

    def report(self, wake, observed=None):
        return self.client.put("/api/dawn/alarm", json={
            "alarm_at": None if wake is None else wake * 1000,
            "observed_at": (self.clock.return_value if observed is None else observed) * 1000,
        })

    def tick(self, now):
        self.clock.return_value = now
        self.server.poll()
        self.server.automate()

    def test_persisted_alarm_drives_only_selected_lamp_and_holds_target(self):
        self.assertEqual(self.configure().status_code, 200)
        self.assertEqual(self.report(self.wake).json()["data"]["alarm_at"], self.wake * 1000)
        self.server = hue_web.HueServer(self.bridge, self.path)
        self.assertEqual(self.server.dawn_state()["alarm_at"], self.wake * 1000)
        self.tick(self.wake - 1201)
        self.assertEqual(self.bridge.calls, [])
        self.tick(self.wake - 1200)
        self.tick(self.wake - 600)
        # Google Horloge may publish the following alarm as this one rings.
        self.clock.return_value = self.wake
        self.server.sync_dawn({"alarm_at": (self.wake + 86400) * 1000,
                               "observed_at": self.wake * 1000})
        self.tick(self.wake)
        self.tick(self.wake + 240)
        self.assertEqual([path for path, _ in self.bridge.calls], ["light/light-0"] * 3)
        payloads = [payload for _, payload in self.bridge.calls]
        self.assertEqual(payloads[0]["on"], {"on": True})
        self.assertEqual([p["dimming"]["brightness"] for p in payloads], [1, 35.5, 70])
        self.assertTrue(all("xy" in p["color"] for p in payloads))
        self.tick(self.wake + 301)
        self.assertIsNone(self.server.dawn_run)

    def test_disable_cancel_and_stale_observations(self):
        self.assertEqual(self.configure(uid="light-1").status_code, 400)
        self.assertIsNone(self.report(self.wake).json()["data"]["alarm_at"])
        self.configure()
        self.report(self.wake)
        self.clock.return_value += 1
        self.report(None)
        stale = self.report(self.wake, observed=self.clock.return_value - 1)
        self.assertIsNone(stale.json()["data"]["alarm_at"])
        self.tick(self.wake - 30)
        self.assertEqual(self.bridge.calls, [])
        self.report(self.wake + 60)
        self.configure(False)
        self.tick(self.wake + 5)
        self.assertEqual(self.bridge.calls, [])

    def test_manual_off_during_ramp_survives_restart(self):
        self.configure()
        self.report(self.wake)
        self.tick(self.wake - 1199)
        self.tick(self.wake - 1198)
        self.server.switch("light-0", False)
        self.bridge.calls.clear()
        self.server = hue_web.HueServer(self.bridge, self.path)
        self.tick(self.wake - 600)
        self.tick(self.wake)
        self.assertEqual(self.bridge.calls, [])

    def test_vacation_priority_and_alarm_already_passed(self):
        self.configure()
        self.report(self.wake)
        self.server.vacation.update(enabled=True, light_ids=["light-0"])
        with patch.object(self.server, "_vacation_apply_locked"):
            self.tick(self.wake - 900)
        self.server.vacation["enabled"] = False
        self.tick(self.wake + 1)
        self.assertEqual(self.bridge.calls, [])

    def test_wall_switch_off_during_dawn_is_respected(self):
        self.configure()
        self.report(self.wake)
        self.tick(self.wake - 1199)
        self.tick(self.wake - 1198)
        self.bridge.lights[0]["on"]["on"] = False
        self.bridge.calls.clear()
        self.tick(self.wake - 700)
        self.tick(self.wake - 600)
        self.assertEqual(self.bridge.calls, [])

    def test_web_alarm_replaces_schedule_and_runs_once_without_android(self):
        now = self.clock.return_value
        chosen = hue_web.datetime.fromtimestamp(now + 3600, hue_web.LOCAL_TZ)
        wake_time = chosen.strftime("%H:%M")
        settings = {**hue_web.DAWN_DEFAULTS, "enabled": True, "light_id": "light-0"}
        self.configure()
        self.report(self.wake)
        invalid = self.client.put("/api/dawn", json={**settings, "wake_time": "24:00"})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.server.dawn_state()["alarm_at"], self.wake * 1000)

        saved = self.client.put("/api/dawn", json={**settings, "wake_time": wake_time}).json()["data"]
        wake = int(chosen.replace(second=0, microsecond=0).timestamp())
        self.assertEqual(saved["next_alarm_at"], wake * 1000)
        self.assertEqual(saved["observed_at"], 0)
        self.assertEqual(self.report(None).json()["data"]["alarm_at"], wake * 1000)
        self.server = hue_web.HueServer(self.bridge, self.path)
        self.assertEqual(self.server.dawn_state()["wake_time"], wake_time)
        self.tick(wake - 1201)
        self.assertEqual(self.bridge.calls, [])
        self.tick(wake - 1200)
        self.tick(wake - 600)
        self.tick(wake)
        self.assertEqual([p["dimming"]["brightness"] for _, p in self.bridge.calls], [1, 35.5, 70])
        self.assertIsNone(self.server.dawn_state()["next_alarm_at"])
        self.server = hue_web.HueServer(self.bridge, self.path)
        self.bridge.calls.clear()
        self.tick(wake + 86400 - 600)
        self.assertFalse(any(p.get("on", {}).get("on") for _, p in self.bridge.calls))

    def test_resaving_same_hour_schedules_next_day_after_execution(self):
        local = hue_web.datetime(2026, 11, 19, 6, 30, tzinfo=hue_web.LOCAL_TZ)
        self.clock.return_value = local.timestamp() - 60
        settings = {**hue_web.DAWN_DEFAULTS, "enabled": True, "light_id": "light-0", "wake_time": "06:30"}
        self.assertEqual(self.server.set_dawn(settings)["next_alarm_at"], local.timestamp() * 1000)
        self.clock.return_value = local.timestamp()
        tomorrow = local + hue_web.timedelta(days=1)
        self.assertEqual(self.server.set_dawn(settings)["next_alarm_at"], tomorrow.timestamp() * 1000)

    def test_nonexistent_and_repeated_hours_follow_zurich_time(self):
        local = hue_web.datetime(2026, 3, 29, 0, 0, tzinfo=hue_web.LOCAL_TZ)
        next_valid = local.replace(day=30, hour=2, minute=30)
        self.assertEqual(hue_web.next_web_alarm("02:30", local.timestamp()), next_valid.timestamp() * 1000)
        first = hue_web.datetime(2026, 10, 25, 2, 30, tzinfo=hue_web.LOCAL_TZ)
        second = first.replace(fold=1)
        self.assertEqual(hue_web.next_web_alarm("02:30", first.timestamp() - 60), first.timestamp() * 1000)
        self.assertEqual(hue_web.next_web_alarm("02:30", first.timestamp() + 60), second.timestamp() * 1000)
