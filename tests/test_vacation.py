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


    def test_quick_test_runs_hardware_actions_then_resumes_live_plan(self):
        self.srv.set_vacation(True, ["light-1"])
        original = list(self.srv.vacation["schedule"])
        started = self.srv.set_vacation_test("start")
        self.assertTrue(started["running"])
        self.assertEqual(started["duration_seconds"], 60)
        self.assertGreater(started["total"], 0)
        self.assertEqual(original, self.srv.vacation["schedule"])
        self.bridge.calls.clear()
        self.srv.automate()
        self.assertTrue(any(path == "light/light-1" and payload["on"]["on"] is False
                            for path, payload in self.bridge.calls))
        self.srv.poll()
        self.assertEqual(self.srv.vacation["overrides"], {})
        # Tout début de journée testé, puis première lumière dans 3 à 4 s.
        self.srv.vacation_test["started_monotonic"] -= 5
        self.srv.automate()
        self.assertTrue(any(path == "light/light-1" and payload["on"]["on"] is True
                            for path, payload in self.bridge.calls))
        self.srv.poll()
        self.assertEqual(self.srv.vacation["overrides"], {})
        # Contrôle : à l'échéance aucune rafale de commandes accumulées.
        before = len(self.bridge.calls)
        self.srv.vacation_test["started_monotonic"] -= 57
        self.srv.automate()
        self.assertFalse(self.srv.vacation_test["running"])
        self.assertEqual(self.srv.vacation_test["status"], "terminé")
        self.assertLessEqual(len(self.bridge.calls) - before, 1)
        self.assertTrue(self.srv.vacation["enabled"])
        self.assertEqual(original, self.srv.vacation["schedule"])

    def test_quick_test_stop_and_restart_do_not_persist_acceleration(self):
        self.srv.set_vacation(True, ["light-0"])
        self.srv.set_vacation_test("start")
        self.assertTrue(self.srv.set_vacation_test("stop")["running"] is False)
        self.assertEqual(self.srv.vacation_test["status"], "interrompu")
        self.srv.set_vacation_test("start")
        restored = HueServer(self.bridge, self.root/"settings.json",
                              logging.getLogger("test_demo_reboot"))
        restored.poll()
        self.assertTrue(restored.vacation["enabled"])
        self.assertIsNone(restored.vacation_test)

    def test_quick_test_requires_vacation_and_ignores_conflicting_clock(self):
        with self.assertRaisesRegex(ValueError, "Activer"):
            self.srv.set_vacation_test("start")
        self.srv.set_vacation(True, ["light-0"])
        with self.assertRaises(ValueError):
            self.srv.set_clock_mode("accelere")
        self.srv.set_vacation_test("start")
        with self.assertRaises(ValueError):
            self.srv.set_vacation_test("start")
        self.srv.set_vacation(False)
        self.assertFalse(self.srv.vacation_test["running"])
        self.assertFalse(self.srv.vacation["enabled"])

    def test_quick_test_api(self):
        with patch.object(hue_web,"controller",self.srv):
            with TestClient(hue_web.app) as client:
                self.assertEqual(client.post("/api/vacation/test", json={"action":"start"}).status_code,400)
                self.assertEqual(client.post("/api/vacation",json={
                    "enabled":True,"light_ids":["light-2"]}).status_code,200)
                response = client.post("/api/vacation/test",json={"action":"start"})
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.json()["data"]["running"])
                self.assertTrue(client.get("/api/vacation").json()["data"]["test"]["running"])
                self.assertEqual(client.post("/api/vacation/test",json={"action":"bad"}).status_code,400)
                stopped = client.post("/api/vacation/test",json={"action":"stop"})
                self.assertEqual(stopped.status_code,200)
                self.assertFalse(stopped.json()["data"]["running"])

    def test_quick_test_excludes_all_observed_events_from_training_history(self):
        """ON/OFF et Zigbee observés pendant les 60 s ne deviennent pas des habitudes."""
        self.srv.set_vacation(True, ["light-1"])
        self.srv.set_vacation_test("start")
        self.assertTrue(self.srv.vacation_test["running"])
        history = self.root / "logs" / "presence_events.csv"
        self.assertFalse(history.exists())

        # Changement de l'ampoule testée, y compris un état qui ne ressemble
        # pas à la dernière commande générée par le moteur.
        self.bridge.lights[1]["on"] = {"on": False}
        self.srv.poll()
        self.bridge.lights[1]["on"] = {"on": True}
        self.srv.poll()
        self.bridge.connectivity[1]["status"] = "disconnected"
        self.srv.poll()
        self.bridge.connectivity[1]["status"] = "connected"
        self.srv.poll()

        # Par prudence, aucune ligne d'apprentissage n'est écrite durant la démo,
        # même si une autre lampe change physiquement d'état.
        self.bridge.lights[2]["on"] = {"on": False}
        self.srv.poll()
        self.assertFalse(history.exists())
        self.assertEqual(self.srv.vacation["overrides"], {})

    def test_quick_test_stop_ignores_late_echo_then_resumes_real_logging(self):
        history = self.root / "logs" / "presence_events.csv"
        self.bridge.lights[1]["on"] = {"on": False}
        self.srv.poll()
        self.bridge.lights[1]["on"] = {"on": True}
        self.srv.poll()
        before = self.srv.presence_log.recent()
        self.assertEqual(len(before), 2)

        self.srv.set_vacation(True, ["light-1"])
        self.srv.set_vacation_test("start")
        self.bridge.lights[1]["on"] = {"on": False}
        self.srv.poll()
        self.srv.set_vacation_test("stop")
        self.bridge.lights[1]["on"] = {"on": True}  # Retard de remontée après arrêt.
        self.srv.poll()
        self.assertEqual(self.srv.presence_log.recent(), before)
        self.assertEqual(self.srv.vacation["overrides"], {})

        # Tant que Vacances est actif, aucune lampe ne doit être apprise :
        # ni celle du test, ni une lampe hors sélection.
        self.bridge.lights[2]["on"] = {"on": False}
        self.srv.poll()
        self.assertEqual(self.srv.presence_log.recent(), before)

        # La fin du test ne suffit pas : il faut désactiver Vacances.
        self.srv.vacation_test["log_block_until"] = time.monotonic() - 1
        self.bridge.lights[1]["on"] = {"on": False}
        self.srv.poll()
        self.assertEqual(self.srv.presence_log.recent(), before)

        # Au retour, ignorer les échos retardés pendant 45 secondes.
        self.srv.set_vacation(False)
        self.bridge.lights[2]["on"] = {"on": True}
        self.srv.poll()
        self.assertEqual(self.srv.presence_log.recent(), before)

        self.srv._history_resume_after = time.monotonic() - 1
        self.bridge.lights[2]["on"] = {"on": False}
        self.srv.poll()
        self.assertEqual(len(self.srv.presence_log.recent()), 3)

    def test_vacation_stops_learning_but_not_neighbor_override(self):
        """Vacances n'apprend jamais ses sorties, mais respecte la télécommande."""
        history = self.root / "logs" / "presence_events.csv"
        self.srv.set_vacation(True, ["light-1"])
        # Un visiteur allume la lampe en dehors du test rapide.
        self.bridge.lights[1]["on"] = {"on": False}
        self.srv.poll()
        self.bridge.lights[1]["on"] = {"on": True}
        self.srv.poll()
        self.assertIn("light-1", self.srv.vacation["overrides"])
        self.assertTrue(self.srv.vacation["overrides"]["light-1"]["on"])
        self.assertFalse(history.exists())

        # Une autre lampe change, puis une lampe devient Zigbee hors ligne.
        self.bridge.lights[2]["on"] = {"on": False}
        self.bridge.connectivity[1]["status"] = "disconnected"
        self.srv.poll()
        self.assertFalse(history.exists())

        # L'interruption reste bloquée après un redémarrage en mode Vacances.
        restored = HueServer(self.bridge, self.root/"settings.json",
                             logging.getLogger("test_vacation_no_learning_restart"))
        restored.poll()
        self.assertTrue(restored.vacation["enabled"])
        self.bridge.lights[0]["on"] = {"on": False}
        restored.poll()
        self.assertFalse(history.exists())

    def test_demo_timeout_protects_late_bridge_events(self):
        self.srv.set_vacation(True, ["light-1"])
        self.srv.set_vacation_test("start")
        self.srv.vacation_test["started_monotonic"] -= 61
        self.srv.vacation_test["log_block_until"] = time.monotonic() - 5
        self.srv.automate()
        self.assertFalse(self.srv.vacation_test["running"])
        self.assertTrue(self.srv._presence_history_suppressed("light-1"))
        self.bridge.lights[1]["on"] = {
            "on": not self.bridge.lights[1]["on"]["on"]}
        self.srv.poll()
        self.assertFalse((self.root / "logs" / "presence_events.csv").exists())
        self.assertEqual(self.srv.vacation["overrides"], {})

    def test_accelerated_clock_never_trains_presence_log(self):
        """Les tests de courbes horaires ne doivent pas contaminer l'historique."""
        history = self.root / "logs" / "presence_events.csv"
        self.srv.set_clock_mode("accelere")
        self.bridge.lights[0]["on"] = {"on": False}
        self.srv.poll()
        self.bridge.connectivity[0]["status"] = "disconnected"
        self.srv.poll()
        self.assertFalse(history.exists())

        self.srv.set_clock_mode("reel")
        self.bridge.connectivity[0]["status"] = "connected"
        self.srv.poll()
        self.bridge.lights[0]["on"] = {"on": True}
        self.srv.poll()
        self.assertFalse(history.exists())

        self.srv._history_resume_after = time.monotonic() - 1
        self.bridge.lights[0]["on"] = {"on": False}
        self.srv.poll()
        self.assertEqual(self.srv.presence_log.recent()[0]["event"], "light_off")

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
