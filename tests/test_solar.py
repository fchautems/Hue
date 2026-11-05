import unittest
from math import inf, nan
from datetime import date, datetime
from hue_solar import solar_times


class SolarTests(unittest.TestCase):
    def test_swiss_seasons(self):
        winter = solar_times(date(2026, 12, 21), 46.5, 6.2)
        summer = solar_times(date(2026, 6, 21), 46.5, 6.2)
        self.assertTrue(7 <= winter["sunrise"].hour <= 9)
        self.assertTrue(16 <= winter["sunset"].hour <= 18)
        self.assertTrue(4 <= summer["sunrise"].hour <= 7)
        self.assertTrue(20 <= summer["sunset"].hour <= 22)
        self.assertLess(winter["sunrise"], winter["sunset"])
        self.assertLess(summer["sunrise"], summer["sunset"])

    def test_dst_timezone(self):
        before = solar_times(date(2026, 3, 28), 46.5, 6.2)
        after = solar_times(date(2026, 3, 29), 46.5, 6.2)
        self.assertEqual(before["sunrise"].utcoffset().total_seconds(), 3600)
        self.assertEqual(after["sunrise"].utcoffset().total_seconds(), 7200)

    def test_invalid_nonfinite_coordinates(self):
        for lat, lon in [(nan, 6.2), (46.5, nan), (inf, 6.2), (46.5, -inf), (True, 6.2), (46.5, None), ('46.5', 6.2)]:
            with self.subTest(lat=lat, lon=lon), self.assertRaises(ValueError):
                solar_times(date(2026, 11, 5), lat, lon)

    def test_winter_time_transition(self):
        before = solar_times(date(2026, 10, 24), 46.5, 6.2)
        after = solar_times(date(2026, 10, 25), 46.5, 6.2)
        self.assertEqual(before['sunrise'].utcoffset().total_seconds(), 7200)
        self.assertEqual(after['sunrise'].utcoffset().total_seconds(), 3600)
        for day, result in [(date(2026, 10, 24), before), (date(2026, 10, 25), after)]:
            self.assertEqual(result['sunrise'].date(), day)
            self.assertEqual(result['sunset'].date(), day)
            self.assertLess(result['sunrise'], result['sunset'])

    def test_polar_and_invalid(self):
        result = solar_times(date(2026, 6, 21), 80, 15)
        self.assertIsNone(result["sunrise"])
        self.assertIsNone(result["sunset"])
        with self.assertRaises(ValueError):
            solar_times(date(2026, 1, 1), 91, 6)
        with self.assertRaises(ValueError):
            solar_times(datetime.now(), 46, 6)


if __name__ == "__main__":
    unittest.main()
