from enum import Enum


class DualAuthRequest(Enum):
    CANCELLED = "Canceled"
    APPROVED = "Approved"


class DualAuthSettingValue(Enum):
    ON = "ON"
    OFF = "OFF"
