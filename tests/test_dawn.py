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
