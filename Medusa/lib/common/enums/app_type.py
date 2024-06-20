from enum import Enum


class AppType(Enum):
    all = "ALL"
    vmware = "VMWARE"
    aws = "AWS"
    ms365 = "MS365"
    hpe_array_volume = "HPE_ARRAY_VOLUME"
    mssql = "MSSQL"
    azure = "AZURE"
    unknown = "UNKNOWN"
