from enum import Enum


# Protection job schedule status values in assets
class ScheduleStatus(Enum):
    NOT_RUN = "NOT_RUN"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PAUSED = "PAUSED"
