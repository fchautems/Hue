"""Generate a fixed, reviewable daily profile; never controls a lamp."""
from hue_solar import solar_times
from hue_simple_profile import validate_simple_profile, simple_brightness_at
from hue_rgb import DEFAULT_RGB_PHASES, rgb_at, validate_rgb_phases
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_SOLAR_CONFIG = dict(latitude=46.46, longitude=6.22, tz="Europe/Zurich",
                            wake=420, bed=1350, low=10, high=85)


def validate_solar_config(raw):
    if not isinstance(raw, dict) or set(raw) != set(DEFAULT_SOLAR_CONFIG):
        raise ValueError("Renseigne le lieu, le réveil, le coucher et les deux niveaux lumineux.")
    for key, bound in (("latitude", 90), ("longitude", 180)):
        value = raw[key]
        if type(value) not in (int, float) or not isfinite(value) or not -bound <= value <= bound:
            raise ValueError("Coordonnées du lieu invalides.")
    try:
        if not isinstance(raw['tz'], str):
            raise ValueError()
        ZoneInfo(raw['tz'])
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Fuseau horaire inconnu.") from None
    wake, bed, low, high = (raw[k] for k in ('wake', 'bed', 'low', 'high'))
    if (type(wake) is not int or type(bed) is not int or
            not 0 <= wake < bed <= 1439 or bed - wake < 180):
        raise ValueError("Réveil avant coucher, avec au moins trois heures entre les deux (sans passage de minuit).")
    if type(low) is not int or type(high) is not int or not 1 <= low < high <= 100:
        raise ValueError("Le minimum doit être inférieur au maximum, entre 1 et 100 %.")
    return dict(raw)


def draft_profile(day, latitude, longitude, tz, wake, bed, low=10, high=85):
    if type(wake) is not int or type(bed) is not int or not 0 <= wake < bed <= 1439 or bed - wake < 180:
        raise ValueError("Réveil avant coucher, avec au moins trois heures entre les deux (sans passage de minuit).")
    times = solar_times(day, latitude, longitude, tz)
    minute = lambda value: value.hour * 60 + value.minute
    rise, sunset = times['sunrise'], times['sunset']
    # Solar anchors are used directly. Only the existing 30-minute minimum
    # and chronological order constrain days outside the user's waking hours.
    rise_minute = minute(rise) if rise else wake + 60
    set_minute = minute(sunset) if sunset else bed - 90
    morning_end = max(wake + 30, min(bed - 30, rise_minute))
    evening_start = max(morning_end, min(bed - 30, set_minute))
    params = validate_simple_profile(dict(wake=wake, morning_end=morning_end,
        evening_start=evening_start, bed=bed, min_brightness=low, max_brightness=high,
        transition_shape="asymmetric"))
    colors = validate_rgb_phases(DEFAULT_RGB_PHASES)
    samples = [dict(minute=m, brightness=simple_brightness_at(params, m),
                    color=rgb_at(colors, params, m)) for m in range(0, 1441, 15)]
    note = ""
    if rise and sunset and (morning_end != rise_minute or evening_start != set_minute):
        note = "Soleil hors de ta plage de veille : horaires ajustés pour conserver l’ordre et au moins 30 minutes par transition."
    return dict(day=day.isoformat(), params=params, colors=colors, samples=samples,
                timing_note=note,
                sunrise=rise.isoformat() if rise else None,
                sunset=sunset.isoformat() if sunset else None,
                timezone=tz,
                polar_fallback=rise is None or sunset is None)
