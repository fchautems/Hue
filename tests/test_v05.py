"""v0.5 : indépendance par lampe, migration v0.4 et restauration des réglages."""
import copy
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import hue_web
from hue_web import HueServer
from test_server import FakeClient, LIGHT


class ThreeLamps(FakeClient):
    def __init__(self):
        super().__init__()
        self.lights = []
        self.connectivity = []
        for index, name in enumerate(("Entrée", "Salon", "Douche")):
            light = copy.deepcopy(LIGHT)
            light["id"] = f"light-{index}"
            light["owner"] = {"rid": f"device-{index}"}
            light["metadata"] = {"name": name}
            light["dimming"] = {"brightness": 33 + index * 10}
            self.lights.append(light)
            self.connectivity.append({"owner": {"rid": f"device-{index}"}, "status": "connected"})

    def resource(self, path, method="GET", payload=None):
        if method == "PUT":
            self.calls.append((path, copy.deepcopy(payload)))
            uid = path.split("/")[-1]
            light = next(l for l in self.lights if l["id"] == uid)
            if "on" in payload:
                light["on"] = copy.deepcopy(payload["on"])
            if "dimming" in payload:
                light["dimming"] = copy.deepcopy(payload["dimming"])
            return []
        if path == "light":
            return self.lights
        if path == "zigbee_connectivity":
            return self.connectivity
        if path == "device":
            return [{"id": f"device-{i}", "product_data": {"model_id": "DIMMER"}}
                    for i in range(3)]
        raise ValueError(path)


