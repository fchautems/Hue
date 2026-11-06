"""Solar API remains offline, read-only and independent of Hue setup."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import hue_web


class SolarPreviewTests(unittest.TestCase):
    def setUp(self):
        self.http = TestClient(hue_web.app)

    def test_local_hours_seasons_and_dst(self):
        for day, offset in [('2026-01-15', '+01:00'), ('2026-06-21', '+02:00'),
                            ('2026-03-29', '+02:00'), ('2026-10-25', '+01:00')]:
            with self.subTest(day=day):
                response = self.http.get('/api/solar/preview', params={'day': day})
                self.assertEqual(response.status_code, 200)
                data = response.json()['data']
                self.assertTrue(data['sunrise'].startswith(day))
                self.assertTrue(data['sunrise'].endswith(offset))
                self.assertLess(data['sunrise_minute'], data['sunset_minute'])
                self.assertGreater(data['daylight_minutes'], 0)

    def test_invalid_inputs(self):
        for params in [{'day': '2026-02-30'}, {'tz': 'No/SuchZone'},
                       {'latitude': 'nan'}, {'longitude': 'inf'},
                       {'latitude': 91}, {'longitude': -181}, {'latitude': 'abc'}]:
            with self.subTest(params=params):
                self.assertIn(self.http.get('/api/solar/preview', params=params).status_code, [400, 422])

    def test_offline_without_controller_or_settings(self):
        with (patch.object(hue_web, 'controller', None),
              patch.object(hue_web.requests.Session, 'request', side_effect=AssertionError('network')),
              patch.object(hue_web.Path, 'write_text', side_effect=AssertionError('settings write'))):
            response = self.http.get('/api/solar/preview', params={'day': '2026-11-06'})
            self.assertEqual(response.status_code, 200)

    def test_today_uses_requested_timezone(self):
        from datetime import datetime, timezone
        fixed = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        with patch.object(hue_web, 'datetime') as clock:
            clock.now.side_effect = lambda zone: fixed.astimezone(zone)
            data = self.http.get('/api/solar/preview', params={'tz': 'Pacific/Kiritimati',
                                  'latitude': 1.87, 'longitude': -157.4}).json()['data']
        self.assertEqual(data['day'], '2026-01-02')
        self.assertTrue(data['sunrise'].startswith('2026-01-02'))

    def test_polar_day_does_not_fail(self):
        data = self.http.get('/api/solar/preview', params={'day': '2026-06-21',
                             'latitude': 78.22, 'longitude': 15.65, 'tz': 'Arctic/Longyearbyen'}).json()['data']
        self.assertIsNone(data['sunrise'])
        self.assertIsNone(data['daylight_minutes'])
