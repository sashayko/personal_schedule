import calendar
import os
from datetime import date, datetime, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, jsonify, render_template, request
from flask_migrate import Migrate
from sqlalchemy.engine import URL

from feeds import FeedError, load_events
from models import ICalFeed, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
    "mysql+pymysql",
    username=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASSWORD", "root"),
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "3306")),
    database=os.environ.get("DB_NAME", "schedule"),
)
db.init_app(app)
migrate = Migrate(app, db)

KIND_ORDER = ["event", "activity", "task"]


def local_today():
    """Today's date in TIMEZONE (if set), else the server's local date."""
    tz_name = os.environ.get("TIMEZONE")
    if tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name)).date()
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return date.today()


def format_time(event):
    if event["all_day"]:
        return "All day"
    start = event["start"].strftime("%H:%M")
    return f"{start} – {event['end'].strftime('%H:%M')}" if event["end"] else start


def build_month(year, month, today, items_by_day):
    """Return weeks (Mon-first) of day cells for the month grid."""
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
        weeks.append([
            {
                "date": d.isoformat(),
                "day": d.day,
                "in_month": d.month == month,
                "is_today": d == today,
                "kinds": [k for k in KIND_ORDER if any(i["kind"] == k for i in items_by_day.get(d.isoformat(), ()))],
            }
            for d in week
        ])
    return weeks


@app.route("/")
def home():
    today = local_today()
    feed = ICalFeed.query.first()
    month_days = calendar.Calendar(firstweekday=0).monthdatescalendar(today.year, today.month)
    grid_start, grid_end = month_days[0][0], month_days[-1][-1] + timedelta(days=1)

    # date (ISO string) -> list of items shown for that day
    items_by_day = {}
    feed_error = None
    if feed:
        try:
            events = load_events(feed.url, grid_start, grid_end, force=request.args.get("refresh") == "1")
        except FeedError as exc:
            app.logger.warning("iCal feed %s: %s", feed.url, exc)
            feed_error = str(exc)
            events = []
        for event in events:
            for day in event["days"]:
                items_by_day.setdefault(day.isoformat(), []).append({
                    "kind": "event",
                    "title": event["title"],
                    "time": format_time(event),
                    "location": event["location"],
                })

    return render_template(
        "index.html",
        today=today,
        month_title=today.strftime("%B %Y"),
        weekdays=["M", "T", "W", "T", "F", "S", "S"],
        weeks=build_month(today.year, today.month, today, items_by_day),
        today_count=len(items_by_day.get(today.isoformat(), [])),
        items_by_day=items_by_day,
        feed_error=feed_error,
        ical_url=feed.url if feed else "",
    )


ICAL_URL_SCHEMES = {"http", "https", "webcal"}
ICAL_URL_MAX_LENGTH = ICalFeed.url.type.length


@app.put("/settings/ical-url")
def save_ical_url():
    """Store the user's iCal feed URL, replacing any previous one. An empty URL removes it."""
    url = ((request.get_json(silent=True) or {}).get("url") or "").strip()
    if url:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ICAL_URL_SCHEMES or not parsed.netloc:
            return jsonify(error="Enter a valid http(s) or webcal URL."), 400
        if len(url) > ICAL_URL_MAX_LENGTH:
            return jsonify(error=f"URL must be at most {ICAL_URL_MAX_LENGTH} characters."), 400

    # Single-user app: there is only ever one feed, so replace whatever is stored
    current = ICalFeed.query.first()
    if current and current.url == url:
        return jsonify(url=url)
    ICalFeed.query.delete()
    if url:
        db.session.add(ICalFeed(url=url))
    db.session.commit()
    return jsonify(url=url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
