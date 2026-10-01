from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.types import DateTime, TypeDecorator


CAIRO_TZ = ZoneInfo("Africa/Cairo")


def cairo_now() -> datetime:
    return datetime.now(CAIRO_TZ)


def cairo_today() -> date:
    return cairo_now().date()


class CairoDateTime(TypeDecorator):
    """Store UTC, return aware Cairo time on both SQLite and PostgreSQL."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime values must be timezone-aware")
        utc_value = value.astimezone(timezone.utc)
        # SQLite drops timezone information; a naive UTC value is unambiguous.
        return utc_value.replace(tzinfo=None) if dialect.name == "sqlite" else utc_value

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return utc_value.astimezone(CAIRO_TZ)
