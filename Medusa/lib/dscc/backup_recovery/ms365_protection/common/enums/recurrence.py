from enum import Enum


class Recurrence(Enum):
    CALENDAR_RECURRENCE_DAILY_RECURRENCE = "CALENDAR_RECURRENCE_DAILY_RECURRENCE"
    CALENDAR_RECURRENCE_WEEKLY_RECURRENCE = "CALENDAR_RECURRENCE_WEEKLY_RECURRENCE"
    CALENDAR_RECURRENCE_ABSOLUTE_MONTHLY_RECURRENCE = "CALENDAR_RECURRENCE_ABSOLUTE_MONTHLY_RECURRENCE"
    CALENDAR_RECURRENCE_RELATIVE_MONTHLY_RECURRENCE = "CALENDAR_RECURRENCE_RELATIVE_MONTHLY_RECURRENCE"
    CALENDAR_RECURRENCE_ABSOLUTE_YEARLY_RECURRENCE = "CALENDAR_RECURRENCE_ABSOLUTE_YEARLY_RECURRENCE"
    CALENDAR_RECURRENCE_RELATIVE_YEARLY_RECURRENCE = "CALENDAR_RECURRENCE_RELATIVE_YEARLY_RECURRENCE"


class PatternType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    ABSOLUTEMONTHLY = "absoluteMonthly"
    RELATIVEMONTHLY = "relativeMonthly"
    ABSOLUTEYEARLY = "absoluteYearly"
    RELATIVEYEARLY = "relativeYearly"


class DaysOfWeek(Enum):
    SUNDAY = "sunday"
    MONDAT = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURDSAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"


class PatternIndex(Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    LAST = "last"


class RecurrenceRangeType(Enum):
    ENDDATE = "endDate"
    NOEND = "noEnd"
    NUMBERED = "numbered"