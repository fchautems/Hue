"""CI-only check. The Raspberry Pi's Python discovery does not require Node.js."""
from datetime import date
import json
import subprocess
from unittest import TestCase

from hue_simple_profile import simple_brightness_at
from hue_solar_profile import DEFAULT_SOLAR_CONFIG, draft_profile


class SolarRhythmParityTests(TestCase):
    def test_browser_brightness_matches_python_every_minute_including_midnight(self):
        configs = [
            dict(DEFAULT_SOLAR_CONFIG, wake=315),
            dict(DEFAULT_SOLAR_CONFIG, wake=10, bed=1200),
            dict(DEFAULT_SOLAR_CONFIG, bed=1430),
        ]
        script = """
            global.window = {};
            require('./static/solar_math.js');
            const profile = JSON.parse(process.argv[1]);
            const levels = Array.from({length: 1441}, (_, minute) =>
                window.HueRhythm.brightness(profile, minute));
            console.log(JSON.stringify(levels));
        """
        for config in configs:
            with self.subTest(wake=config["wake"], bed=config["bed"]):
                profile = draft_profile(date(2026, 11, 6), **config)["params"]
                output = subprocess.check_output(
                    ["node", "-e", script, json.dumps(profile)], text=True, timeout=15,
                )
                expected = [simple_brightness_at(profile, minute) for minute in range(1441)]
                self.assertEqual(json.loads(output), expected)
