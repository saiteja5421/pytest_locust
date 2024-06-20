from enum import Enum


class CommandType(Enum):
    Powershell = "Powershell"
    CMD = "CMD"


class AZCommandType(Enum):
    SHELL = "RunShellScript"
    POWERSHELL = "RunPowerShellScript"
