from enum import Enum


class ScheduleType(Enum):
    MINUTES = "BY_MINUTES"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
