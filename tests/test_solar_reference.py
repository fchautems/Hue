"""Coarse independent civil-time checks for Swiss solar previews.

Reference times are rounded approximate Lausanne values (not ephemeris-grade).
The 20-minute tolerance deliberately checks gross UTC/DST/date mistakes only.
"""
import unittest
from datetime import date
from hue_solar import solar_times


class SwissSolarReferenceTests(unittest.TestCase):
    def test_lausanne_solstice_reference_local_clock(self):
        # Approximate observed sunrise/sunset in Lausanne, Switzerland.
        cases = (
            (date(2026, 6, 21), (5, 40), (21, 30), 7200),
            (date(2026, 12, 21), (8, 15), (16, 49), 3600),
        )
        for day, rise, set_, offset in cases:
            with self.subTest(day=day):
                events = solar_times(day, 46.52, 6.63)
                for key, expected in (("sunrise", rise), ("sunset", set_)):
                    actual = events[key]
                    self.assertEqual(actual.date(), day)
                    self.assertEqual(actual.utcoffset().total_seconds(), offset)
                    minutes = actual.hour * 60 + actual.minute
                    reference = expected[0] * 60 + expected[1]
                    self.assertLessEqual(abs(minutes - reference), 20)

    def test_nyon_solar_order_and_local_date(self):
        for day in (date(2026, 3, 29), date(2026, 10, 25)):
            with self.subTest(day=day):
                events = solar_times(day, 46.38, 6.24)
                self.assertEqual(events["sunrise"].date(), day)
                self.assertEqual(events["sunset"].date(), day)
                self.assertLess(events["sunrise"], events["sunset"])


if __name__ == "__main__":
    unittest.main()
