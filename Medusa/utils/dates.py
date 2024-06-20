from datetime import datetime, timedelta
from typing import Union
from dateutil import parser


def parse_to_iso8601(date_time: str, time_offset_minutes=0):
    datetime_parsed = datetime.strptime(date_time, "%a, %d %b %Y %H:%M:%S %Z")
    datetime_calculated = datetime_parsed - timedelta(minutes=time_offset_minutes)
    datetime_formated = datetime_calculated.strftime("%Y-%m-%dT%H:%M:%SZ")

    return datetime_formated


def get_iso8601():
    datetime_formated = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    return datetime_formated


def datetime_to_iso8601(date_time: datetime):
    datetime_formated = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return datetime_formated


def compare_dates(date_new: Union[datetime, str], date_old: Union[datetime, str], days_offset: int = 2) -> bool:
    date_new = date_new if isinstance(date_new, datetime) else parser.parse(date_new).replace(tzinfo=None)
    date_old = date_old if isinstance(date_old, datetime) else parser.parse(date_old).replace(tzinfo=None)
    delta_days = date_new - date_old
    if delta_days.days < days_offset:
        return True
    return False
