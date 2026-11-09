"""Télécommandes Hue via le flux d'événements et la boucle d'automatisation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from hue_web import HueServer
from test_v05 import ThreeLamps


def ref(kind, uid):
    return {"rtype": kind, "rid": uid}


def update(kind, uid, **data):
    return [{"type": "update", "data": [{"type": kind, "id": uid, **data}]}]


class AccessoryBridge(ThreeLamps):
    def __init__(self):
        super().__init__()
        salon = [{"group": ref("room", "salon")}]
        zone = [{"group": ref("zone", "coin"), "items": [ref("device", "device-1")]}]
        self.accessories = {
            "behavior_instance": [{"enabled": True, "configuration": {
                "buttons": {
                    "down": {"where": salon, "on_repeat": {"action": "dim_down"}},
                    "up": {"where": salon, "on_repeat": {"action": "dim_up"}},
                    "scene": {"where": salon, "on_short_release": {"scene_cycle": {}}},
                },
                "rotaries": {"dial": {"where": zone}},
            }}],
            "room": [{"id": "salon", "children": [ref("device", "device-0")]}],
            "zone": [{"id": "coin", "children": [ref("device", "device-0"), ref("device", "device-1")]}],
            "bridge_home": [],
        }

    def resource(self, path, method="GET", payload=None):
        if method == "GET" and path in self.accessories:
            return self.accessories[path]
        return super().resource(path, method, payload)


class DimmerTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.settings = Path(temporary.name) / "settings.json"
        self.bridge = AccessoryBridge()
        self.server = HueServer(self.bridge, self.settings)
        self.server.poll()
        for uid in ("light-0", "light-1"):
            self.server.set_light_mode(uid, "auto")
        self.server.set_clock_mode("accelere")
        self.server.set_sim({"running": False, "minute": 720})

    def deliver(self, batch):
        self.server._queue_dimmer_events(self.bridge, batch)
        self.server.poll()
        self.server.automate()

    def button(self, uid, event="initial_press"):
        self.deliver(update("button", uid, button={"button_report": {"event": event}}))

    def test_dimmer_suspends_only_its_room_and_resumes_on_next_on(self):
        self.bridge.lights[0]["dimming"]["brightness"] = 24
        self.button("down")
        self.assertEqual(self.server.dimmer_held, {"light-0"})
        self.assertEqual([path for path, _ in self.bridge.calls], ["light/light-1"])
        self.assertTrue(self.server.get_lights()[0]["manual_override"])
        self.bridge.calls.clear()
        self.bridge.lights[0]["on"]["on"] = False
        self.deliver(update("light", "light-0", on={"on": False}))
        self.assertEqual(self.bridge.calls, [])
        self.bridge.lights[0]["on"]["on"] = True
        self.deliver(update("light", "light-0", on={"on": True}))
        self.assertEqual(self.bridge.calls[-1][1]["dimming"]["brightness"], 100)
        self.assertEqual(self.server.get_lights()[0]["control_mode"], "auto")
        self.assertFalse(self.server.get_lights()[0]["manual_override"])

    def test_rotary_targets_only_configured_items_and_survives_restart(self):
        self.deliver(update("relative_rotary", "dial", relative_rotary={
            "rotary_report": {"action": "start", "rotation": {"steps": 16}},
        }))
        self.assertEqual(self.server.dimmer_held, {"light-1"})
        self.server = HueServer(self.bridge, self.settings)
        self.server.poll()
        self.assertTrue(self.server.get_lights()[1]["manual_override"])
        self.server.set_light_mode("light-1", "auto")
        self.assertFalse(self.server.get_lights()[1]["manual_override"])

    def test_off_on_between_two_polls_and_permanent_manual(self):
        self.server.set_light_mode("light-1", "manuel")
        self.button("up", "repeat")
        self.assertEqual(self.server.dimmer_held, {"light-0"})
        self.deliver(update("light", "light-0", on={"on": False}) +
                     update("light", "light-0", on={"on": True}))
        self.assertFalse(self.server.dimmer_held)
        self.assertEqual(self.server.get_lights()[1]["control_mode"], "manuel")

    def test_scene_unresolved_dial_and_vacations_leave_auto_unchanged(self):
        self.button("scene", "short_release")
        self.deliver(update("relative_rotary", "unmapped", relative_rotary={
            "rotary_report": {"action": "start", "rotation": {"steps": 5}},
        }))
        self.assertFalse(self.server.dimmer_held)
        self.server.set_clock_mode("reel")
        self.server.set_vacation(True, ["light-0"])
        self.button("down")
        self.assertFalse(self.server.dimmer_held)
