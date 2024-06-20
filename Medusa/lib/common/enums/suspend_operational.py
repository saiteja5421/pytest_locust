from enum import Enum


class SuspendOperational(Enum):
    ensure = "ENSURE"
    active = "ACTIVE"
    suspended = "SUSPENDED"
    partially_suspended = "PARTIALLY_SUSPENDED"
