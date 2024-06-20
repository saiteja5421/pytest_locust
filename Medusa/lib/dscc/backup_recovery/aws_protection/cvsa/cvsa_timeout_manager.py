import os
from enum import Enum

is_localstack = os.getenv("LOCALSTACK_URL")


class Timeout(Enum):
    CREATED_EVENT = 300 if is_localstack else 1800
    STARTED_EVENT = 300 if is_localstack else 1800
    RESIZED_EVENT = 300 if is_localstack else 1800
    REQUESTED_EVENT = 60
    REQUEST_FINISHED_EVENT = 60
    READY_EVENT = 300 if is_localstack else 1800
    STOPPED_EVENT = 300 if is_localstack else 1800
    STOPPED_EVENT_ORPHANED = 600 if is_localstack else 1800
    STOPPED_EVENT_IDLE = 900 if is_localstack else 7200
    TERMINATED_EVENT = 300 if is_localstack else 1800
    MAINTENANCE_EVENT = 600 if is_localstack else 1800
    MAINTENANCE_EVENT_DEBUG = 300 if is_localstack else 1800
    MAINTENANCE_EVENT_DR_START = 600 if is_localstack else 3900
    MAINTENANCE_EVENT_DR_STOP = 600 if is_localstack else 1800
    MAINTENANCE_EVENT_UPGRADE_START = 1800 if is_localstack else 3900
    MAINTENANCE_EVENT_UPGRADE_STOP = 600 if is_localstack else 1800
    MAINTENANCE_EVENT_UPGRADE_ERROR = 600 if is_localstack else 1800
    STARTED_EVENT_DURING_MAINTENANCE = 300 if is_localstack else 1800
    UNREGISTER_EVENT = 60
    REGISTER_EVENT = 60
    STORE_DELETED_EVENT = 900
    BILLING_EVENT = 900
    UNPROTECT_FINISHED_EVENT = 360
