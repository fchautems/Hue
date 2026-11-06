"""Generate a fixed, reviewable daily profile; never controls a lamp."""
from hue_solar import solar_times
from hue_simple_profile import validate_simple_profile, simple_brightness_at
from hue_rgb import DEFAULT_RGB_PHASES, rgb_at, validate_rgb_phases


def draft_profile(day, latitude, longitude, tz, wake, bed, low=10, high=85):
    if type(wake) is not int or type(bed) is not int or not 0 <= wake < bed <= 1439 or bed - wake < 180:
        raise ValueError("Réveil avant coucher, avec au moins trois heures entre les deux (sans passage de minuit).")
    times = solar_times(day, latitude, longitude, tz)
    minute = lambda value: value.hour * 60 + value.minute
    rise, sunset = times['sunrise'], times['sunset']
    # Personal rhythm is authoritative: solar adjustment remains bounded.
    morning_end = max(wake + 30, min(wake + 120, minute(rise) + 30 if rise else wake + 60))
    evening_start = max(morning_end, bed - 180, min(bed - 30, minute(sunset) if sunset else bed - 90))
    params = validate_simple_profile(dict(wake=wake, morning_end=morning_end,
        evening_start=evening_start, bed=bed, min_brightness=low, max_brightness=high))
    colors = validate_rgb_phases(DEFAULT_RGB_PHASES)
    samples = [dict(minute=m, brightness=simple_brightness_at(params, m),
                    color=rgb_at(colors, params, m)) for m in range(0, 1441, 15)]
    return dict(day=day.isoformat(), params=params, colors=colors, samples=samples,
                polar_fallback=rise is None or sunset is None)
