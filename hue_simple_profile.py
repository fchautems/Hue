"""Profil simple à rampe monotone, plateau et raccords C2 (sans paliers brusques)."""
from __future__ import annotations

import math

DEFAULT_SIMPLE_PROFILE = {
    "wake": 375,              # 06:15, début de montée
    "morning_end": 780,       # 13:00, début du plateau
    "evening_start": 1080,    # 18:00, fin du plateau
    "bed": 1380,              # 23:00, début du minimum nocturne
    "min_brightness": 10,
    "max_brightness": 85,
}


def validate_simple_profile(raw):
    """Accepte uniquement 4 horaires dans l'ordre et deux niveaux lumineux.

    On conserve pour le moment une journée sans transition traversant minuit.
    Le profil retourne toujours au niveau nocturne avant minuit.
    """
    if not isinstance(raw, dict) or set(raw) != set(DEFAULT_SIMPLE_PROFILE):
        raise ValueError("La courbe simple nécessite quatre horaires et deux luminosités.")
    for name in DEFAULT_SIMPLE_PROFILE:
        value = raw[name]
        if type(value) is not int:
            raise ValueError("Les horaires et luminosités doivent être des nombres entiers.")
    wake, morning_end, evening_start, bed = (
        raw[name] for name in ("wake", "morning_end", "evening_start", "bed")
    )
    if not (0 <= wake < morning_end <= evening_start < bed <= 1439):
        raise ValueError("Respecte l'ordre : lever, fin de montée, début de descente, coucher.")
    if morning_end - wake < 30 or bed - evening_start < 30:
        raise ValueError("La montée et la descente doivent durer au moins 30 minutes.")
    low, high = raw["min_brightness"], raw["max_brightness"]
    if not (1 <= low < high <= 100):
        raise ValueError("Le minimum doit être inférieur au maximum (entre 1 et 100 %).")
    return dict(raw)


def smootherstep(t):
    """Polynôme quintique monotone, dérivées première et seconde nulles aux bornes."""
    t = max(0.0, min(1.0, float(t)))
    return t * t * t * (t * (6 * t - 15) + 10)


def simple_brightness_at(profile, minute):
    """Niveau continu sur 24 h : nuit, montée, plateau, descente, nuit."""
    p = validate_simple_profile(profile)
    m = float(minute)
    if not math.isfinite(m):
        raise ValueError("Heure invalide.")
    m %= 1440
    low, high = p["min_brightness"], p["max_brightness"]
    if m <= p["wake"] or m >= p["bed"]:
        return float(low)
    if m < p["morning_end"]:
        t = (m - p["wake"]) / (p["morning_end"] - p["wake"])
        return round(low + (high - low) * smootherstep(t), 2)
    if m <= p["evening_start"]:
        return float(high)
    t = (m - p["evening_start"]) / (p["bed"] - p["evening_start"])
    return round(high - (high - low) * smootherstep(t), 2)
