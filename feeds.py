"""Download an iCal (.ics) feed and turn it into per-day calendar items."""

import os
import time
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import icalendar
import recurring_ical_events

FETCH_TIMEOUT_SECONDS = 15
CACHE_SECONDS = 10 * 60

# url -> (fetched_at, raw ics bytes); the feed is re-downloaded at most every CACHE_SECONDS
_cache = {}


class FeedError(Exception):
    """The feed could not be downloaded or parsed."""


def _download(url, force=False):
    cached = _cache.get(url)
    if cached and not force and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    # webcal:// is just a hint for calendar apps; the feed itself is served over https
    fetch_url = "https://" + url[len("webcal://"):] if url.lower().startswith("webcal://") else url
    request = urllib.request.Request(fetch_url, headers={"User-Agent": "PersonalSchedule/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            data = response.read()
    except Exception as exc:
        raise FeedError(f"Couldn't download the calendar: {exc}") from exc

    _cache[url] = (time.monotonic(), data)
    return data


def _timezone(calendar):
    """TIMEZONE env var wins, then the feed's own X-WR-TIMEZONE, then UTC."""
    for name in (os.environ.get("TIMEZONE"), calendar.get("X-WR-TIMEZONE")):
        if name:
            try:
                return ZoneInfo(str(name))
            except (ZoneInfoNotFoundError, ValueError):
                pass
    return ZoneInfo("UTC")


def load_events(url, start, end, force=False):
    """Return events overlapping [start, end) as dicts, sorted by start.

    Each dict has: title, location, all_day, start (datetime or date), end, and
    days (every date the event covers, so multi-day events show on each day).
    """
    data = _download(url, force)
    try:
        calendar = icalendar.Calendar.from_ical(data)
    except Exception as exc:
        raise FeedError(f"Couldn't read the calendar: {exc}") from exc

    tz = _timezone(calendar)
    events = []
    for component in recurring_ical_events.of(calendar).between(start, end):
        ev_start = component.get("DTSTART").dt
        ev_end = component.get("DTEND").dt if component.get("DTEND") else None
        all_day = not isinstance(ev_start, datetime)

        if all_day:
            first_day = ev_start
            # DTEND of an all-day event is exclusive
            last_day = (ev_end - timedelta(days=1)) if ev_end else ev_start
        else:
            # Floating times (no tz) are taken to be in the calendar's timezone
            ev_start = ev_start.astimezone(tz) if ev_start.tzinfo else ev_start.replace(tzinfo=tz)
            if ev_end:
                ev_end = ev_end.astimezone(tz) if ev_end.tzinfo else ev_end.replace(tzinfo=tz)
            first_day = ev_start.date()
            # An event ending exactly at midnight doesn't occupy the next day
            last_day = (ev_end - timedelta(microseconds=1)).date() if ev_end and ev_end > ev_start else first_day

        days = []
        d = max(first_day, start)
        while d <= last_day and d < end:
            days.append(d)
            d += timedelta(days=1)

        events.append({
            "title": str(component.get("SUMMARY") or "(No title)"),
            "location": str(component.get("LOCATION") or ""),
            "all_day": all_day,
            "start": ev_start,
            "end": ev_end,
            "days": days,
        })

    # Within a day: all-day events first, then by start time
    events.sort(key=lambda e: (e["days"][0] if e["days"] else start, not e["all_day"],
                               "" if e["all_day"] else e["start"].strftime("%H:%M")))
    return events
