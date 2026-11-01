import calendar
from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ICalFeed(db.Model):
    """An iCal (.ics) feed URL to import calendar items from."""

    __tablename__ = "ical_feeds"

    # 768 chars is MySQL's limit for an indexed utf8mb4 column (3072 bytes)
    url = db.Column(db.String(768), primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CalendarItem(db.Model):
    """An event, activity or task the user added in the app."""

    __tablename__ = "calendar_items"

    KINDS = ("event", "activity", "task")
    FREQUENCIES = ("daily", "weekly", "fortnightly", "monthly")
    FREQUENCY_LABELS = {
        "daily": "Every day",
        "weekly": "Every week",
        "fortnightly": "Every 2 weeks",
        "monthly": "Every month",
    }

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.Enum(*KINDS, name="calendar_item_kind"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    # For recurring items (activities) this is the first occurrence
    date = db.Column(db.Date, nullable=False, index=True)
    # Both empty = all day; tasks only use start_time (as a due time)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    location = db.Column(db.String(200), nullable=False, default="")
    notes = db.Column(db.Text)
    # Recurrence: NULL frequency = happens once; repeat_until (inclusive) NULL = repeats forever
    frequency = db.Column(db.Enum(*FREQUENCIES, name="calendar_item_frequency"))
    repeat_until = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def occurrences(self, start, end):
        """Dates in [start, end) on which this item happens."""
        last = min(end - timedelta(days=1), self.repeat_until or end)
        if not self.frequency:
            return [self.date] if start <= self.date <= last else []

        if self.frequency == "monthly":
            # Same day of the month; months without that day (e.g. the 31st) are skipped
            dates = []
            year, month = self.date.year, self.date.month
            while (year, month) <= (last.year, last.month):
                if self.date.day <= calendar.monthrange(year, month)[1]:
                    d = self.date.replace(year=year, month=month)
                    if d >= start and d <= last:
                        dates.append(d)
                year, month = (year + 1, 1) if month == 12 else (year, month + 1)
            return dates

        step = timedelta(days={"daily": 1, "weekly": 7, "fortnightly": 14}[self.frequency])
        d = self.date
        if d < start:
            # Jump to the first occurrence on or after start
            d += step * -(-(start - d).days // step.days)
        dates = []
        while d <= last:
            dates.append(d)
            d += step
        return dates
