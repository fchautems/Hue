"""Continuous solar lighting curves anchored to daylight and personal hours."""
import math

RHYTHM_DEFAULTS = dict(transition=30, comfort=55, saturation=45,
                       morning_hue=34, evening_hue=28, night_hue=30, day_kelvin=2700)


def validate_rhythm(raw, wake, bed, low, high):
    if not isinstance(raw, dict) or set(raw) != set(RHYTHM_DEFAULTS):
        raise ValueError("Réglages du rythme solaire incomplets.")
    bounds = dict(transition=(1, 180), comfort=(low, high), saturation=(0, 100),
                  morning_hue=(0, 359), evening_hue=(0, 359), night_hue=(0, 359), day_kelvin=(2700, 6500))
    for key, (minimum, maximum) in bounds.items():
        if type(raw[key]) is not int or not minimum <= raw[key] <= maximum:
            raise ValueError("Vérifie durée, luminosité de confort, saturation, teintes et blanc de journée.")
    if 2 * raw['transition'] > 1440 - (bed - wake):
        raise ValueError("Les transitions avant réveil et après coucher doivent tenir dans la nuit.")
    return dict(raw)


def solar_rhythm_times(p):
    """Timing for daily profiles, also used by their saved fixed copies."""
    r = p['solar_rhythm']
    wake, bed, duration = r['wake'], r['bed'], r['transition']
    morning_end, warm_at = p['morning_end'], p['solar_warm_at']
    fade_duration = min(duration, (bed - morning_end) // 2)
    return dict(
        wake_start=wake - duration,
        warm_start=max(morning_end, warm_at - 45),
        warm_at=warm_at,
        dim_start=bed - 2 * fade_duration,
        dim_middle=bed - fade_duration,
        night_color_start=max(warm_at, bed - fade_duration),
    )


def rhythm_position(anchors, minute):
    """Find an interval in a list of cyclic anchors, including midnight."""
    start = anchors[0]
    m = float(minute)
    if not math.isfinite(m):
        raise ValueError("Heure invalide.")
    m = (m - start) % 1440 + start
    for index, (a, b) in enumerate(zip(anchors, anchors[1:])):
        if a <= m < b:
            return index, (m-a)/(b-a)
    return len(anchors) - 1, 0


def legacy_anchors(p):
    r = p['solar_rhythm']
    wake, bed, duration = r['wake'], r['bed'], r['transition']
    return [wake - duration, wake, p['morning_end'], p['evening_start'], bed, bed + duration]


def rhythm_progress(t, evening=False):
    # Smooth asymmetric S: rapid morning rise, slow beginning of evening fall.
    from hue_simple_profile import smootherstep
    return smootherstep(t*t if evening else 1-(1-t)**2)


def rhythm_brightness(p, minute):
    r = p['solar_rhythm']
    low, high, comfort = p['min_brightness'], p['max_brightness'], r['comfort']
    levels = [low, comfort, high, high, comfort, low, low]
    if 'solar_warm_at' in p:
        timing = solar_rhythm_times(p)
        anchors = [timing['wake_start'], r['wake'], p['morning_end'],
                   timing['dim_start'], timing['dim_middle'], r['bed']]
    else:
        anchors = legacy_anchors(p)
    i, t = rhythm_position(anchors, minute)
    k = rhythm_progress(t, evening=i in (3, 4))
    return round(levels[i] + (levels[i+1]-levels[i])*k, 2)


def daylight_xy(kelvin):
    """CIE D-series daylight locus, 4000–6500 K (chromaticity, not spectrum).

    Reference: https://colour.readthedocs.io/en/master/generated/colour.temperature.CCT_to_xy_CIE_D.html
    """
    x = -4.607e9/kelvin**3 + 2.9678e6/kelvin**2 + 99.11/kelvin + .244063
    return {'x': x, 'y': -3*x*x + 2.87*x - .275}


def day_white_xy(kelvin):
    """Use the Planckian locus for warm white and preserve the daylight presets."""
    if kelvin >= 4000:
        return daylight_xy(kelvin)
    # Kang et al. approximation on the 2222–4000 K interval.
    x = -0.2661239e9/kelvin**3 - 0.2343580e6/kelvin**2 + 877.6956/kelvin + 0.179910
    y = -0.9549476*x**3 - 1.37418593*x*x + 2.09137015*x - 0.16748867
    return {'x': x, 'y': y}


def display_rgb(xy):
    """Approximate sRGB preview of xy at normalized luminance, without dimming."""
    x, y = xy['x'], xy['y']
    X, Y, Z = x/y, 1, (1-x-y)/y
    rgb = [3.2404542*X-1.5371385*Y-.4985314*Z,
           -.969266*X+1.8760108*Y+.041556*Z,
           .0556434*X-.2040259*Y+1.0572252*Z]
    scale = max(1, *rgb)
    def encode(v):
        v = max(0, v/scale)
        return round(255*(12.92*v if v <= .0031308 else 1.055*v**(1/2.4)-.055))
    return [encode(v) for v in rgb]


def rhythm_color(p, minute):
    from hue_rgb import hsv_to_xy
    r = p['solar_rhythm']
    morning, day = (r['morning_hue'], r['saturation']), (r['morning_hue'], 0)
    evening, night = (r['evening_hue'], r['saturation']), (r['night_hue'], 100)
    if 'solar_warm_at' in p:
        timing = solar_rhythm_times(p)
        anchors = [timing['wake_start'], r['wake'], p['morning_end'], timing['warm_start'],
                   timing['warm_at'], timing['night_color_start'], r['bed']]
        points = [night, morning, day, (evening[0], 0), evening, evening, night, night]
    else:
        anchors = legacy_anchors(p)
        points = [night, morning, day, (evening[0], 0), evening, night, night]
    i, t = rhythm_position(anchors, minute)
    k = rhythm_progress(t, evening=i == len(anchors) - 2)
    (ha, sa), (hb, sb) = points[i:i+2]
    h = (ha + (((hb-ha+180)%360)-180)*k) % 360
    s = sa + (sb-sa)*k
    pure, white = hsv_to_xy({'h': h, 's': 100}), day_white_xy(r['day_kelvin'])
    xy = {axis: white[axis] + (pure[axis]-white[axis])*s/100 for axis in ('x','y')}
    return {'h': h, 's': s, 'xy': xy, 'display_rgb': display_rgb(xy)}
