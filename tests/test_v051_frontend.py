"""Vérifications sans navigateur, sûres sur le Raspberry Pi et exécutables en staging."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MobileErgonomicsTests(unittest.TestCase):
    def test_resources_are_loaded_in_right_order(self):
        html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
        self.assertIn('/static/v051.css', html)
        self.assertIn('/static/v051.js', html)
        self.assertLess(html.index('/static/v05.css'), html.index('/static/v051.css'))
        self.assertLess(html.index('/static/app.js'), html.index('/static/v051.js'))

    def test_explicit_save_and_cancel_are_available(self):
        html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
        self.assertIn('id="profile-edit-status"', html)
        self.assertIn('id="cancel-profile"', html)
        self.assertIn('id="save-profile"', html)
        self.assertIn('id="v051-simulation-toggle"', html)

    def test_curve_editor_does_not_touch_lamp_controls(self):
        source = (ROOT / "static/v051.js").read_text(encoding="utf-8")
        self.assertIn("/api/profile/", source)
        self.assertIn("if (!profileDirty", source)
        self.assertNotIn("/api/light/", source)
        self.assertNotIn("/api/clock-mode", source)
        self.assertIn("/api/profile/${encodeURIComponent(selectedId)}`,'PUT'", source)

    def test_mobile_is_styled_for_touch_and_scrolling(self):
        css = (ROOT / "static/v051.css").read_text(encoding="utf-8")
        self.assertIn("touch-action:none", css)
        self.assertIn("@media(max-width:700px)", css)
        self.assertIn(".v051-point-list", css)
        self.assertIn(".profile-actions", css)


if __name__ == "__main__":
    unittest.main()
