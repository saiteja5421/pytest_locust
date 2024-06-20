from enum import Enum


class BackupKafkaEventStatus(Enum):
    SUCCESS = "EVENT_STATUS_SUCCESS"
    FAILURE = "EVENT_STATUS_FAILURE"
