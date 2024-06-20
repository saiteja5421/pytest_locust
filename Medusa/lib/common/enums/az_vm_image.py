"""
CLI: az vm image list --output table
"""

from enum import Enum
from azure.mgmt.compute.models import ImageReference


class AZVMImage(Enum):
    CENT_OS = ImageReference(publisher="OpenLogic", offer="CentOS", sku="7.5", version="latest")
    DEBIAN = ImageReference(publisher="Debian", offer="debian-10", sku="10", version="latest")
    SUSE = ImageReference(publisher="SUSE", offer="opensuse-leap-15-3", sku="gen2", version="latest")
    RHEL = ImageReference(
        publisher="Canonical", offer="0001-com-ubuntu-server-jammy", sku="22_04-lts-gen2", version="latest"
    )
    WINDOWS_SERVER = ImageReference(
        publisher="MicrosoftWindowsServer", offer="WindowsServer", sku="2022-datacenter-g2", version="latest"
    )
