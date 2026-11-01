import calendar
import os
from datetime import date
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request
from flask_migrate import Migrate
from sqlalchemy.engine import URL

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

# Placeholder data until real storage exists: (date, kind) where kind is event/activity/task.
SAMPLE_ITEMS = [
    (date(2026, 10, 2), "task"),
    (date(2026, 10, 6), "event"),
    (date(2026, 10, 6), "activity"),
    (date(2026, 10, 9), "activity"),
    (date(2026, 10, 13), "event"),
    (date(2026, 10, 14), "task"),
    (date(2026, 10, 16), "activity"),
    (date(2026, 10, 20), "event"),
    (date(2026, 10, 20), "task"),
    (date(2026, 10, 23), "activity"),
    (date(2026, 10, 27), "task"),
    (date(2026, 10, 29), "event"),
    (date(2026, 10, 29), "activity"),
    (date(2026, 10, 29), "task"),
    (date(2026, 10, 29), "task"),
    (date(2026, 10, 30), "activity"),
]

KIND_ORDER = ["event", "activity", "task"]


def build_month(year, month, today):
    """Return weeks (Mon-first) of day cells for the month grid."""
    kinds_by_day = {}
    for day, kind in SAMPLE_ITEMS:
        kinds_by_day.setdefault(day, set()).add(kind)

    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
        weeks.append([
            {
                "day": d.day,
                "in_month": d.month == month,
                "is_today": d == today,
                "kinds": [k for k in KIND_ORDER if k in kinds_by_day.get(d, ())],
            }
            for d in week
        ])
    return weeks


@app.route("/")
def home():
    today = date.today()
    today_count = sum(1 for day, _ in SAMPLE_ITEMS if day == today)
    feed = ICalFeed.query.first()
    return render_template(
        "index.html",
        today=today,
        month_title=today.strftime("%B %Y"),
        weekdays=["M", "T", "W", "T", "F", "S", "S"],
        weeks=build_month(today.year, today.month, today),
        today_count=today_count,
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
