"""Télécommandes Hue via le flux d'événements et la boucle d'automatisation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from hue_web import HueError, HueServer
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
        if method == "GET" and path == "":
            return [dict(item, type=kind) for kind, items in self.accessories.items() for item in items]
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

    def reassign(self):
        down = self.bridge.accessories["behavior_instance"][0]["configuration"]["buttons"]["down"]
        down["where"] = [{"group": ref("zone", "coin"), "items": [ref("light", "light-1")]}]

    def test_next_press_uses_reassignment_even_without_config_notification(self):
        self.button("down")
        self.assertEqual(self.server.dimmer_held, {"light-0"})
        self.deliver(update("light", "light-0", on={"on": False}))
        self.reassign()
        self.button("down")
        self.assertEqual(self.server.dimmer_held, {"light-1"})

    def test_old_press_does_not_cross_a_config_update(self):
        press = update("button", "down", button={"button_report": {"event": "initial_press"}})
        self.reassign()
        self.deliver(press + update("behavior_instance", "switch-config"))
        self.assertFalse(self.server.dimmer_held)
        self.button("down")
        self.assertEqual(self.server.dimmer_held, {"light-1"})

    def test_config_change_during_read_drops_only_superseded_presses(self):
        resource = self.bridge.resource
        press = update("button", "down", button={"button_report": {"event": "initial_press"}})

        def change_during_read(path, method="GET", payload=None):
            if path in ("", "behavior_instance"):
                self.bridge.resource = resource
                self.reassign()
                self.server._queue_dimmer_events(self.bridge, update("behavior_instance", "switch-config") + press)
            return resource(path, method, payload)

        self.bridge.resource = change_during_read
        self.button("down")
        self.assertFalse(self.server.dimmer_held)
        self.server.automate()
        self.assertEqual(self.server.dimmer_held, {"light-1"})

    def test_configured_scene_holds_only_its_lamps_and_power_buttons_are_ignored(self):
        buttons = self.bridge.accessories["behavior_instance"][0]["configuration"]["buttons"]
        slot = [{"action": {"recall": ref("scene", "lecture")}}]
        buttons["scene"]["where"] = [{"group": ref("zone", "coin")}]
        buttons["scene"]["on_short_release"] = {"scene_cycle_extended": {"slots": [slot]}}
        buttons["power"] = {"where": buttons["scene"]["where"], "on_short_release": {
            "time_based_extended": {"slots": [{"actions": slot}], "with_off": {"enabled": True}},
        }}
        self.bridge.accessories["scene"] = [{"id": "lecture", "actions": [
            {"target": ref("light", "light-1"), "action": {"dimming": {"brightness": 28}}},
        ]}]
        self.button("power", "short_release")
        self.assertFalse(self.server.dimmer_held)
        self.button("scene", "short_release")
        self.assertEqual(self.server.dimmer_held, {"light-1"})

    def test_group_membership_changes_and_empty_items_never_select_the_whole_group(self):
        self.button("down")
        self.assertEqual(self.server.dimmer_held, {"light-0"})
        self.deliver(update("light", "light-0", on={"on": False}))
        room = self.bridge.accessories["room"][0]
        room["children"] = [ref("device", "device-1"), ref("device", "device-2")]
        self.server.set_light_mode("light-2", "auto")
        self.button("down")
        self.assertEqual(self.server.dimmer_held, {"light-1", "light-2"})
        self.deliver(update("light", "light-1", on={"on": False}) +
                     update("light", "light-2", on={"on": False}))
        down = self.bridge.accessories["behavior_instance"][0]["configuration"]["buttons"]["down"]
        down["where"][0]["items"] = []
        self.button("down")
        self.assertFalse(self.server.dimmer_held)

    def test_failed_config_read_never_reuses_old_targets_and_next_press_recovers(self):
        self.button("down")
        self.deliver(update("light", "light-0", on={"on": False}))
        self.reassign()
        resource = self.bridge.resource

        def unavailable(path, method="GET", payload=None):
            if path == "":
                raise HueError("lecture indisponible")
            return resource(path, method, payload)

        self.bridge.resource = unavailable
        self.button("down")
        self.assertFalse(self.server.dimmer_held)
        self.bridge.resource = resource
        self.button("down")
        self.assertEqual(self.server.dimmer_held, {"light-1"})

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
