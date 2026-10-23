import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

import hue_web


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")
    def json(self):
        return self.payload


class Session:
    def __init__(self):
        self.discovered = []
        self.pair_response = [{"error": {"type": 101, "description": "link button not pressed"}}]
        self.posts = []
    def get(self, url, timeout):
        assert url == "https://discovery.meethue.com/"
        return Response(self.discovered)
    def post(self, url, json, verify, timeout):
        assert verify is False
        assert json == {"devicetype": "hue_lab#pc"}
        self.posts.append(url)
        return Response(self.pair_response)


class OnboardingTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".hue_config.json"
        self.example = Path(self.tmp.name) / "hue_config.example.json"
        self.example.write_text('{"ip":"10.0.0.2","key":""}', encoding="utf-8")
        self.session = Session()
        self.setup = hue_web.HueOnboarding(self.path, self.example, self.session)
    def tearDown(self):
        self.tmp.cleanup()

    def test_config_is_created_without_secret(self):
        self.setup.ensure_config()
        self.assertTrue(self.path.is_file())
        self.assertEqual(json.loads(self.path.read_text()), {"ip": "10.0.0.2", "key": ""})
        self.assertEqual(self.setup.public_status(), {"ip": "10.0.0.2", "paired": False, "config_exists": True})
        self.setup.ensure_config()  # ne pas écraser une config existante

    def test_discovery_ignores_duplicate_and_public_ip(self):
        self.session.discovered = [
            {"internalipaddress": "10.0.0.2"},
            {"internalipaddress": "10.0.0.2"},
            {"internalipaddress": "8.8.8.8"},
            {"internalipaddress": "192.168.1.25"},
        ]
        self.assertEqual(self.setup.discover(), ["10.0.0.2", "192.168.1.25"])

    def test_pair_pending_does_not_save_fake_key(self):
        self.setup.ensure_config()
        result = self.setup.pair_once("10.0.0.2")
        self.assertEqual(result, {"paired": False, "waiting_for_button": True, "ip": "10.0.0.2"})
        self.assertEqual(json.loads(self.path.read_text())["key"], "")

    def test_pair_success_verifies_and_saves_and_updates_server(self):
        self.session.pair_response = [{"success": {"username": "true-key"}}]
        with patch.object(hue_web.HueClient, "resource", side_effect=lambda path, *a, **kw: [{"id": "l1", "owner": {"rid": "d1"}, "on": {"on": True}}] if path == "light" else []):
            with patch.object(hue_web, "controller", hue_web.HueServer(logger_=logging.getLogger("test")) ) as server:
                result = self.setup.pair_once("10.0.0.2")
                self.assertTrue(result["paired"])
                self.assertEqual(result["lights"], 1)
                self.assertIsNotNone(server.client)
                self.assertEqual(server.client.ip, "10.0.0.2")
                self.assertEqual(server.state()["needs_setup"], False)
        self.assertEqual(json.loads(self.path.read_text()), {"ip": "10.0.0.2", "key": "true-key"})
        self.assertNotIn("true-key", str(self.setup.public_status()))

    def test_invalid_key_is_not_persisted(self):
        self.session.pair_response = [{"success": {"username": "wrong"}}]
        with patch.object(hue_web.HueClient, "resource", side_effect=hue_web.HueError("API refusée")):
            with self.assertRaises(hue_web.HueError):
                self.setup.pair_once("10.0.0.2")
        self.assertFalse(self.path.exists())

    def test_invalid_ip_never_sends_request(self):
        for ip in ["127.0.0.1", "8.8.8.8", "192.168.1.2:9999", "localhost", "http://10.0.0.2", "169.254.1.1"]:
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                self.setup.pair_once(ip)
        self.assertEqual(self.session.posts, [])

    def test_http_endpoints_no_key_exposed(self):
        with patch.object(hue_web, "setup", self.setup):
            self.setup.ensure_config()
            app = TestClient(hue_web.app)
            self.session.discovered = [{"internalipaddress": "10.0.0.2"}]
            status = app.get("/api/setup/status")
            self.assertEqual(status.status_code, 200)
            self.assertFalse(status.json()["data"]["paired"])
            self.assertNotIn("key", str(status.json()))
            self.assertEqual(app.get("/api/setup/discover").json()["data"]["bridges"], ["10.0.0.2"])
            self.assertTrue(app.post("/api/setup/pair", json={"ip": "10.0.0.2"}).json()["data"]["waiting_for_button"])
            self.assertEqual(app.post("/api/setup/pair", json={"ip": "127.0.0.1"}).status_code, 400)
            self.assertEqual(app.get("/").status_code, 200)
            self.assertIn("Démarrer l'association", app.get("/").text)
