"""Allumage par le plan, le pont natif et les scènes préparées."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from hue_dimmer import dimmer_events
from hue_web import HueServer, START_SCENE_APPDATA
from test_dimmer import AccessoryBridge, ref, update


class SceneBridge(AccessoryBridge):
    def __init__(self):
        super().__init__()
        self.accessories["scene"] = []
        self.lights[0]["color"] = {"xy": {"x": 0.28, "y": 0.29}}
        for light in self.lights:
            light["on"]["on"] = False

    def resource(self, path, method="GET", payload=None):
        scenes = self.accessories["scene"]
        if path == "scene" and method == "POST":
            uid = f"scene-{len(scenes)}"
            scenes.append({"id": uid, **copy.deepcopy(payload)})
            self.calls.append((path, copy.deepcopy(payload)))
            return [ref("scene", uid)]
        if path.startswith("scene/") and method == "PUT":
            self.calls.append((path, copy.deepcopy(payload)))
            next(scene for scene in scenes if scene["id"] == path[6:]).update(copy.deepcopy(payload))
            return []
        result = super().resource(path, method, payload)
        if path.startswith("light/") and method == "PUT" and "color" in payload:
            next(light for light in self.lights if light["id"] == path[6:])["color"].update(payload["color"])
        return copy.deepcopy(result)

    def press(self, uid):
        button = self.accessories["behavior_instance"][0]["configuration"]["buttons"]["power"]
        button["on_short_release"] = {"recall": ref("scene", uid)}
        scene = next(scene for scene in self.accessories["scene"] if scene["id"] == uid)
        for step in scene["actions"]:
            light = next(light for light in self.lights if light["id"] == step["target"]["rid"])
            light.update(copy.deepcopy(step["action"]))
        return update("button", "power", button={"last_event": "short_release"})


class StartSceneTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bridge = SceneBridge()
        self.path = Path(temporary.name) / "settings.json"
        self.server = HueServer(self.bridge, self.path)
        self.server.poll()
        self.server.set_light_mode("light-0", "auto")
        colors = {
            "morning": {"h": 30, "s": 60}, "day": {"h": 40, "s": 0},
            "evening": {"h": 20, "s": 80}, "night": {"h": 15, "s": 95},
        }
        self.server.settings["profile_types"]["light-0"] = "simple"
        self.server.settings["rgb_profiles"]["light-0"] = colors
        self.server.settings["rgb_auto_enabled"]["light-0"] = True
        clock = patch("hue_web.wall_clock_minutes", return_value=720)
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.bridge.accessories["behavior_instance"][0]["configuration"]["buttons"]["power"] = {}

    def test_web_sends_one_complete_command_and_no_followup_transition(self):
        self.server.switch("light-0", True)
        self.server.poll()
        self.server.automate()
        self.assertEqual(len(self.bridge.calls), 1)
        path, command = self.bridge.calls[0]
        self.assertEqual(path, "light/light-0")
        self.assertEqual(command["on"], {"on": True})
        self.assertIn("color", command)
        self.assertEqual(command["dynamics"], {"duration": 0})

    def test_unconfigured_button_corrects_existing_state_without_a_fade_or_second_on(self):
        self.bridge.lights[0]["on"]["on"] = True
        self.server.poll()
        self.server.automate()
        self.assertEqual(len(self.bridge.calls), 1)
        _, command = self.bridge.calls[0]
        self.assertEqual(command["dynamics"]["duration"], 0)
        self.assertNotIn("on", command)
        self.assertIn("color", command)

    def test_managed_scene_applies_profile_directly_and_does_not_hold_auto(self):
        self.server.prepare_start_scene("salon", "room")
        scene = self.bridge.accessories["scene"][0]
        expected = scene["actions"][0]["action"]
        self.assertEqual(scene["metadata"]["appdata"], START_SCENE_APPDATA)
        self.assertFalse(self.bridge.lights[0]["on"]["on"])
        self.server._queue_dimmer_events(self.bridge, self.bridge.press(scene["id"]))
        self.bridge.calls.clear()
        self.server.poll()
        self.server.automate()
        self.server.poll()
        self.server.automate()
        self.assertFalse(self.server.dimmer_held)
        self.assertEqual(self.bridge.calls, [])
        self.assertEqual(self.bridge.lights[0]["dimming"], expected["dimming"])
        self.assertEqual(self.bridge.lights[0]["color"], expected["color"])

    def test_scene_retry_reuses_id_refreshes_only_when_needed_and_survives_restart(self):
        self.server.prepare_start_scene("salon", "room")
        self.server.prepare_start_scene("salon", "room")
        self.server.prepare_start_scene("coin", "zone")
        self.assertEqual([path for path, _ in self.bridge.calls], ["scene", "scene"])
        restored = HueServer(self.bridge, self.path)
        restored.poll()
        self.clock.return_value = 60
        self.bridge.calls.clear()
        restored.automate()
        self.assertEqual([path for path, _ in self.bridge.calls], ["scene/scene-0", "scene/scene-1"])
        for _, payload in self.bridge.calls:
            self.assertEqual(set(payload), {"actions"})
        restored.automate()
        self.assertEqual(len(self.bridge.calls), 2)
        self.assertTrue(all(not light["on"]["on"] for light in self.bridge.lights))

    def test_scene_content_refresh_keeps_queued_button_but_target_change_invalidates_it(self):
        self.server.prepare_start_scene("salon", "room")
        scene = self.bridge.accessories["scene"][0]
        self.server.automate()
        unchanged = update("scene", scene["id"], actions=scene["actions"])
        changed = update("scene", scene["id"], actions=[{"target": ref("light", "light-1")}])
        self.assertEqual(list(dimmer_events(unchanged, self.server._start_scene_targets)), [])
        self.assertEqual(list(dimmer_events(changed, self.server._start_scene_targets)),
                         [("config", scene["id"], "scene")])
