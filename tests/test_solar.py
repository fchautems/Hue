import unittest
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
