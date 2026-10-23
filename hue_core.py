"""Calcul de l'heure virtuelle et interpolation douce des courbes Hue."""
from __future__ import annotations
from datetime import datetime
import time

DEFAULT_POINTS = [
    {"minute": 0, "brightness": 8},
    {"minute": 360, "brightness": 8},
    {"minute": 480, "brightness": 70},
    {"minute": 600, "brightness": 100},
    {"minute": 1020, "brightness": 100},
    {"minute": 1200, "brightness": 55},
    {"minute": 1320, "brightness": 16},
    {"minute": 1439, "brightness": 8},
]


def validate_points(points):
    if not isinstance(points, list) or not 2 <= len(points) <= 24:
        raise ValueError("La courbe doit contenir entre 2 et 24 points.")
    cleaned = []
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("Point de courbe invalide.")
        minute, brightness = point.get("minute"), point.get("brightness")
        if isinstance(minute, bool) or not isinstance(minute, int) or not 0 <= minute < 1440:
            raise ValueError("L'heure doit correspondre à une minute entre 0 et 1439.")
        if isinstance(brightness, bool) or not isinstance(brightness, (int, float)) or not 1 <= brightness <= 100:
            raise ValueError("La luminosité doit être entre 1 % et 100 %.")
        cleaned.append({"minute": minute, "brightness": float(brightness)})
    cleaned.sort(key=lambda p: p["minute"])
    if len(set(p["minute"] for p in cleaned)) != len(cleaned):
        raise ValueError("Deux points ne peuvent pas avoir la même heure.")
    return cleaned


def brightness_at(points, minute):
    """Interpolation cyclique smoothstep continue, sans saut aux points ni à minuit."""
    points = validate_points(points)
    minute = float(minute) % 1440
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        start = a["minute"]
        end = b["minute"] if i + 1 < len(points) else b["minute"] + 1440
        at = minute if minute >= start else minute + 1440
        if start <= at <= end:
            t = (at - start) / (end - start)
            eased = t * t * (3 - 2 * t)
            return round(a["brightness"] + (b["brightness"] - a["brightness"]) * eased, 2)
    # Tout instant avant le premier point appartient à l'intervalle cyclique final.
    a, b = points[-1], points[0]
    t = ((minute + 1440 - a["minute"]) if minute < a["minute"] else (minute - a["minute"])) / (1440 + b["minute"] - a["minute"])
    eased = t * t * (3 - 2 * t)
    return round(a["brightness"] + (b["brightness"] - a["brightness"]) * eased, 2)


def wall_clock_minutes():
    now = datetime.now().astimezone()
    return now.hour * 60 + now.minute + now.second / 60


def simulated_minutes(sim, monotonic_now=None):
    base = float(sim.get("minute", 0))
    if not sim.get("enabled") or not sim.get("running"):
        return base % 1440
    elapsed = max(0.0, (time.monotonic() if monotonic_now is None else monotonic_now) - sim.get("started_at", 0))
    return (base + elapsed * 1440 / float(sim["seconds_per_day"])) % 1440


def public_sim(sim, monotonic_now=None):
    return {
        "enabled": bool(sim["enabled"]),
        "running": bool(sim["running"]),
        "apply": bool(sim["apply"]),
        "seconds_per_day": sim["seconds_per_day"],
        "minute": round(simulated_minutes(sim, monotonic_now), 3),
    }
