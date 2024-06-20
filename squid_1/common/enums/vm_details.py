from dataclasses import dataclass
from enum import Enum


@dataclass
class VmInstanceDetails:
    instance_type: str
    cpu: int
    ram: int


class VmDetails(Enum):
    STANDARD_F2S_v2 = VmInstanceDetails("Standard_F2s_v2", 2, 4)
    STANDARD_F4S_v2 = VmInstanceDetails("Standard_F4s_v2", 4, 8)
    STANDARD_F8S_v2 = VmInstanceDetails("Standard_F8s_v2", 8, 16)
    STANDARD_F16S_v2 = VmInstanceDetails("Standard_F16s_v2", 16, 32)
    STANDARD_F32s_v2 = VmInstanceDetails("Standard_F32s_v2", 32, 64)
