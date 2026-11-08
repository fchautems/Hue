"""Solar rhythm: personal times are comfort targets, not the night minimum."""
import math

RHYTHM_DEFAULTS = dict(transition=30, comfort=55, saturation=45,
                       morning_hue=34, evening_hue=28, night_hue=16, day_kelvin=5000)


def validate_rhythm(raw, wake, bed, low, high):
    if not isinstance(raw, dict) or set(raw) != set(RHYTHM_DEFAULTS):
        raise ValueError("Réglages du rythme solaire incomplets.")
    bounds = dict(transition=(1, 180), comfort=(low, high), saturation=(0, 100),
                  morning_hue=(0, 359), evening_hue=(0, 359), night_hue=(0, 359), day_kelvin=(4000, 6500))
    for key, (minimum, maximum) in bounds.items():
        if type(raw[key]) is not int or not minimum <= raw[key] <= maximum:
            raise ValueError("Vérifie durée, luminosité de confort, saturation, teintes et blanc de journée.")
    if 2 * raw['transition'] > 1440 - (bed - wake):
        raise ValueError("Les transitions avant réveil et après coucher doivent tenir dans la nuit.")
    return dict(raw)


def rhythm_position(p, minute):
    """Find one of six cyclic intervals, including transitions across midnight."""
    r = p['solar_rhythm']
    wake, bed, duration = r['wake'], r['bed'], r['transition']
    start, end = wake - duration, bed + duration
    m = float(minute)
    if not math.isfinite(m):
        raise ValueError("Heure invalide.")
    m = (m - start) % 1440 + start
    anchors = [start, wake, p['morning_end'], p['evening_start'], bed, end]
    for index in range(5):
        a, b = anchors[index:index+2]
        if a <= m < b:
            return index, (m-a)/(b-a)
    return 5, 0


def rhythm_progress(t, evening=False):
    # Smooth asymmetric S: rapid morning rise, slow beginning of evening fall.
    from hue_simple_profile import smootherstep
    return smootherstep(t*t if evening else 1-(1-t)**2)


def rhythm_brightness(p, minute):
    r = p['solar_rhythm']
    low, high, comfort = p['min_brightness'], p['max_brightness'], r['comfort']
    levels = [low, comfort, high, high, comfort, low, low]
    i, t = rhythm_position(p, minute)
    k = rhythm_progress(t, evening=i in (3, 4))
    return round(levels[i] + (levels[i+1]-levels[i])*k, 2)


def daylight_xy(kelvin):
    """CIE D-series daylight locus, 4000–6500 K (chromaticity, not spectrum).

    Reference: https://colour.readthedocs.io/en/master/generated/colour.temperature.CCT_to_xy_CIE_D.html
    """
    x = -4.607e9/kelvin**3 + 2.9678e6/kelvin**2 + 99.11/kelvin + .244063
    return {'x': x, 'y': -3*x*x + 2.87*x - .275}


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
    saturation = r['saturation']
    points = [(r['night_hue'],100), (r['morning_hue'],saturation),
              (r['morning_hue'],0), (r['evening_hue'],0),
              (r['evening_hue'],saturation), (r['night_hue'],100), (r['night_hue'],100)]
    i, t = rhythm_position(p, minute)
    # Bring out the evening hue while the room is still bright.
    k = rhythm_progress(t, evening=i == 4)
    (ha, sa), (hb, sb) = points[i:i+2]
    h = (ha + (((hb-ha+180)%360)-180)*k) % 360
    s = sa + (sb-sa)*k
    pure, white = hsv_to_xy({'h': h, 's': 100}), daylight_xy(r['day_kelvin'])
    xy = {axis: white[axis] + (pure[axis]-white[axis])*s/100 for axis in ('x','y')}
    return {'h': h, 's': s, 'xy': xy, 'display_rgb': display_rgb(xy)}
