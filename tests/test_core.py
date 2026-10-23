import unittest
from hue_core import brightness_at, validate_points, simulated_minutes


class ProfileTests(unittest.TestCase):
    def test_midpoint_smooth(self):
        p = [{"minute": 0, "brightness": 20}, {"minute": 720, "brightness": 80}]
        self.assertEqual(brightness_at(p, 360), 50)
        self.assertEqual(brightness_at(p, 1080), 50)
        self.assertEqual(brightness_at(p, 1440), 20)

    def test_continuity_at_midnight(self):
        p = [{"minute": 120, "brightness": 20}, {"minute": 600, "brightness": 80}]
        self.assertAlmostEqual(brightness_at(p, 0), brightness_at(p, 1440), places=7)
        self.assertAlmostEqual(brightness_at(p, 1439.9), brightness_at(p, 0), delta=0.1)

    def test_continuity_around_knot(self):
        p = [{"minute": 0, "brightness": 5}, {"minute": 300, "brightness": 90}, {"minute": 900, "brightness": 20}]
        self.assertAlmostEqual(brightness_at(p, 299.99), brightness_at(p, 300.01), delta=0.001)

    def test_validation(self):
        bad = [
            [{"minute": 0, "brightness": 0}, {"minute": 200, "brightness": 20}],
            [{"minute": 0, "brightness": 10}, {"minute": 0, "brightness": 20}],
            [{"minute": 0, "brightness": 10}],
            [{"minute": "12:00", "brightness": 10}, {"minute": 500, "brightness": 20}],
        ]
        for p in bad:
            with self.subTest(p=p), self.assertRaises(ValueError):
                validate_points(p)

    def test_simulation_virtual_time(self):
        sim = {"enabled": True, "running": True, "seconds_per_day": 60, "minute": 600, "started_at": 100.0}
        self.assertEqual(simulated_minutes(sim, 115.0), 960)
        self.assertEqual(simulated_minutes(sim, 135.0), 0)
        sim["running"] = False
        self.assertEqual(simulated_minutes(sim, 115.0), 600)


if __name__ == "__main__":
    unittest.main()
