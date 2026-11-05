"""Offline approximate sunrise/sunset for previews; never controls lights."""
from datetime import date, datetime, timedelta, timezone
from math import acos, asin, atan2, cos, degrees, isfinite, radians, sin, tan
from zoneinfo import ZoneInfo


def solar_times(day: date, latitude: float, longitude: float, tz_name: str = "Europe/Zurich") -> dict:
    """Local aware solar times, or None for polar day/night.

    NOAA approximate geometry, apparent zenith 90.833 degrees; longitude east positive.
    Not intended for navigation or precision astronomical work.
    """
    if not isinstance(day, date) or isinstance(day, datetime):
        raise ValueError("day must be a date")
    if (not isinstance(latitude, (int, float)) or isinstance(latitude, bool)
            or not isinstance(longitude, (int, float)) or isinstance(longitude, bool)
            or not isfinite(latitude) or not isfinite(longitude)
            or not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
        raise ValueError("invalid coordinates")
    tz = ZoneInfo(tz_name)
    n = day.timetuple().tm_yday

    def event(sunrise):
        lng_hour = longitude / 15
        t = n + ((6 if sunrise else 18) - lng_hour) / 24
        m = 0.9856 * t - 3.289
        true_long = (m + 1.916 * sin(radians(m)) + 0.020 * sin(2 * radians(m)) + 282.634) % 360
        ra = degrees(atan2(0.91764 * tan(radians(true_long)), 1)) % 360
        ra += (int(true_long / 90) * 90 - int(ra / 90) * 90)
        ra /= 15
        sin_dec = 0.39782 * sin(radians(true_long))
        cos_dec = cos(asin(sin_dec))
        denominator = cos_dec * cos(radians(latitude))
        if abs(denominator) < 1e-12:
            return None
        cos_h = (cos(radians(90.833)) - sin_dec * sin(radians(latitude))) / denominator
        if not -1 <= cos_h <= 1:
            return None
        h = 360 - degrees(acos(cos_h)) if sunrise else degrees(acos(cos_h))
        utc_hours = h / 15 + ra - 0.06571 * t - 6.622 - lng_hour
        # NOAA's UTC hour is modulo one day, but the UTC *date* is not
        # necessarily the requested civil date (notably near the dateline).
        # Pick the UTC day whose converted local date matches the request.
        utc_midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        utc_time = timedelta(hours=utc_hours % 24)
        candidates = [
            (utc_midnight + timedelta(days=shift) + utc_time).astimezone(tz)
            for shift in (-1, 0, 1)
        ]
        matching = [instant for instant in candidates if instant.date() == day]
        if len(matching) != 1:
            raise ValueError("cannot resolve solar event on local date")
        return matching[0]

    return {"sunrise": event(True), "sunset": event(False)}
