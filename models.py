from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ICalFeed(db.Model):
    """An iCal (.ics) feed URL to import calendar items from."""

    __tablename__ = "ical_feeds"

    # 768 chars is MySQL's limit for an indexed utf8mb4 column (3072 bytes)
    url = db.Column(db.String(768), primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
