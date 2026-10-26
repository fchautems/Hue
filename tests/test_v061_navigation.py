"""v0.6.1 — vérification de la fusion de navigation et de l'horloge conservée."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NodeParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.nodes = []
        self.ids = {}
        self.nav = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = (tag, attrs)
        ancestors = [item[1].get("id") for item in self.stack]
        self.nodes.append((tag, attrs, ancestors))
        if attrs.get("id"):
            self.ids.setdefault(attrs["id"], []).append((tag, attrs, ancestors))
        if "data-tab" in attrs:
            self.nav.append(attrs["data-tab"])
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for ix in range(len(self.stack) - 1, -1, -1):
            if self.stack[ix][0] == tag:
                del self.stack[ix:]
                return


class UnifiedInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "static" / "v061.css").read_text(encoding="utf-8")
        cls.ui = (ROOT / "static" / "v061.js").read_text(encoding="utf-8")
        cls.rgb_ui = (ROOT / "static" / "v06.js").read_text(encoding="utf-8")
        cls.parser = NodeParser()
        cls.parser.feed(cls.template)

    def test_a_single_combined_navigation_entry(self):
        self.assertEqual(self.parser.nav.count("profiles"), 1)
        self.assertEqual(self.parser.nav.count("colors"), 0)
        self.assertIn("Horloge & lumières", self.template)

    def test_clock_is_preserved_and_rgb_nested_in_same_tab(self):
        p = self.parser
        self.assertEqual(len(p.ids["clock-svg"]), 1)
        self.assertEqual(len(p.ids["v051-simulator"]), 1)
        self.assertEqual(len(p.ids["rgb-wheel"]), 1)
        self.assertIn("tab-profiles", p.ids["tab-colors"][0][2])
        self.assertNotIn("tab", p.ids["tab-colors"][0][1].get("class", "").split())
        self.assertIn("tab-profiles", p.ids["v061-advanced"][0][2])

    def test_common_lamp_selector_and_advanced_editor(self):
        p = self.parser
        self.assertEqual(len(p.ids["profile-light"]), 1)
        self.assertIn("tab-profiles", p.ids["profile-light"][0][2])
        self.assertIn("v061-advanced", p.ids["point-rows"][0][2])
        self.assertIn("v061-advanced", p.ids["v052-simple-editor"][0][2])
        self.assertEqual(p.ids["v061-advanced"][0][0], "details")
        self.assertIn("#tab-profiles #tab-colors .rgb-lamp-row{display:none", self.css)

    def test_clock_not_hidden_on_mobile(self):
        self.assertIn("#tab-profiles .two-col.top-section{display:grid!important", self.css)
        self.assertIn("#tab-profiles #v061-sim-options{display:none}", self.css)
        self.assertIn("body.v051-show-simulator #tab-profiles #v061-sim-options{display:block}", self.css)

    def test_preserves_unsaved_changes_and_navigation(self):
        self.assertIn("window.HueRGB?.hasChanges()", self.ui)
        self.assertIn("event.stopImmediatePropagation()", self.ui)
        self.assertIn("window.HueRGB?.open(selectedId, true)", self.ui)
        self.assertIn("window.HueProfiles?.hasUnsaved()", self.ui)
        self.assertIn("activeTab==='profiles'&&tab!=='profiles'&&hasChanges()", self.rgb_ui)
        self.assertIn("draft=clone(saved.data);render()", self.rgb_ui)

    def test_script_order(self):
        self.assertLess(self.template.index('src="/static/v052.js'), self.template.index('src="/static/v06.js'))
        self.assertLess(self.template.index('src="/static/v06.js'), self.template.index('src="/static/v061.js'))

    def test_existing_clock_and_simulation_ids_unchanged(self):
        for name in ["clock-mode", "clock-ticks", "hour-hand", "minute-hand",
                     "clock-digital", "time-slider", "sim-play", "sim-speed", "clock-source"]:
            with self.subTest(name=name):
                self.assertEqual(len(self.parser.ids[name]), 1)


if __name__ == "__main__":
    unittest.main()
