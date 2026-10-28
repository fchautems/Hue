"""Planificateur de présence local. Ne dépend d'aucun service d'IA.

Les observations Zigbee ne sont jamais assimilées à des actions d'utilisateur.
L'historique ne retient que les couples logiques ON/OFF, avec des durées plausibles.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, time
import hashlib
from pathlib import Path
import random
from statistics import median
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Zurich")
GRACE_SECONDS = 600
EVENT_TYPES = {"light_on", "light_off"}


def past_sessions(path: Path, allowed: set[str]) -> dict[str, list[tuple[int, int]]]:
    """Sessions ON→OFF suffisamment fiables pour guider les horaires."""
    sessions = {uid: [] for uid in allowed}
    pending = {}
    try:
        with Path(path).open("r", encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source, delimiter=";"):
                uid, event = row.get("light_id"), row.get("event")
                if uid not in allowed:
                    continue
                # Une déconnexion interrompt les paires potentiellement ambiguës.
                if event == "zigbee_disconnected":
                    pending.pop(uid, None)
                    continue
                if event not in EVENT_TYPES:
                    continue
                try:
                    at = datetime.fromisoformat(row["detected_at"]).astimezone(LOCAL_TZ)
                except (ValueError, TypeError, KeyError):
                    continue
                if event == "light_on":
                    pending[uid] = at
                elif uid in pending:
                    start = pending.pop(uid)
                    duration = int((at - start).total_seconds() / 60)
                    if 5 <= duration <= 360 and start.date() == at.date():
                        sessions[uid].append((start.hour * 60 + start.minute, duration))
    except (OSError, UnicodeError, csv.Error):
        pass  # Le moteur fonctionne aussi à partir d'un historique vide.
    return sessions


def build_schedule(light_ids: list[str], history_file: Path, seed: str,
                   starting: datetime, days: int = 7) -> list[dict]:
    """Programme déterministe sur une fenêtre glissante, aléatoire selon le jour."""
    unique_ids = list(dict.fromkeys(light_ids))
    history = past_sessions(history_file, set(unique_ids))
    start = starting.astimezone(LOCAL_TZ).date()
    plan = []
    for day_offset in range(days):
        day = start + timedelta(days=day_offset)
        for index, uid in enumerate(unique_ids):
            rng = random.Random(int.from_bytes(
                hashlib.sha256(f"{seed}:{day.isoformat()}:{uid}".encode()).digest()[:8], "big"))
            # Toutes les lampes ne sont pas synchronisées.
            evening_start = 18 * 60 + 20 + index * 24
            evening_length = 180 - min(index * 35, 100)
            samples = [(minute, duration) for minute, duration in history[uid]
                       if 16 * 60 <= minute <= 23 * 60]
            if len(samples) >= 2:
                average_start = int(median(s for s, _ in samples))
                average_length = int(median(d for _, d in samples))
                evening_start = int(0.7 * average_start + 0.3 * evening_start)
                evening_length = int(0.7 * average_length + 0.3 * evening_length)
            start_minute = max(17 * 60, min(22 * 60, evening_start + rng.randint(-25, 25)))
            duration = max(25, min(235, evening_length + rng.randint(-22, 22)))
            end_minute = min(23 * 60 + 45, start_minute + duration)
            # Une courte présence matinale est facultative selon le jour et la lampe.
            if rng.random() < 0.65:
                morning_start = 7 * 60 + index * 13 + rng.randint(-28, 28)
                morning_duration = rng.randint(15, 42)
                plan.extend(_pair(day, uid, morning_start, morning_start + morning_duration))
            plan.extend(_pair(day, uid, start_minute, end_minute))
    return sorted(plan, key=lambda e: (e["at"], e["light_id"], not e["on"]))


def _pair(day, uid, start_minutes, end_minutes):
    def stamp(minutes):
        dt = datetime.combine(day, time(0), tzinfo=LOCAL_TZ) + timedelta(minutes=minutes)
        return dt.isoformat(timespec="seconds")
    return [{"at": stamp(start_minutes), "light_id": uid, "on": True},
            {"at": stamp(end_minutes), "light_id": uid, "on": False}]


def desired_states(schedule: list[dict], when: datetime, selected: list[str]) -> dict[str, bool]:
    """Reconstitue l'état à cette heure, y compris après redémarrage du Pi."""
    result = {uid: False for uid in selected}
    now = when.timestamp()
    for item in schedule:
        try:
            at = datetime.fromisoformat(item["at"]).timestamp()
        except (KeyError, TypeError, ValueError):
            continue
        if at > now:
            break
        uid = item.get("light_id")
        if uid in result:
            result[uid] = item.get("on") is True
    return result


def validate_selection(ids: object, known: set[str]) -> list[str]:
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids):
        raise ValueError("Choisir au moins une lampe.")
    selected = list(dict.fromkeys(ids))
    if len(selected) > 30 or not set(selected).issubset(known):
        raise ValueError("Sélection de lampes invalide.")
    return selected
