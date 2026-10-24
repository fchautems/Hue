import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from hue_web import HueClient, HueError, HueServer

LIGHT = {"id": "light-a", "metadata": {"name": "Salon"}, "owner": {"rid": "device-a"},
         "on": {"on": True}, "dimming": {"brightness": 50},
         "dynamics": {"status": "none"}, "powerup": {"preset": "last_on_state"}}

class FakeClient:
    ip = "10.0.0.2"
    def __init__(self):
        self.lights = [dict(LIGHT)]
        self.connectivity = [{"id": "zigbee-a", "owner": {"rid": "device-a"}, "status": "connected"}]
        self.calls = []
    def resource(self, path, method="GET", payload=None):
        if method == "PUT":
            self.calls.append((path, payload))
            if "powerup" in (payload or {}):
                powerup = payload["powerup"]
                if powerup.get("preset") == "custom":
                    dimming = powerup.get("dimming", {}).get("dimming")
                    if not isinstance(dimming, dict) or not isinstance(dimming.get("brightness"), (int, float)):
                        raise ValueError("Schéma powerup.dimming invalide")
                self.lights[0]["powerup"] = payload["powerup"]
            return []
        if path == "light":
            return self.lights
        if path == "device":
            return [{"id": "device-a", "product_data": {"model_id": "MODEL-1", "manufacturer_name": "Signify"}}]
        if path == "zigbee_connectivity":
            return self.connectivity
        raise ValueError(path)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.fake = FakeClient()
        self.server = HueServer(self.fake, Path(self.tmp.name) / "settings.json", logging.getLogger("unit_test"))
        self.server.poll()
    def tearDown(self):
        self.tmp.cleanup()
    def test_discovery_and_capabilities(self):
        lights = self.server.get_lights()
        self.assertEqual(lights[0]["model"], "MODEL-1")
        self.assertTrue(lights[0]["capabilities"]["powerup"])
        self.assertEqual(lights[0]["status"], "connected")
        self.assertNotIn("key", self.server.diagnostics())
    def test_safe_by_default(self):
        self.server.automate()
        self.assertEqual(self.fake.calls, [])
        self.server.set_mode("manuel")
        self.server.automate()
        self.assertEqual(self.fake.calls, [])
    def test_automatic_only_when_active_and_on(self):
        self.server.set_mode("accelere")
        self.server.set_sim({"minute": 600, "running": False})
        self.server.automate()
        self.assertEqual(len(self.fake.calls), 1)
        self.assertEqual(self.fake.calls[0][1]["dimming"]["brightness"], 100)
        self.fake.calls.clear()
        self.fake.lights[0]["on"] = {"on": False}
        self.server.poll()
        self.server.automate()
        self.assertEqual(self.fake.calls, [])
    def test_no_command_when_zigbee_disconnected(self):
        self.fake.connectivity[0]["status"] = "disconnected"
        self.server.poll()
        self.server.set_mode("accelere")
        self.server.set_sim({"minute": 600, "running": False})
        self.server.automate()
        self.assertEqual(self.fake.calls, [])
    def test_reconnect_gets_immediate_duration(self):
        self.fake.connectivity[0]["status"] = "disconnected"
        self.server.poll()
        self.fake.connectivity[0]["status"] = "connected"
        self.server.poll()
        self.assertIn("light-a", self.server.reconnect_pending)
        self.server.set_mode("accelere")
        self.server.set_sim({"minute": 600, "running": False})
        self.server.automate()
        self.assertEqual(self.fake.calls[0][1]["dynamics"]["duration"], 1500)
        self.assertNotIn("light-a", self.server.reconnect_pending)
    def test_preset_writes_only_with_explicit_action(self):
        self.assertEqual(self.fake.calls, [])
        self.server.set_powerup("light-a", "custom", 17)
        self.assertEqual(
            self.fake.calls[0][1]["powerup"]["dimming"]["dimming"]["brightness"],
            17,
        )
    def test_power_cycle_diagnostic_uses_observed_zigbee_transition(self):
        self.server.arm_power_test("light-a")
        self.assertEqual(self.server.diagnostics()["power_tests"]["light-a"]["status"], "armé")
        self.fake.connectivity[0]["status"] = "disconnected"
        self.server.poll()
        self.assertEqual(self.server.diagnostics()["power_tests"]["light-a"]["status"], "hors ligne observé")
        self.fake.connectivity[0]["status"] = "connected"
        self.server.poll()
        test = self.server.diagnostics()["power_tests"]["light-a"]
        self.assertEqual(test["status"], "reconnecté")
        self.assertGreaterEqual(test["observed_offline_seconds"], 0)

    def test_profile_persisted(self):
        self.server.set_profile("light-a", [{"minute": 0, "brightness": 5}, {"minute": 720, "brightness": 99}])
        self.assertTrue((Path(self.tmp.name) / "settings.json").is_file())

    def test_hue_error_keeps_detail_without_exposing_key(self):
        class Response:
            status_code = 400
            def json(self):
                return {"errors": [{"description": "body contains invalid value"}]}
            def raise_for_status(self):
                raise AssertionError("Les erreurs Hue structurées sont traitées avant HTTPError")
        class Session:
            def request(self, *args, **kwargs):
                return Response()
        client = HueClient("10.0.0.2", "secret-test-key")
        client.session = Session()
        with self.assertRaises(HueError) as caught:
            client.resource("light/light-a", "PUT", {"powerup": {"preset": "custom"}})
        message = str(caught.exception)
        self.assertIn("body contains invalid value", message)
        self.assertNotIn("secret-test-key", message)

if __name__ == "__main__":
    unittest.main()
