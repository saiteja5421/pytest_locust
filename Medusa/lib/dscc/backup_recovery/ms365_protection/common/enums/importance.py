from enum import Enum


class Importance(Enum):
    IMPORTANCE_LOW = "IMPORTANCE_LOW"
    IMPORTANCE_NORMAL = "IMPORTANCE_NORMAL"
    IMPORTANCE_HIGH = "IMPORTANCE_HIGH"


class MS365Importance(Enum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
