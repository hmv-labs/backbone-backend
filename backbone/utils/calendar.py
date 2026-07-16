import datetime
import logging
from collections import defaultdict
from typing import Type

from django.db.models.query import QuerySet
from django.utils.timezone import make_aware
from rest_framework.serializers import Serializer

logger = logging.getLogger(__file__)


def get_days(year: int, month: int, week_start: str = "monday"):
    """
    Returns exactly 42 days (6 weeks) for a calendar month view.

    Each item:
    {
        "date": "YYYY-MM-DD",
        "is_in_current_month": bool
    }

    week_start:
        - "monday" (ISO, default)
        - "sunday"
    """
    if week_start not in {"monday", "sunday"}:
        raise ValueError("week_start must be 'monday' or 'sunday'")

    first_day = datetime.date(year, month, 1)

    if week_start == "monday":
        # Monday = 0, Sunday = 6
        start_offset = first_day.weekday()
    else:
        # Sunday = 0, Saturday = 6
        start_offset = (first_day.weekday() + 1) % 7

    # First cell in the calendar grid
    start_date = first_day - datetime.timedelta(days=start_offset)

    days = []
    for i in range(42):  # 6 weeks × 7 days
        current = start_date + datetime.timedelta(days=i)
        days.append(current.isoformat())

    return days


def get_daily_events(
    *,
    queryset: QuerySet,
    serializer_class: Type[Serializer],
    datetime_field: str = "created_at",
    month: str | None = None,  # eg: "2026-05"
):
    days = []
    if month:
        try:
            year, mon = month.split("-")
            days = get_days(int(year), int(mon))
        except Exception as exc:
            logger.error(exc)

    if not days:
        now = datetime.datetime.now()
        days = get_days(now.year, now.month)

    start_dt = make_aware(
        datetime.datetime.combine(
            datetime.datetime.fromisoformat(days[0]).date(), datetime.time.min
        )
    )

    end_dt = make_aware(
        datetime.datetime.combine(
            datetime.datetime.fromisoformat(days[-1]).date(), datetime.time.max
        )
    )

    queryset = queryset.filter(**{f"{datetime_field}__range": (start_dt, end_dt)})

    qs_data = defaultdict(list)

    for item in queryset.iterator():
        qs_data[getattr(item, datetime_field).strftime("%Y-%m-%d")].append(item)

    results = []

    for day in days:
        results.append(
            {
                "date": day,
                "events": serializer_class(
                    sorted(
                        qs_data.get(day, []), key=lambda i: getattr(i, datetime_field)
                    ),
                    many=True,
                ).data,
            }
        )

    return results
