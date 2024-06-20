from enum import Enum


class ProtectionStatus(Enum):
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"
    LAPSED = "LAPSED"
    PROTECTED = "PROTECTED"
    UNPROTECTED = "UNPROTECTED"
    PAUSED = "PAUSED"
