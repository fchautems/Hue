"""Preserve existing controls and APIs while regrouping activity destinations."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import socket
import unittest
from unittest.mock import MagicMock, patch
import requests
import hue_web
from hue_discovery import discover_local_bridges
from test_v061_navigation import NodeParser

ROOT = Path(__file__).resolve().parents[1]


class ErgonomicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = NodeParser()
        cls.parser.feed((ROOT / 'templates/index.html').read_text())

    def test_activity_navigation_and_settings(self):
        nav = [attrs['data-tab'] for tag, attrs, ancestors in self.parser.nodes
               if 'nav-item' in attrs.get('class', '').split()]
        self.assertEqual(nav, ['dashboard', 'profiles', 'presence', 'settings', 'updates'])
        for uid in ('tab-setup', 'tab-diagnostics', 'tab-updates'):
            self.assertIn('tab-settings', self.parser.ids[uid][0][2])

    def test_single_clock_and_existing_capabilities_preserved(self):
        for uid in ('clock-source', 'clock-svg', 'sim-play', 'sim-speed', 'time-slider',
                    'profile-light', 'profile-chart', 'v052-chart', 'v052-save',
                    'save-profile', 'cancel-profile', 'rgb-wheel', 'rgb-save',
                    'solar-save', 'vacation-toggle', 'vacation-test-toggle',
                    'vacation-day-next', 'presence-older', 'export-diag',
                    'refresh-logs', 'setup-pair', 'update-check', 'update-apply'):
            with self.subTest(uid=uid):
                self.assertEqual(len(self.parser.ids[uid]), 1)
        self.assertIn('tab-profiles', self.parser.ids['clock-source'][0][2])
        self.assertIn('tab-diagnostics', self.parser.ids['diag-lights'][0][2])

    def test_ip_is_not_filled_with_a_fictional_discovery(self):
        attrs = self.parser.ids['setup-ip'][0][1]
        self.assertFalse(attrs.get('value'))
        self.assertIn('hidden', self.parser.ids['setup-bridges'][0][1])
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            setup = hue_web.HueOnboarding(path, ROOT / 'hue_config.example.json')
            setup.ensure_config()
            self.assertEqual(setup.public_status()['ip'], '')
            path.write_text(json.dumps({'ip': '10.0.0.12', 'key': 'private'}))
            setup.ensure_config()
            self.assertEqual(json.loads(path.read_text())['key'], 'private')
            self.assertEqual(setup.public_status()['ip'], '10.0.0.12')

    def test_discovery_falls_back_on_empty_invalid_or_failed_cloud(self):
        for payload in ([], {}, requests.ConnectionError('offline')):
            with self.subTest(payload=payload):
                session = MagicMock()
                if isinstance(payload, Exception):
                    session.get.side_effect = payload
                else:
                    session.get.return_value.json.return_value = payload
                setup = hue_web.HueOnboarding(session=session)
                with patch.object(hue_web, 'discover_local_bridges', return_value=['10.0.0.12']) as local:
                    self.assertEqual(setup.discover(), ['10.0.0.12'])
                    local.assert_called_once()

    def test_discovery_does_not_modify_existing_config(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            original = '{"ip":"10.0.0.12","key":"private"}'
            path.write_text(original)
            session = MagicMock()
            session.get.return_value.json.return_value = []
            setup = hue_web.HueOnboarding(path, session=session)
            with patch.object(hue_web, 'discover_local_bridges', return_value=[]):
                self.assertEqual(setup.discover(), [])
            self.assertEqual(path.read_text(), original)

    def test_ssdp_only_offers_private_hue_advertisements_from_sender(self):
        def packet(ip, server='IpBridge/1.70', status='200 OK'):
            return f'HTTP/1.1 {status}\r\nSERVER: {server}\r\nLOCATION: http://{ip}/description.xml\r\n\r\n'.encode()
        sock = MagicMock()
        sock.recvfrom.side_effect = [
            (packet('10.0.0.12', 'Generic printer'), ('10.0.0.12', 1900)),
            (packet('10.0.0.12', status='404 Nope'), ('10.0.0.12', 1900)),
            (packet('not-an-ip'), ('10.0.0.12', 1900)),
            (packet('8.8.8.8'), ('8.8.8.8', 1900)),
            (packet('10.0.0.13'), ('10.0.0.12', 1900)),
            (packet('10.0.0.12'), ('10.0.0.12', 1900)),
            (packet('10.0.0.12'), ('10.0.0.12', 1900)),
            socket.timeout(),
        ]
        context = MagicMock()
        context.__enter__.return_value = sock
        with patch('hue_discovery.socket.socket', return_value=context):
            self.assertEqual(discover_local_bridges(), ['10.0.0.12'])
        self.assertEqual(sock.sendto.call_args[0][1], ('239.255.255.250', 1900))
        with patch('hue_discovery.socket.socket', side_effect=OSError('multicast unavailable')):
            self.assertEqual(discover_local_bridges(), [])
