"""Historique local des observations Hue, sans supposer une coupure secteur.

Les heures correspondent aux observations du pont, non aux actions physiques.
Ce CSV reste local au Raspberry (répertoire logs/, ignoré par Git).
"""
from __future__ import annotations

import csv
from collections import deque
from datetime import datetime
from pathlib import Path
import threading

FIELDS = ("detected_at", "light_id", "light_name", "event")


class PresenceLog:
    def __init__(self, path: Path, logger):
        self.path = Path(path)
        self.logger = logger
        self.lock = threading.Lock()

    def record(self, uid: str, name: str, event: str) -> None:
        """Ajoute une transition constatée ; une erreur disque ne bloque pas Hue."""
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            with self.lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8", newline="") as output:
                    writer = csv.writer(output, delimiter=";")
                    if output.tell() == 0:
                        writer.writerow(FIELDS)
                    writer.writerow((timestamp, uid, name, event))
        except OSError as exc:
            self.logger.warning("Journal de présence indisponible (%s)", type(exc).__name__)

    def recent(self, limit: int = 40) -> list[dict[str, str]]:
        """Dernières observations en premier, sans charger tout le CSV en mémoire."""
        limit = max(1, min(int(limit), 100))
        try:
            with self.lock:
                if not self.path.is_file():
                    return []
                with self.path.open("r", encoding="utf-8", newline="") as source:
                    reader = csv.DictReader(source, delimiter=";")
                    rows = deque((
                        {field: row.get(field, "") for field in FIELDS}
                        for row in reader
                        if row.get("event") in (
                            "light_on", "light_off", "zigbee_connected", "zigbee_disconnected")
                    ), maxlen=limit)
            return list(reversed(rows))
        except (OSError, UnicodeError, csv.Error) as exc:
            self.logger.warning("Lecture du journal de présence impossible (%s)", type(exc).__name__)
            return []
