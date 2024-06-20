from dataclasses import dataclass
from enum import Enum


@dataclass
class VmInstanceDetails:
    instance_type: str
    cpu: int
    ram: int


class VmDetails(Enum):
    Standard_E2S_v5 = VmInstanceDetails("Standard_E2s_v5", 2, 16)
    Standard_D4ls_v5 = VmInstanceDetails("Standard_D4ls_v5", 4, 8)
    Standard_D4S_v5 = VmInstanceDetails("Standard_D4s_v5", 4, 16)
    Standard_E4s_v5 = VmInstanceDetails("Standard_E4s_v5", 4, 32)
    Standard_D8ls_v5 = VmInstanceDetails("Standard_D8ls_v5", 8, 16)
    Standard_D8s_v5 = VmInstanceDetails("Standard_D8s_v5", 8, 32)
    Standard_E8S_v5 = VmInstanceDetails("Standard_E8s_v5", 8, 64)
    Standard_D16ls_v5 = VmInstanceDetails("Standard_D16ls_v5", 16, 32)
    Standard_D16S_v5 = VmInstanceDetails("Standard_D16s_v5", 16, 64)
    Standard_E16s_v5 = VmInstanceDetails("Standard_E16s_v5", 16, 128)
    Standard_E20s_v5 = VmInstanceDetails("Standard_E20s_v5", 20, 160)
    Standard_D32ls_v5 = VmInstanceDetails("Standard_D32ls_v5", 32, 64)
    Standard_D32s_v5 = VmInstanceDetails("Standard_D32s_v5", 32, 128)
    Standard_E32s_v5 = VmInstanceDetails("Standard_E32s_v5", 32, 256)
    Standard_D48ls_v5 = VmInstanceDetails("Standard_D48ls_v5", 48, 96)
    Standard_D48s_v5 = VmInstanceDetails("Standard_D48s_v5", 48, 192)
    Standard_D64ls_v5 = VmInstanceDetails("Standard_D64ls_v5", 64, 128)
    Standard_E48s_v5 = VmInstanceDetails("Standard_E48s_v5", 48, 384)
    Standard_D64s_v5 = VmInstanceDetails("Standard_D64s_v5", 64, 256)
    Standard_E64s_v5 = VmInstanceDetails("Standard_E64s_v5", 64, 512)
    Standard_D96s_v5 = VmInstanceDetails("Standard_D96s_v5", 96, 384)
    Standard_E96s_v5 = VmInstanceDetails("Standard_E96s_v5", 96, 672)
