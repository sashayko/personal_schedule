from datetime import datetime

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

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.Enum(*KINDS, name="calendar_item_kind"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    # Both empty = all day; tasks only use start_time (as a due time)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    location = db.Column(db.String(200), nullable=False, default="")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
