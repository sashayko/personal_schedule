import calendar
from datetime import date

from flask import Flask, render_template

app = Flask(__name__)

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
    return render_template(
        "index.html",
        today=today,
        month_title=today.strftime("%B %Y"),
        weekdays=["M", "T", "W", "T", "F", "S", "S"],
        weeks=build_month(today.year, today.month, today),
        today_count=today_count,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
