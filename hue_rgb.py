"""Hue Lab v0.6: validated RGB wheel profiles and continuous colour scheduling.

Colours use HSV only at the *UI configuration* boundary. Hue API v2 receives
CIE xy, constrained to the lamp's reported gamut when available.
"""
from __future__ import annotations

import colorsys
import math

from hue_simple_profile import DEFAULT_SIMPLE_PROFILE, smootherstep, validate_simple_profile

DEFAULT_RGB_PHASES = {
    "morning": {"h": 34, "s": 68},
    "day": {"h": 45, "s": 8},
    "evening": {"h": 28, "s": 75},
    "night": {"h": 16, "s": 87},
}
DEFAULT_MANUAL_COLOR = {"h": 35, "s": 35}
PHASES = tuple(DEFAULT_RGB_PHASES)


def validate_hs(raw):
    if not isinstance(raw, dict) or set(raw) != {"h", "s"}:
        raise ValueError("Une couleur doit contenir teinte h et saturation s.")
    h, s = raw["h"], raw["s"]
    if type(h) is not int or type(s) is not int or not 0 <= h <= 359 or not 0 <= s <= 100:
        raise ValueError("Teinte : 0–359°, saturation : 0–100 %." )
    return {"h": h, "s": s}


def validate_rgb_phases(raw):
    if not isinstance(raw, dict) or set(raw) != set(PHASES):
        raise ValueError("Quatre couleurs sont nécessaires : matin, journée, soir et nuit.")
    return {key: validate_hs(raw[key]) for key in PHASES}


def _mix(a, b, t):
    k = smootherstep(t)
    # Plus court chemin angulaire. La saturation nulle est neutre : la roue
    # permet toujours de choisir une couleur à saturation zéro.
    delta = ((b["h"] - a["h"] + 180) % 360) - 180
    return {"h": (a["h"] + delta * k) % 360, "s": a["s"] + (b["s"] - a["s"]) * k}


def rgb_at(phases, profile, minute):
    """Couleur continue pendant les deux rampes, jour/nuit stables.

    Nuit jusqu'au lever, matin au milieu de la rampe ascendante, jour
    à sa fin, puis soir au milieu de la descente et nuit au coucher.
    """
    # Les validateurs garantissent l'ordre temporel et une durée non nulle.
    p = validate_simple_profile(profile)
    phases = validate_rgb_phases(phases)
    m = float(minute)
    if not math.isfinite(m):
        raise ValueError("Heure invalide.")
    m %= 1440
    wake, morning_end, evening_start, bed = (
        p[name] for name in ("wake", "morning_end", "evening_start", "bed")
    )
    mid_morning = (wake + morning_end) / 2
    mid_evening = (evening_start + bed) / 2
    if m <= wake or m >= bed:
        return dict(phases["night"])
    if m < mid_morning:
        return _mix(phases["night"], phases["morning"], (m - wake) / (mid_morning - wake))
    if m < morning_end:
        return _mix(phases["morning"], phases["day"], (m - mid_morning) / (morning_end - mid_morning))
    if m <= evening_start:
        return dict(phases["day"])
    if m < mid_evening:
        return _mix(phases["day"], phases["evening"], (m - evening_start) / (mid_evening - evening_start))
    return _mix(phases["evening"], phases["night"], (m - mid_evening) / (bed - mid_evening))


def _linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def hsv_to_xy(hs, gamut=None):
    """Convert Hue/Sat to xy for Hue API v2, clipping to the device gamut.

    sRGB D65 -> XYZ -> xy. Lamp brightness is controlled *separately*.
    Use fully bright HSV V=1 so wheel chromaticity never changes with dimming.
    """
    # Accept floating interpolation output; persisted settings remain integer.
    h, s = float(hs["h"]), float(hs["s"])
    if not all(map(math.isfinite, (h, s))) or not 0 <= h < 360 or not 0 <= s <= 100:
        raise ValueError("Teinte ou saturation invalide.")
    r, g, b = [_linear(v) for v in colorsys.hsv_to_rgb(h / 360, s / 100, 1)]
    X = 0.4124564*r + 0.3575761*g + 0.1804375*b
    Y = 0.2126729*r + 0.7151522*g + 0.0721750*b
    Z = 0.0193339*r + 0.1191920*g + 0.9503041*b
    scale = X + Y + Z
    xy = (X/scale, Y/scale)
    triangle = gamut_vertices(gamut)
    if triangle and not point_inside_triangle(xy, triangle):
        # Closest point on any edge: safe even for restricted gamut A/B/C.
        xy = min((nearest_on_segment(xy, triangle[i], triangle[(i+1)%3]) for i in range(3)),
                 key=lambda pt:(pt[0]-xy[0])**2+(pt[1]-xy[1])**2)
    return {"x": round(max(0.0001,min(0.9999,xy[0])), 5),
            "y": round(max(0.0001,min(0.9999,xy[1])), 5)}


def gamut_vertices(gamut):
    if not isinstance(gamut, dict):
        return None
    try:
        vertices = tuple((float(gamut[c]["x"]), float(gamut[c]["y"])) for c in ("red", "green", "blue"))
        area = ((vertices[1][0]-vertices[0][0])*(vertices[2][1]-vertices[0][1])
                -(vertices[2][0]-vertices[0][0])*(vertices[1][1]-vertices[0][1]))
        if abs(area) < 1e-6 or any(not(math.isfinite(x) and math.isfinite(y) and 0<x<1 and 0<y<1) for x,y in vertices):
            return None
        return vertices
    except (KeyError,TypeError,ValueError,OverflowError):
        return None


def point_inside_triangle(pt, verts):
    def cross(a,b,p):
        return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
    a,b,c=verts
    signs=[cross(a,b,pt),cross(b,c,pt),cross(c,a,pt)]
    return min(signs)>=-1e-9 or max(signs)<=1e-9


def nearest_on_segment(point, start, end):
    dx,dy=end[0]-start[0],end[1]-start[1]
    t=max(0,min(1,((point[0]-start[0])*dx+(point[1]-start[1])*dy)/(dx*dx+dy*dy)))
    return (start[0]+t*dx,start[1]+t*dy)


def xy_distance(a,b):
    if not a or not b:
        return float("inf")
    return math.hypot(float(a["x"])-float(b["x"]),float(a["y"])-float(b["y"]))
