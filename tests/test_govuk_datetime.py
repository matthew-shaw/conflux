from datetime import datetime, timedelta

import pytest

from app.utils.govuk_datetime import format_govuk_datetime, format_govuk_duration


@pytest.mark.parametrize(
    "dt,include_time,include_day,include_year,truncate_month,expected",
    [
        # With time, day, and year
        (
            datetime(2022, 6, 14, 23, 59),
            True,
            True,
            True,
            False,
            "11:59pm on Tuesday 14 June 2022",
        ),
        # Midnight
        (
            datetime(2024, 12, 25, 0, 0),
            True,
            True,
            True,
            False,
            "midnight on Wednesday 25 December 2024",
        ),
        # Midday
        (
            datetime(2024, 12, 25, 12, 0),
            True,
            True,
            True,
            False,
            "midday on Wednesday 25 December 2024",
        ),
        # No year
        (
            datetime(2023, 5, 1, 17, 30),
            True,
            True,
            False,
            False,
            "5:30pm on Monday 1 May",
        ),
        # Date only
        (
            datetime(2023, 5, 1),
            False,
            True,
            True,
            False,
            "Monday 1 May 2023",
        ),
        # Minimal date only
        (
            datetime(2023, 5, 1),
            False,
            False,
            False,
            False,
            "1 May",
        ),
        # Truncated month
        (
            datetime(2023, 2, 14),
            False,
            True,
            True,
            True,
            "Tuesday 14 Feb 2023",
        ),
        # Truncated month with time
        (
            datetime(2023, 8, 30, 15, 0),
            True,
            True,
            True,
            True,
            "3pm on Wednesday 30 Aug 2023",
        ),
        # Truncated month with no day or year
        (
            datetime(2023, 8, 30),
            False,
            False,
            False,
            True,
            "30 Aug",
        ),
    ],
)
def test_format_govuk_datetime_variants(dt, include_time, include_day, include_year, truncate_month, expected):
    result = format_govuk_datetime(
        dt,
        include_time=include_time,
        include_day=include_day,
        include_year=include_year,
        truncate_month=truncate_month,
    )
    assert result == expected


def test_format_govuk_datetime_invalid_input():
    with pytest.raises(TypeError):
        format_govuk_datetime("2022-06-14")  # type: ignore


@pytest.mark.parametrize(
    "td,expected",
    [
        (timedelta(hours=6, minutes=30), "6 hours 30 minutes"),
        (timedelta(hours=1), "1 hour"),
        (timedelta(minutes=45), "45 minutes"),
        (timedelta(), "0 minutes"),
        (timedelta(hours=1, minutes=1), "1 hour 1 minute"),
        (timedelta(hours=2, minutes=0), "2 hours"),
        (timedelta(minutes=1), "1 minute"),
        (timedelta(hours=24), "24 hours"),
        (timedelta(minutes=0), "0 minutes"),
    ],
)
def test_format_govuk_duration_exact(td, expected):
    result = format_govuk_duration(td)
    assert result == expected


def test_format_govuk_duration_invalid_input():
    with pytest.raises(TypeError):
        format_govuk_duration("2 hours")  # type: ignore
