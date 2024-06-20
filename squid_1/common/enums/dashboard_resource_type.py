from enum import Enum


class DashboardResourceType(Enum):
    AWS_ACCOUNTS = "cspAccounts"
    AWS_VMS = "cspMachines"
    AWS_VOLUMES = "cspVolumes"
    DATA_STORES = "dataStores"
    VCENTERS = "vCenters"
    VCENTER_VMS = "virtualMachines"
    RDS = "cspRDS"
