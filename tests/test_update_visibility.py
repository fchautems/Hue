"""Read-only revision, release notes and update changelog regression tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hue_update_api


class UpdateVisibilityTests(unittest.TestCase):
    def test_local_revision_and_detached_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git/refs/heads").mkdir(parents=True)
            (root / ".git/HEAD").write_text("ref: refs/heads/main\n")
            expected = "0123456789abcdef0123456789abcdef01234567"
            (root / ".git/refs/heads/main").write_text(expected + "\n")
            with patch.object(hue_update_api, "ROOT", root):
                self.assertEqual(hue_update_api.local_revision(), expected[:12])
                (root / ".git/HEAD").write_text(expected + "\n")
                self.assertEqual(hue_update_api.local_revision(), expected[:12])

    def test_revision_works_without_git_and_rejects_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(hue_update_api, "ROOT", root):
                self.assertIsNone(hue_update_api.local_revision())
                (root / ".git").mkdir()
                (root / ".git/HEAD").write_text("not a sha\n")
                self.assertIsNone(hue_update_api.local_revision())

    def test_api_shows_current_revision_and_changelog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "status.json"
            state.write_text('{"installed":"old","remote":"new","available":true,'
                             '"changes":["Interface améliorée"],"change_kind":"interface"}')
            (root / "RELEASE_LOG.md").write_text(
                "# Journal\n\n## Nouveau cycle\n\n- **Code concret :** affichage revu.\n")
            with (patch.object(hue_update_api, "ROOT", root),
                  patch.object(hue_update_api, "STATUS_FILE", state),
                  patch.object(hue_update_api, "worker_installed", return_value=True),
                  patch.object(hue_update_api, "local_revision", return_value="0123456789ab")):
                status = hue_update_api.status()
            self.assertEqual(status["installed"], "0123456789ab")
            self.assertEqual(status["changes"], ["Interface améliorée"])
            self.assertEqual(status["change_kind"], "interface")
            self.assertEqual(status["latest_note"], "affichage revu.")

    def test_cache_buster_bound_to_revision_on_all_assets(self):
        import re
        template = (Path(__file__).resolve().parents[1] / "templates/index.html").read_text()
        assets = re.findall(r'(?:href|src)="(/static/[^"]+)"', template)
        self.assertGreaterEqual(len(assets), 10)
        self.assertTrue(all("?rev={{ asset_rev }}" in asset for asset in assets))
        self.assertIn('id="update-changes-title"', template)
        self.assertIn('id="brand-version"', template)

    @unittest.skipIf(__import__("sys").platform == "win32", "Linux updater only")
    def test_updater_summarizes_internal_and_interface_commits(self):
        from updater import worker

        def fake_git(*args, **kwargs):
            if args[0] == "log":
                return "Correction des tests\n"
            if args[0] == "diff":
                return "tests/test_solar.py\nPROJECT_STATE.md"
            raise AssertionError(args)

        with patch.object(worker, "git", side_effect=fake_git):
            notes, kind = worker.update_changes("a" * 40, "b" * 40)
            self.assertEqual(notes, ["Correction des tests"])
            self.assertEqual(kind, "internal")
        with patch.object(worker, "git", side_effect=lambda *args, **kwargs:
                          "Nouveau bouton" if args[0] == "log" else "templates/index.html"):
            notes, kind = worker.update_changes("a" * 40, "b" * 40)
            self.assertEqual(kind, "interface")
            self.assertEqual(notes, ["Nouveau bouton"])
        self.assertEqual(worker.update_changes("abc", "abc"), ([], "none"))


if __name__ == "__main__":
    unittest.main()
