"""Hue Lab v0.3: transitions et réception d'événements Hue v2.

Le flux d'événements améliore la réactivité ; le polling reste le secours.
Aucun événement n'est traité comme preuve électrique d'un retour secteur.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable

import requests


def reconnect_transition_ms(current: float | None, target: float, *, default_start: float = 10.0) -> int:
    """Durée d'une correction après reconnexion (de 0.5 à 2 s)."""
    difference = abs(float(target) - (float(current) if isinstance(current, (int, float)) else default_start))
    if difference < 10:
        return 500
    if difference < 30:
        return 1000
    if difference <= 60:
        return 1500
    return 2000


def event_has_reconnect_signal(event_containers: object) -> bool:
    """Vrai si un changement Hue peut justifier une relecture immédiate."""
    if not isinstance(event_containers, list):
        return False
    for container in event_containers:
        if not isinstance(container, dict) or container.get("type") not in ("update", "add"):
            continue
        for item in container.get("data", []):
            if not isinstance(item, dict):
                continue
            if item.get("type") == "zigbee_connectivity" and item.get("status") in ("connected", "disconnected"):
                return True
            if item.get("type") == "light" and item.get("on", {}).get("on") is True:
                return True
    return False


class HueEventStream:
    """Écoute SSE non bloquante, avec reconnexion automatique et arrêt propre."""

    def __init__(self, get_client: Callable, on_change: Callable, stop_event: threading.Event, logger=None):
        self.get_client = get_client
        self.on_change = on_change
        self.stop_event = stop_event
        self.log = logger or logging.getLogger(__name__)
        self.thread = None
        self.status = "arrêté"
        self.last_event = None

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run, name="HueEvents", daemon=True)
            self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            client = self.get_client()
            if client is None or not getattr(client, "session", None):
                self.status = "en attente du pont"
                self.stop_event.wait(3)
                continue
            try:
                # Une session distincte pour le flux évite de partager requests.Session entre threads.
                headers = {"hue-application-key": client.session.headers["hue-application-key"], "Accept": "text/event-stream"}
                with requests.get(
                    f"https://{client.ip}/eventstream/clip/v2",
                    headers=headers, stream=True, verify=False, timeout=(4, 25)
                ) as response:
                    response.raise_for_status()
                    self.status = "connecté"
                    for line in response.iter_lines(decode_unicode=True):
                        if self.stop_event.is_set() or client is not self.get_client():
                            break
                        if not line or not line.startswith("data:"):
                            continue
                        try:
                            data = json.loads(line[5:].strip())
                        except ValueError:
                            continue
                        self.last_event = time.time()
                        if event_has_reconnect_signal(data):
                            self.on_change()
            except requests.RequestException as exc:
                # Ne jamais afficher les en-têtes, donc ne jamais divulguer la clé.
                self.status = "reconnexion"
                self.log.info("Flux Hue indisponible (%s), nouvelle tentative", type(exc).__name__)
            if not self.stop_event.is_set():
                self.stop_event.wait(3)
        self.status = "arrêté"