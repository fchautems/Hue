"""Solo through the web routes and real monitor with a simulated CLIP bridge."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

import hue_web
from test_v05 import ThreeLamps


class SoloBridge(ThreeLamps):
    def __init__(self):
        super().__init__()
        self.lights[0]["on"]["on"] = False
        self.lights[1]["on"]["on"] = False
        self.rooms = [
            {"id": f"room-{room}", "type": "room",
             "children": [{"rtype": "device", "rid": f"device-{index}"} for index in lamps]}
            for room, lamps in enumerate(([0, 1], [2]))
        ]
        self.zone = {"id": "zone", "type": "zone", "children": [
            {"rtype": "room", "rid": room["id"]} for room in self.rooms[:2]]}
        self.accessory = {"type": "behavior_instance", "enabled": True, "configuration": {
            "buttons": {"button-on": {"on_short_release": {
                "action": "on", "where": [{"group": {"rtype": "zone", "rid": "zone"}}]}}}}}
        self.reject = set()
        self.defer_off = set()

    def resource(self, path, method="GET", payload=None):
        if method == "GET":
            if path == "room":
                return copy.deepcopy(self.rooms)
            if path == "":
                return copy.deepcopy([*self.rooms, self.zone, self.accessory])
        if method == "PUT" and path in self.reject:
            self.calls.append((path, copy.deepcopy(payload)))
            raise hue_web.HueError("Commande refusée")
        if method == "PUT" and path in self.defer_off and payload.get("on") == {"on": False}:
            self.calls.append((path, copy.deepcopy(payload)))
            return []
        return copy.deepcopy(super().resource(path, method, payload))


class SoloTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "hue_settings.json"
        self.bridge = SoloBridge()
        self.server = hue_web.HueServer(self.bridge, self.path)
        self.server.poll()
        self.api = TestClient(hue_web.app)
        controller = patch.object(hue_web, "controller", self.server)
        controller.start()
        self.addCleanup(controller.stop)
        clock = patch("hue_web.time.monotonic", return_value=500)
        self.monotonic = clock.start()
        self.addCleanup(clock.stop)

    def set_solo(self, enabled):
        return self.api.put("/api/solo", json={"enabled": enabled})

    def switch(self, index, on=True):
        return self.api.post(f"/api/light/light-{index}/switch", json={"on": on})

    def tick(self, advance=0):
        self.monotonic.return_value += advance
        self.server.poll()
        self.server.automate()

    def physical(self, index, on):
        self.bridge.lights[index]["on"]["on"] = on

    def states(self):
        return [item["on"]["on"] for item in self.bridge.lights]

    def power_commands(self):
        return [(path, payload["on"]["on"]) for path, payload in self.bridge.calls if "on" in payload]

    def test_web_switch_keeps_other_lights_in_room_and_persists_solo(self):
        self.assertEqual(self.set_solo("true").status_code, 400)
        self.assertEqual(self.set_solo(True).json()["data"], {"enabled": True})
        self.assertEqual(self.bridge.calls, [])
        self.assertEqual(self.switch(0).status_code, 200)
        self.assertEqual(self.switch(1).status_code, 200)
        self.assertEqual(self.states(), [True, True, False])
        self.tick(2)
        self.tick(15)
        self.assertEqual(self.power_commands(), [
            ("light/light-0", True), ("light/light-2", False), ("light/light-1", True)])
        restored = hue_web.HueServer(self.bridge, self.path)
        restored.poll()
        restored.automate()
        self.assertTrue(restored.state()["solo_enabled"])
        self.assertEqual(self.states(), [True, True, False])
        self.assertEqual(restored.settings["manual_states"]["light-2"]["on"], False)
        self.set_solo(False)
        self.switch(2)
        self.tick(2)
        self.assertEqual(self.states(), [True, True, True])

    def test_zone_command_is_one_interaction_and_keeps_accepted_rooms(self):
        self.set_solo(True)
        request = {"light_ids": ["light-0", "light-1", "light-2"], "on": True}
        response = self.api.post("/api/lights/switch", json=request)
        self.assertEqual(response.json()["data"]["accepted"], request["light_ids"])
        self.tick(2)
        self.assertEqual(self.states(), [True, True, True])
        self.assertTrue(all(on for _, on in self.power_commands()))
        self.bridge.reject.add("light/light-1")
        response = self.api.post("/api/lights/switch", json={**request, "on": False})
        self.assertEqual(response.json()["data"], {
            "accepted": ["light-0", "light-2"], "errors": {"light-1": "Commande refusée"}})

    def test_physical_on_only_once_with_duplicate_reports_and_off_ack(self):
        self.set_solo(True)
        self.physical(0, True)
        self.tick()
        self.assertEqual(self.bridge.calls, [])
        self.tick(1)
        self.tick(1)
        self.tick(15)
        self.assertEqual(self.states(), [True, False, False])
        self.assertEqual(self.power_commands(), [("light/light-2", False)])
        self.physical(1, True)
        self.tick()
        self.tick(1)
        self.assertEqual(self.states(), [True, True, False])
        self.assertEqual(self.power_commands(), [("light/light-2", False)])

    def test_physical_zone_binding_preserves_already_lit_room(self):
        self.bridge.rooms.append({"id": "room-2", "type": "room",
                                  "children": [{"rtype": "device", "rid": "device-1"}]})
        self.bridge.rooms[0]["children"].pop()
        self.physical(1, True)
        self.tick()
        self.set_solo(True)
        event = [{"type": "update", "data": [
            {"id": "button-on", "type": "button", "button": {"last_event": "short_release"}}]}]
        self.server._queue_dimmer_events(self.bridge, event)
        self.server._queue_dimmer_events(self.bridge, event)
        self.physical(0, True)
        self.tick()
        self.tick(1)
        self.tick(1)
        self.assertEqual(self.states(), [True, False, True])
        self.assertEqual(self.power_commands(), [("light/light-1", False)])

    def test_gradation_reconnect_and_orphan_do_not_move(self):
        self.set_solo(True)
        self.bridge.lights[2]["dimming"]["brightness"] = 10
        self.tick(2)
        self.bridge.connectivity[0]["status"] = "connectivity_issue"
        self.tick(2)
        self.physical(0, True)
        self.bridge.connectivity[0]["status"] = "connected"
        self.tick(2)
        self.tick(2)
        self.assertEqual(self.bridge.calls, [])
        self.bridge.rooms[0]["children"].pop()
        self.physical(1, True)
        self.tick()
        self.tick(1)
        self.assertEqual(self.bridge.calls, [])

    def test_accessory_dimming_is_ignored_even_if_bridge_also_powers_on(self):
        self.bridge.accessory["configuration"]["buttons"]["button-on"]["on_short_release"]["action"] = "dim_up"
        self.set_solo(True)
        event = [{"type": "update", "data": [
            {"id": "button-on", "type": "button", "button": {"last_event": "short_release"}}]}]
        self.server._queue_dimmer_events(self.bridge, event)
        self.physical(0, True)
        self.tick()
        self.tick(1)
        self.assertEqual(self.states(), [True, False, True])
        self.assertEqual(self.power_commands(), [])

    def test_pending_off_does_not_repeat_with_a_stale_bridge_snapshot(self):
        self.set_solo(True)
        self.bridge.defer_off.add("light/light-2")
        self.switch(0)
        self.tick()
        self.switch(1)
        self.tick(2)
        self.assertEqual(self.power_commands().count(("light/light-2", False)), 1)
        self.physical(2, False)
        self.tick()
        self.tick(20)
        self.assertEqual(self.power_commands().count(("light/light-2", False)), 1)

    def test_startup_restore_and_vacation_updates_are_not_movements(self):
        self.server.settings["manual_states"]["light-0"]["on"] = True
        self.server.manual_restore_pending.add("light-0")
        self.set_solo(True)
        self.tick()
        self.tick(2)
        self.assertEqual(self.states(), [True, False, True])
        self.assertEqual(self.power_commands(), [("light/light-0", True)])
        self.server.vacation.update(enabled=True, light_ids=["light-0", "light-1"])
        with patch("hue_web.desired_states", return_value={"light-0": True, "light-1": True}):
            self.tick()
            self.tick(2)
        self.assertEqual(self.states(), [True, True, True])
        self.assertEqual(self.power_commands(), [("light/light-0", True), ("light/light-1", True)])

    def test_dawn_can_light_its_lamp_during_solo(self):
        self.set_solo(True)
        self.bridge.lights[0]["color"] = {}
        self.tick()
        with patch("hue_web.time.time", return_value=1_800_000_000):
            self.server.set_dawn({**hue_web.DAWN_DEFAULTS, "enabled": True, "light_id": "light-0"})
            self.server.sync_dawn({"alarm_at": 1_800_000_600_000, "observed_at": 1_800_000_000_000})
            self.tick()
            self.tick(2)
            self.assertEqual(self.states(), [True, False, True])
            self.assertEqual(self.power_commands(), [("light/light-0", True)])
            self.physical(2, False)
            self.tick()
            self.switch(2)
            self.assertEqual(self.states(), [True, False, True])
