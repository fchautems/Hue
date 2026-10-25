"""V0.4 : auth, API, et vérification réelle sur des dépôts Git temporaires."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient
import hue_update_api as update_api
import hue_web


class ApiTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pin_path = Path(self.temp.name) / "pin.json"
        salt = b"0123456789abcdef"
        record = {"salt": salt.hex(), "iterations": 100000,
                  "hash": hashlib.pbkdf2_hmac("sha256", b"hello-12345", salt, 100000).hex()}
        self.pin_path.write_text(json.dumps(record))
        self.api = TestClient(hue_web.app)
        self.addCleanup(self.api.close)
        self.env = patch.object(update_api, "PIN_FILE", self.pin_path)
        self.env.start()
        self.addCleanup(self.env.stop)
        update_api._failures.clear()

    def test_requires_pin_and_fixed_action(self):
        self.assertEqual(self.api.get("/api/update/status").status_code, 200)
        self.assertEqual(self.api.post("/api/update/apply", json={"pin": "bad"}).status_code, 403)
        with patch.object(update_api, "trigger") as trigger:
            result = self.api.post("/api/update/check", json={"pin": "hello-12345"})
            self.assertEqual(result.status_code, 200)
            trigger.assert_called_once_with("check")
        self.assertEqual(self.api.post("/api/update/shutdown", json={"pin": "hello-12345"}).status_code, 400)

    def test_rate_limit(self):
        for _ in range(5):
            self.assertFalse(update_api.authorize_pin("wrong", "local"))
        self.assertFalse(update_api.authorize_pin("hello-12345", "local"))


class WorkerGitTests(TestCase):
    def git(self, *parts, cwd=None):
        return subprocess.run(["git", *parts], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        root = Path(self.t.name)
        self.root = root
        self.remote = root / "remote.git"
        self.source = root / "source"
        self.app = root / "hue-lab"
        self.state = root / "state"
        self.manager = root / "manager"
        self.git("init", "--bare", str(self.remote))
        self.git("init", str(self.source))
        self.git("config", "user.name", "Hue test", cwd=self.source)
        self.git("config", "user.email", "hue@test.invalid", cwd=self.source)
        self.git("checkout", "-b", "main", cwd=self.source)
        (self.source / "requirements.txt").write_text("\n")
        (self.source / "app.py").write_text("print('first')\n")
        (self.source / ".gitignore").write_text(".hue_config.json\nhue_settings.json\n.venv/\n")
        (self.source / "tests").mkdir()
        (self.source / "tests/test_basic.py").write_text("import unittest\nclass T(unittest.TestCase):\n def test_ok(self):\n  self.assertTrue(True)\n")
        (self.source / "updater").mkdir()
        (self.source / "updater/worker.py").write_text("# test worker\n")
        self.git("add", ".", cwd=self.source)
        self.git("commit", "-m", "first", cwd=self.source)
        self.git("remote", "add", "origin", str(self.remote), cwd=self.source)
        self.git("push", "origin", "main", cwd=self.source)
        self.git("clone", "-b", "main", str(self.remote), str(self.app))
        self.original = self.git("rev-parse", "HEAD", cwd=self.app)
        (self.app / ".venv/bin").mkdir(parents=True)
        (self.app / ".venv/bin/python").symlink_to(sys.executable)
        (self.app / ".hue_config.json").write_text('{"secret":"not-on-github"}')
        (self.app / "hue_settings.json").write_text('{"profiles":{"a":10}}')
        (self.source / "app.py").write_text("print('second')\n")
        self.git("add", "app.py", cwd=self.source)
        self.git("commit", "-m", "second", cwd=self.source)
        self.git("push", "origin", "main", cwd=self.source)
        self.latest = self.git("rev-parse", "HEAD", cwd=self.source)
        self.bin = root / "bin"
        self.bin.mkdir()
        systemctl = self.bin / "systemctl"
        systemctl.write_text("#!/bin/sh\nexit 0\n")
        systemctl.chmod(0o755)
        app = self.app
        class API(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = b'{"lights":[]}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args):
                pass
        self.server = HTTPServer(("127.0.0.1", 0), API)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.worker = Path(__file__).resolve().parents[1] / "updater/worker.py"
        self.env = dict(os.environ, HUE_UPDATE_APP_DIR=str(self.app), HUE_UPDATE_STATE_DIR=str(self.state),
                        HUE_UPDATE_MANAGER_DIR=str(self.manager),
                        HUE_UPDATE_HEALTH_URL=f"http://127.0.0.1:{self.server.server_address[1]}/api/state",
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"])

    def run_worker(self, action):
        return subprocess.run([sys.executable, str(self.worker), action], env=self.env, capture_output=True, text=True, timeout=45)

    def test_check_then_apply_preserves_config(self):
        checked = self.run_worker("check")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        status = json.loads((self.state / "status.json").read_text())
        self.assertTrue(status["available"])
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.app), self.original)
        applied = self.run_worker("apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.app), self.latest)
        self.assertIn('not-on-github', (self.app / ".hue_config.json").read_text())
        self.assertIn('"a":10', (self.app / "hue_settings.json").read_text())
        self.assertTrue(list((self.manager / "backups").glob("*/.hue_config.json")))
        self.assertEqual(json.loads((self.state / "status.json").read_text())["phase"], "success")
        self.assertEqual(self.run_worker("apply").returncode, 0)

    def test_rollback_on_failed_restart(self):
        # Le nouveau service échoue au redémarrage, l'ancien doit être relancé.
        fake = self.bin / "systemctl"
        fake.write_text("#!/bin/sh\n"
                        "if [ \"$2\" = \"start\" ] && [ \"$3\" = \"hue-lab.service\" ]; then\n"
                        "  if [ \"$(git -C \"$HUE_UPDATE_APP_DIR\" rev-parse HEAD)\" = \"$HUE_TEST_NEW_SHA\" ]; then exit 1; fi\n"
                        "fi\nexit 0\n")
        fake.chmod(0o755)
        self.env['HUE_TEST_NEW_SHA'] = self.latest
        result = self.run_worker("apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.app), self.original)
        self.assertEqual(json.loads((self.state / "status.json").read_text())["rollback"], True)
        self.assertIn('not-on-github', (self.app / ".hue_config.json").read_text())

    def test_refuses_dirty_tracked_files(self):
        (self.app / "app.py").write_text("changed locally")
        result = self.run_worker("check")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.app), self.original)
