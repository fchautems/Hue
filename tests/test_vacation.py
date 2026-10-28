"""Scénarios hors réseau du simulateur de présence et priorité télécommande."""
import csv
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import hue_web
from hue_web import HueServer
from hue_vacation import LOCAL_TZ, GRACE_SECONDS, build_schedule, desired_states, past_sessions
from test_v05 import ThreeLamps


class VacationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bridge = ThreeLamps()
        self.srv = HueServer(self.bridge, self.root / "settings.json",
                             logging.getLogger("test_vacation"))
        self.srv.poll()

    def test_fallback_is_stable_and_distinct_by_day(self):
        when = datetime(2026, 10, 30, 12, tzinfo=LOCAL_TZ)
        a = build_schedule(["light-1", "light-2"], self.root / "missing.csv", "seed", when)
        b = build_schedule(["light-1", "light-2"], self.root / "missing.csv", "seed", when)
        self.assertEqual(a, b)
        self.assertTrue(a)
        self.assertEqual(a, sorted(a, key=lambda e:(e["at"], e["light_id"], not e["on"])))
        self.assertEqual({x["light_id"] for x in a}, {"light-1", "light-2"})
        self.assertNotEqual(a[0]["at"][:10], a[-1]["at"][:10])
        self.assertTrue(all(x["on"] in (True, False) for x in a))

    def test_history_influences_evening_and_excludes_zigbee(self):
        f = self.root / "events.csv"
        rows = [
            ["2026-10-26T21:10:00+01:00","light-1","Salon","light_on"],
            ["2026-10-26T22:40:00+01:00","light-1","Salon","light_off"],
            ["2026-10-27T21:20:00+01:00","light-1","Salon","light_on"],
            ["2026-10-27T22:50:00+01:00","light-1","Salon","light_off"],
            ["2026-10-27T23:00:00+01:00","light-1","Salon","zigbee_disconnected"]]
        with f.open("w", newline="",encoding="utf-8") as out:
            w = csv.writer(out, delimiter=";")
            w.writerow(["detected_at", "light_id", "light_name", "event"])
            w.writerows(rows)
        self.assertEqual(len(past_sessions(f, {"light-1"})["light-1"]), 2)
        when = datetime(2026, 10, 30, 12, tzinfo=LOCAL_TZ)
        with_logs = build_schedule(["light-1"], f, "seed", when, days=1)
        without = build_schedule(["light-1"], self.root / "missing", "seed", when, days=1)
        self.assertNotEqual(with_logs, without)
        self.assertTrue(any(e["on"] and int(e["at"][11:13]) >= 20 for e in with_logs))

    def test_enable_issues_commands_and_disable_stops(self):
        self.srv.set_vacation(True, ["light-1"])
        self.assertEqual(self.srv.vacation_state()["light_ids"], ["light-1"])
        self.srv._automate_locked = lambda: None  # Les autres courbes sont isolées de ce test.
        now = datetime.now(LOCAL_TZ)
        self.srv.vacation["schedule"] = [
            {"at": (now-timedelta(minutes=3)).isoformat(), "light_id":"light-1","on":True},
            {"at": (now+timedelta(minutes=30)).isoformat(), "light_id":"light-1","on":False}]
        self.bridge.lights[1]["on"] = {"on":False}
        self.srv.poll()
        self.srv.vacation["overrides"].clear()  # Préparer un état OFF sans commande manuelle active.
        self.bridge.calls.clear()
        self.srv.automate()
        self.assertEqual(self.bridge.calls[-1][0], "light/light-1")
        self.assertTrue(self.bridge.calls[-1][1]["on"]["on"])
        self.assertEqual(self.srv.settings["light_modes"]["light-1"],"manuel")
        self.srv.set_vacation(False)
        self.bridge.calls.clear()
        self.srv.automate()
        self.assertEqual(self.bridge.calls, [])

    def test_external_hue_on_gets_ten_minutes_then_resumes(self):
        self.srv.set_vacation(True, ["light-1"])
        now = datetime.now(LOCAL_TZ)
        self.srv.vacation["schedule"] = [
            {"at": (now-timedelta(hours=2)).isoformat(), "light_id":"light-1","on":False}]
        self.srv.save()
        self.bridge.lights[1]["on"] = {"on":False}
        self.srv.poll()
        self.bridge.calls.clear()
        self.bridge.lights[1]["on"] = {"on":True}  # Le pont a reçu une commande d'un bouton Hue.
        self.srv.poll()
        override = self.srv.vacation["overrides"]["light-1"]
        self.assertTrue(override["on"])
        self.assertGreater(override["until"], time.time() + GRACE_SECONDS - 4)
        self.srv.automate()
        self.assertFalse(any(x[0]=="light/light-1" and x[1].get("on",{}).get("on") is False
                             for x in self.bridge.calls))
        # Redémarrage du serveur : priorité conservée.
        restarted = HueServer(self.bridge, self.root / "settings.json",
                              logging.getLogger("test_vacation_restart"))
        restarted.poll()
        self.assertTrue(restarted.vacation["enabled"])
        self.assertIn("light-1", restarted.vacation["overrides"])
        restarted.vacation["overrides"]["light-1"]["until"] = time.time() - 1
        restarted.automate()
        self.assertTrue(any(x[0]=="light/light-1" and x[1].get("on",{}).get("on") is False
                            for x in self.bridge.calls))

    def test_our_vacation_commands_do_not_create_false_habits(self):
        self.srv.set_vacation(True, ["light-1"])
        now = datetime.now(LOCAL_TZ)
        self.srv.vacation["schedule"] = [
            {"at": (now-timedelta(minutes=2)).isoformat(), "light_id":"light-1","on":False}]
        self.srv.automate()
        self.srv.poll()
        self.assertFalse((self.root/"logs"/"presence_events.csv").exists())
        self.assertNotIn("light-1", self.srv.vacation["overrides"])

    def test_legacy_modes_and_settings_survive(self):
        self.srv.set_light_mode("light-2","auto")
        self.srv.set_vacation(True, ["light-1"])
        self.assertEqual(self.srv.settings["light_modes"]["light-2"],"auto")
        self.assertEqual(self.srv.settings["light_modes"]["light-1"],"manuel")
        restored = HueServer(self.bridge, self.root/"settings.json", logging.getLogger("test_reload"))
        restored.poll()
        self.assertTrue(restored.vacation["enabled"])
        restored.set_vacation(False)
        self.assertFalse(restored.vacation_state()["enabled"])

    def test_invalid_selection_or_clock_has_no_effect(self):
        with self.assertRaises(ValueError):
            self.srv.set_vacation(True, ["unknown"])
        with self.assertRaises(ValueError):
            self.srv.set_vacation(True, [])
        self.srv.set_clock_mode("accelere")
        with self.assertRaises(ValueError):
            self.srv.set_vacation(True, ["light-1"])
        self.assertFalse(self.srv.vacation["enabled"])

    def test_http_routes(self):
        with patch.object(hue_web,"controller",self.srv):
            with TestClient(hue_web.app) as client:
                self.assertEqual(client.get("/api/vacation").status_code, 200)
                self.assertEqual(client.post("/api/vacation",json={
                    "enabled":True,"light_ids":["light-1"]}).status_code,200)
                self.assertTrue(client.get("/api/vacation").json()["data"]["enabled"])
                self.assertEqual(client.post("/api/vacation",json={"enabled":True,
                    "light_ids":["missing"]}).status_code,400)
                self.assertEqual(client.post("/api/vacation",json={"enabled":False}).status_code,200)


if __name__ == "__main__":
    unittest.main()
