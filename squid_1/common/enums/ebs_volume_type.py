from enum import Enum


class EBSVolumeType(Enum):
    GP2 = "gp2"
    GP3 = "gp3"
    IO1 = "io1"
    IO2 = "io2"
    ST1 = "st1"
    SC1 = "sc1"
    STANDARD = "standard"
