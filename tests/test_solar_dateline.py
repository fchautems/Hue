"""Regression tests for solar events crossing UTC midnight at the dateline."""
import unittest
from datetime import date
from hue_solar import solar_times


class DatelineSolarTests(unittest.TestCase):
    def test_civil_dates_at_dateline(self):
        locations = (
            (1.87, -157.4, "Pacific/Kiritimati"),
            (-14.28, -170.7, "Pacific/Pago_Pago"),
            (35.68, 139.69, "Asia/Tokyo"),
            (46.52, 6.63, "Europe/Zurich"),
        )
        for day in (date(2026, 6, 21), date(2026, 12, 21)):
            for latitude, longitude, zone in locations:
                with self.subTest(day=day, zone=zone):
                    events = solar_times(day, latitude, longitude, zone)
                    for event in ("sunrise", "sunset"):
                        self.assertIsNotNone(events[event])
                        self.assertEqual(events[event].date(), day)
                    self.assertLess(events["sunrise"], events["sunset"])

    def test_year_boundary_keeps_requested_local_day(self):
        """UTC date may be in the previous/next year at the dateline."""
        locations = (
            (1.87, -157.4, "Pacific/Kiritimati"),
            (-14.28, -170.7, "Pacific/Pago_Pago"),
        )
        for day in (
            date(2025, 12, 31), date(2026, 1, 1),
            date(2026, 12, 31), date(2027, 1, 1),
        ):
            for latitude, longitude, zone in locations:
                with self.subTest(day=day, zone=zone):
                    events = solar_times(day, latitude, longitude, zone)
                    for event in ("sunrise", "sunset"):
                        self.assertIsNotNone(events[event])
                        self.assertEqual(events[event].date(), day)
                    self.assertLess(events["sunrise"], events["sunset"])

    def test_dateline_sunrise_sunset_reasonable_clock(self):
        for latitude, longitude, zone in (
            (1.87, -157.4, "Pacific/Kiritimati"),
            (-14.28, -170.7, "Pacific/Pago_Pago"),
        ):
            with self.subTest(zone=zone):
                events = solar_times(date(2026, 6, 21), latitude, longitude, zone)
                self.assertTrue(4 <= events["sunrise"].hour <= 8)
                self.assertTrue(16 <= events["sunset"].hour <= 20)


if __name__ == "__main__":
    unittest.main()
