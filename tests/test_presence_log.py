"""Tests du journal d'observations pour le simulateur de présence."""
import csv
from datetime import datetime
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hue_web import HueServer
from test_server import FakeClient


class PresenceLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.client = FakeClient()
        self.server = HueServer(
            self.client, self.root / "settings.json", logging.getLogger("presence_test")
        )
        self.file = self.root / "logs" / "presence_events.csv"
        self.server.poll()

    def events(self):
        with self.file.open(encoding="utf-8", newline="") as source:
            return list(csv.DictReader(source, delimiter=";"))

    def test_first_observation_is_not_a_fake_switch_event(self):
        self.assertFalse(self.file.exists())
        self.server.poll()
        self.assertFalse(self.file.exists())

    def test_zigbee_transitions_once_with_local_timestamps(self):
        self.client.connectivity[0]["status"] = "disconnected"
        self.server.poll()
        self.server.poll()
        self.client.connectivity[0]["status"] = "connected"
        self.server.poll()
        rows = self.events()
        self.assertEqual([r["event"] for r in rows], [
            "zigbee_disconnected", "zigbee_connected"
        ])
        self.assertEqual([r["light_name"] for r in rows], ["Salon", "Salon"])
        self.assertTrue(all(r["light_id"] == "light-a" for r in rows))
        self.assertTrue(all(datetime.fromisoformat(r["detected_at"]).utcoffset()
                            is not None for r in rows))

    def test_logical_on_off_are_distinct_from_zigbee(self):
        self.client.lights[0]["on"] = {"on": False}
        self.server.poll()
        self.client.lights[0]["on"] = {"on": True}
        self.server.poll()
        self.server.poll()
        self.assertEqual([r["event"] for r in self.events()], ["light_off", "light_on"])
        self.assertEqual(self.client.calls, [])  # Le journal ne commande aucune lampe.

    def test_disk_error_does_not_interrupt_monitoring(self):
        self.server.presence_log.path = self.root  # Un dossier ne peut pas être ouvert comme fichier.
        self.client.connectivity[0]["status"] = "disconnected"
        self.server.poll()  # Aucun crash de la surveillance.
        self.assertFalse(self.server.previous_online["light-a"])


if __name__ == "__main__":
    unittest.main()
