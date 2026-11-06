"""Generate a fixed, reviewable daily profile; never controls a lamp."""
from hue_solar import solar_times
from hue_simple_profile import validate_simple_profile, simple_brightness_at
from hue_rgb import DEFAULT_RGB_PHASES, rgb_at, validate_rgb_phases
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from hue_solar_rhythm import RHYTHM_DEFAULTS, validate_rhythm

LEGACY_SOLAR_CONFIG = dict(latitude=46.46, longitude=6.22, tz="Europe/Zurich",
                            wake=420, bed=1350, low=10, high=85)
DEFAULT_SOLAR_CONFIG = dict(LEGACY_SOLAR_CONFIG, **RHYTHM_DEFAULTS)


def validate_solar_config(raw):
    if not isinstance(raw, dict) or set(raw) not in (set(LEGACY_SOLAR_CONFIG), set(DEFAULT_SOLAR_CONFIG)):
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
    if 'transition' in raw:
        validate_rhythm({k:raw[k] for k in RHYTHM_DEFAULTS}, wake, bed, low, high)
    return dict(raw)


def draft_profile(day, latitude, longitude, tz, wake, bed, low=10, high=85, **rhythm):
    validate_solar_config(dict(latitude=latitude, longitude=longitude, tz=tz,
                               wake=wake, bed=bed, low=low, high=high, **rhythm))
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
    if rhythm:
        params['solar_rhythm'] = dict(rhythm, wake=wake, bed=bed)
        validate_simple_profile(params)
    colors = validate_rgb_phases(DEFAULT_RGB_PHASES)
    sample_minutes = list(range(0, 1441, 15))
    if rhythm:
        sample_minutes = sorted(set(range(0, 1441, 5)) | {
            (wake-rhythm['transition']) % 1440, wake, morning_end, evening_start,
            bed, (bed+rhythm['transition']) % 1440})
    samples = [dict(minute=m, brightness=simple_brightness_at(params, m),
                    color=rgb_at(colors, params, m)) for m in sample_minutes]
    note = ""
    if rise and sunset and (morning_end != rise_minute or evening_start != set_minute):
        note = "Soleil hors de ta plage de veille : horaires ajustés pour conserver l’ordre et au moins 30 minutes par transition."
    return dict(day=day.isoformat(), params=params, colors=colors, samples=samples,
                timing_note=note,
                sunrise=rise.isoformat() if rise else None,
                sunset=sunset.isoformat() if sunset else None,
                timezone=tz,
                polar_fallback=rise is None or sunset is None)
