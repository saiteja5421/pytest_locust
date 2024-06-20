from enum import Enum


class VmPowerOption(Enum):
    on = "poweredOn"
    off = "poweredOff"
    suspend = "suspended"
    unknown = "unknown"
