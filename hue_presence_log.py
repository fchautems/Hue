"""Historique local des observations Hue, sans supposer une coupure secteur.

Les heures correspondent aux observations du pont, non aux actions physiques.
Ce CSV reste local au Raspberry (répertoire logs/, ignoré par Git).
"""
from __future__ import annotations

import csv
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
