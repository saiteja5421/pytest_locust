from enum import Enum


class SSMCommandType(Enum):
    WINDOWS = "AWS-RunPowerShellScript"
    LINUX = "AWS-RunShellScript"