class IndependentLamps(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "hue_settings.json"
        self.bridge = ThreeLamps()
        self.srv = HueServer(self.bridge, self.path, logging.getLogger("test_v05"))
        self.srv.poll()

    def test_default_is_manual_and_no_automatic_commands(self):
        state = self.srv.state()
        self.assertEqual(state["auto_count"], 0)
        self.assertEqual(state["clock_mode"], "reel")
        self.assertTrue(all(l["control_mode"] == "manuel" for l in state["lights"]))
        self.srv.automate()
        self.assertEqual(self.bridge.calls, [])

    def test_only_auto_lamp_follows_its_curve_in_accelerated_time(self):
        self.srv.set_light_mode("light-1", "auto")
        self.srv.set_clock_mode("accelere")
        self.srv.set_sim({"minute": 600, "running": False})
        self.srv.automate()
        self.assertEqual([path for path, _ in self.bridge.calls], ["light/light-1"])
        self.assertEqual(self.bridge.calls[0][1]["dimming"]["brightness"], 100)
        self.assertEqual(self.bridge.calls[0][1]["dynamics"]["duration"], 2000)
        self.assertEqual(self.srv.state()["auto_count"], 1)

    def test_manual_to_auto_transition_and_back_freezes_level(self):
        self.srv.set_clock_mode("accelere")
        self.srv.set_sim({"minute": 600, "running": False})
        self.srv.set_light_mode("light-0", "auto")
        self.srv.automate()
        self.srv.poll()
        self.srv.set_light_mode("light-0", "manuel")
        self.bridge.calls.clear()
        self.srv.automate()
        self.assertEqual(self.bridge.calls, [])
        self.assertEqual(self.srv.settings["manual_states"]["light-0"]["brightness"], 100)
        self.assertEqual(self.srv.state()["lights"][0]["control_mode"], "manuel")

    def test_manual_brightness_and_off_state_are_saved(self):
        self.srv.set_brightness("light-0", 17)
        self.srv.switch("light-0", False)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["manual_states"]["light-0"], {"on": False, "brightness": 17.0})
        self.assertEqual(saved["light_modes"]["light-0"], "manuel")
        self.assertTrue(saved["profiles"])

    def test_manual_switch_on_uses_manual_brightness_not_profile(self):
        self.srv.set_brightness("light-2", 18)
        self.srv.switch("light-2", False)
        self.srv.switch("light-2", True)
        payload = self.bridge.calls[-1][1]
        self.assertEqual(payload["dimming"]["brightness"], 18)
        self.assertTrue(payload["on"]["on"])

    def test_manual_state_restored_after_restart(self):
        self.srv.set_brightness("light-0", 23)
        self.srv.switch("light-0", False)
        self.srv.set_light_mode("light-1", "auto")
        self.bridge.calls.clear()
        self.bridge.lights[0]["on"]["on"] = True
        self.bridge.lights[0]["dimming"]["brightness"] = 88
        restarted = HueServer(self.bridge, self.path, logging.getLogger("test_v05"))
        restarted.poll()
        self.assertEqual(restarted.state()["auto_count"], 1)
        restarted.automate()
        self.assertIn("light/light-0", [c[0] for c in self.bridge.calls])
        self.assertTrue(any(c[0] == "light/light-1" for c in self.bridge.calls))
        self.assertFalse(self.bridge.lights[0]["on"]["on"])
        self.assertEqual(restarted.settings["manual_states"]["light-0"]["brightness"], 23)
        self.bridge.calls.clear()
        restarted.poll()
        restarted.automate()
        self.assertEqual(self.bridge.calls, [])

    def test_offline_manual_lamp_is_not_relit_at_restart_or_reconnect(self):
        self.srv.set_brightness("light-0", 19)
        self.bridge.calls.clear()
        self.bridge.connectivity[0]["status"] = "disconnected"
        restarted = HueServer(self.bridge, self.path, logging.getLogger("test_v05"))
        restarted.poll()
        restarted.automate()
        self.assertFalse(self.bridge.calls)
        self.bridge.connectivity[0]["status"] = "connected"
        restarted.poll()
        restarted.automate()
        self.assertFalse(self.bridge.calls)

    def test_automatic_off_lamp_never_relights(self):
        self.srv.set_light_mode("light-1", "auto")
        self.bridge.lights[1]["on"]["on"] = False
        self.srv.poll()
        self.srv.automate()
        self.assertEqual(self.bridge.calls, [])

    def test_manual_brightness_rejected_in_auto(self):
        self.srv.set_light_mode("light-0", "auto")
        with self.assertRaisesRegex(ValueError, "Manuel"):
            self.srv.set_brightness("light-0", 77)
        self.assertEqual(self.bridge.calls, [])

    def test_clock_source_does_not_change_individual_modes(self):
        self.srv.set_light_mode("light-2", "auto")
        self.srv.set_clock_mode("accelere")
        self.srv.set_clock_mode("reel")
        modes = {l["id"]: l["control_mode"] for l in self.srv.get_lights()}
        self.assertEqual(modes, {"light-0": "manuel", "light-1": "manuel", "light-2": "auto"})
        self.assertFalse(self.srv.sim["enabled"])

    def test_v04_legacy_manual_keeps_lamps_manual_and_curve(self):
        old = {"mode": "manuel", "profiles": {"light-0": [
            {"minute": 0, "brightness": 13}, {"minute": 720, "brightness": 91}]}}
        self.path.write_text(json.dumps(old))
        migrated = HueServer(self.bridge, self.path, logging.getLogger("test_v05"))
        migrated.poll()
        self.assertEqual(migrated.state()["auto_count"], 0)
        self.assertEqual(migrated.profile("light-0"), old["profiles"]["light-0"])
        self.assertIn("light_modes", json.loads(self.path.read_text()))

    def test_v04_legacy_reel_migrates_all_lamps_to_auto(self):
        self.path.write_text(json.dumps({"mode": "reel", "profiles": {}}))
        migrated = HueServer(self.bridge, self.path, logging.getLogger("test_v05"))
        migrated.poll()
        self.assertEqual(migrated.state()["auto_count"], 3)
        self.assertTrue(all(v == "auto" for v in migrated.settings["light_modes"].values()))

    def test_clock_reverts_to_realtime_after_app_restart(self):
        self.srv.set_light_mode("light-2", "auto")
        self.srv.set_clock_mode("accelere")
        restarted = HueServer(self.bridge, self.path, logging.getLogger("test_v05"))
        restarted.poll()
        self.assertEqual(restarted.clock_mode, "reel")
        self.assertEqual(restarted.settings["light_modes"]["light-2"], "auto")

    def test_invalid_modes_and_unknown_light_leave_config_untouched(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.srv.set_light_mode("light-0", "couleur")
        with self.assertRaises(ValueError):
            self.srv.set_light_mode("missing", "auto")
        with self.assertRaises(ValueError):
            self.srv.set_clock_mode("manuel")
        self.assertEqual(self.path.read_bytes(), before)

    def test_reconnect_manually_controlled_lamp_stays_independent(self):
        self.bridge.connectivity[2]["status"] = "disconnected"
        self.srv.poll()
        self.bridge.connectivity[2]["status"] = "connected"
        self.srv.poll()
        self.srv.automate()
        self.assertEqual(self.bridge.calls, [])


class V05ApiTests(unittest.TestCase):
    def setUp(self):
        self.original = hue_web.controller
        self.temp = TemporaryDirectory()
        self.bridge = ThreeLamps()
        hue_web.controller = HueServer(self.bridge, Path(self.temp.name)/"settings.json", logging.getLogger("test_v05_routes"))
        hue_web.controller.poll()
        self.client = TestClient(hue_web.app)
        self.addCleanup(self.client.close)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: setattr(hue_web, "controller", self.original))

    def test_individual_control_http(self):
        ok = self.client.post('/api/light/light-1/control-mode', json={"mode": "auto"})
        self.assertEqual(ok.status_code, 200)
        state = self.client.get('/api/state').json()
        self.assertEqual(state["auto_count"], 1)
        self.assertEqual([l["control_mode"] for l in state["lights"]], ["manuel", "auto", "manuel"])
        self.assertEqual(self.client.post('/api/light/light-1/brightness', json={"brightness": 33}).status_code, 400)
        self.assertEqual(self.client.post('/api/light/light-0/brightness', json={"brightness": 33}).status_code, 200)

    def test_clock_http_and_validation(self):
        self.assertEqual(self.client.post('/api/clock-mode', json={"mode": "accelere"}).status_code, 200)
        self.assertEqual(self.client.get('/api/state').json()["clock_mode"], "accelere")
        self.assertEqual(self.client.post('/api/clock-mode', json={"mode": "manuel"}).status_code, 400)
        self.assertEqual(self.client.post('/api/light/light-0/control-mode', json={"mode": "bad"}).status_code, 400)
        self.assertEqual(self.client.post('/api/light/not-found/control-mode', json={"mode": "auto"}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
