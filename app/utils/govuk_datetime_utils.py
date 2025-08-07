from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


def format_govuk_datetime(
    dt: datetime,
    include_time: bool = False,
    include_day: bool = True,
    include_year: bool = True,
    truncate_month: bool = False,
) -> str:
    """
    Format a datetime object according to the GOV.UK Style Guide.

    Examples:
    - 'Tuesday 14 June 2022'
    - '11:59pm on Tuesday 14 June 2022'
    - 'midnight on Tuesday 14 June'
    - Truncated month example: 'Tuesday 14 Jun 2022'

    :param dt: A datetime object
    :param include_time: Whether to include time in the string
    :param include_day: Whether to include the day of the week
    :param include_year: Whether to include the year
    :param truncate_month: Whether to use abbreviated month names (e.g., Jan, Feb)
    """
    if not isinstance(dt, datetime):
        raise TypeError("Expected a datetime object")

    # Convert to UK time
    dt = dt.astimezone(ZoneInfo("Europe/London"))

    t: time = dt.time()

    # Time formatting
    if t == time(0, 0):
        time_str: str = "midnight"
    elif t == time(12, 0):
        time_str = "midday"
    else:
        time_str = dt.strftime("%-I:%M%p").lower().replace(":00", "")

    # Date formatting
    date_parts: list[str] = []
    if include_day:
        date_parts.append(dt.strftime("%A"))
    date_parts.append(dt.strftime("%-d"))
    date_parts.append(dt.strftime("%b" if truncate_month else "%B"))
    if include_year:
        date_parts.append(dt.strftime("%Y"))

    date_str: str = " ".join(date_parts)

    return f"{time_str} on {date_str}" if include_time else date_str


def format_govuk_duration(td: timedelta) -> str:
    """
    Format a timedelta according to the GOV.UK Style Guide.

    Examples:
    - '6 hours 30 minutes'
    - '1 hour'
    - '45 minutes'
    - '0 minutes'
    """
    if not isinstance(td, timedelta):
        raise TypeError("Expected a timedelta object")

    total_minutes: int = int(td.total_seconds() // 60)
    hours: int
    minutes: int
    hours, minutes = divmod(total_minutes, 60)

    parts: list[str] = []
    if hours > 0:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
    if minutes > 0 or not parts:
        parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))

    return " ".join(parts)
