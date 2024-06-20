from enum import Enum
from itertools import chain

import lib.platform.kafka.protobuf.cvsa_manager.cvsa_manager_pb2 as cvsa_manager_pb2


class CloudProvider(Enum):
    AWS = cvsa_manager_pb2.CLOUD_PROVIDER_ENUM_AWS
    AZURE = cvsa_manager_pb2.CLOUD_PROVIDER_ENUM_AZURE

    def __str__(self):
        return "CLOUD_PROVIDER_ENUM_" + str(self.name)


class AwsRegions(Enum):
    AWS_US_EAST_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_US_EAST_1
    AWS_US_EAST_2 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_US_EAST_2
    AWS_US_WEST_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_US_WEST_1
    AWS_US_WEST_2 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_US_WEST_2

    AWS_EU_CENTRAL_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_EU_CENTRAL_1
    AWS_EU_WEST_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_EU_WEST_1
    AWS_EU_WEST_2 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_EU_WEST_2
    AWS_EU_WEST_3 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_EU_WEST_3
    AWS_EU_NORTH_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_EU_NORTH_1

    AWS_CA_CENTRAL_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_CA_CENTRAL_1

    AWS_AP_NORTHEAST_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_AP_NORTHEAST_1
    AWS_AP_NORTHEAST_2 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_AP_NORTHEAST_2
    AWS_AP_NORTHEAST_3 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_AP_NORTHEAST_3
    AWS_AP_SOUTHEAST_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_AP_SOUTHEAST_1
    AWS_AP_SOUTHEAST_2 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_AP_SOUTHEAST_2
    AWS_AP_SOUTH_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_AP_SOUTH_1

    AWS_ME_SOUTH_1 = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AWS_ME_SOUTH_1

    def __str__(self):
        return "CLOUD_REGION_ENUM_REGION_ENUM_" + str(self.name)


class AzureRegions(Enum):
    AZURE_EASTUS = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AZURE_EASTUS
    AZURE_CENTRALUS = cvsa_manager_pb2.CLOUD_REGION_ENUM_REGION_ENUM_AZURE_CENTRALUS

    def __str__(self):
        return "CLOUD_REGION_ENUM_REGION_ENUM_" + str(self.name)


CloudRegions = Enum("CloudRegions", [(i.name, i.value) for i in chain(AwsRegions, AzureRegions)])


class ProtectedAssetType(Enum):
    AWS_EBS = cvsa_manager_pb2.PROTECTED_ASSET_TYPE_ENUM_AWS_EBS

    def __str__(self):
        return "PROTECTED_ASSET_TYPE_ENUM_" + str(self.name)


class CloudVolumeType(Enum):
    AWS_GP3 = cvsa_manager_pb2.CLOUD_VOLUME_TYPE_ENUM_AWS_GP3
    AZURE_PREMIUMSSD = cvsa_manager_pb2.CLOUD_VOLUME_TYPE_ENUM_AZURE_PREMIUMSSD

    def __str__(self):
        return "CLOUD_VOLUME_TYPE_ENUM_" + str(self.name)


class StopReason(Enum):
    CUSTOMER_UNREGISTER = cvsa_manager_pb2.CVSA_STOP_REASON_ENUM_CUSTOMER_UNREGISTER
    IDLE = cvsa_manager_pb2.CVSA_STOP_REASON_ENUM_IDLE
    RESIZE = cvsa_manager_pb2.CVSA_STOP_REASON_ENUM_RESIZE
    UNHEALTHY = cvsa_manager_pb2.CVSA_STOP_REASON_ENUM_UNHEALTHY
    ORPHANED = cvsa_manager_pb2.CVSA_STOP_REASON_ENUM_ORPHANED
    DISASTER_RECOVERY = cvsa_manager_pb2.CVSA_STOP_REASON_ENUM_DISASTER_RECOVERY

    def __str__(self):
        return "CVSA_STOP_REASON_ENUM_" + str(self.name)


class TerminateReason(Enum):
    ORPHANED = cvsa_manager_pb2.CVSA_TERMINATE_REASON_ENUM_ORPHANED
    MAINTENANCE = cvsa_manager_pb2.CVSA_TERMINATE_REASON_ENUM_MAINTENANCE
    CUSTOMER_UNREGISTER = cvsa_manager_pb2.CVSA_TERMINATE_REASON_ENUM_CUSTOMER_UNREGISTER
    READ_ONLY_REQUEST_FINISHED = cvsa_manager_pb2.CVSA_TERMINATE_REASON_ENUM_READ_ONLY_REQUEST_FINISHED

    def __str__(self):
        return "CVSA_TERMINATE_REASON_ENUM_" + str(self.name)


class MaintenanceAction(Enum):
    START = cvsa_manager_pb2.CVSA_MAINTENANCE_ACTION_ENUM_START
    STOP = cvsa_manager_pb2.CVSA_MAINTENANCE_ACTION_ENUM_STOP
    ERROR = cvsa_manager_pb2.CVSA_MAINTENANCE_ACTION_ENUM_ERROR

    def __str__(self):
        return "CVSA_MAINTENANCE_ACTION_ENUM_" + str(self.name)


class MaintenanceOperation(Enum):
    DISASTER_RECOVERY = cvsa_manager_pb2.CVSA_MAINTENANCE_OPERATION_TYPE_ENUM_DISASTER_RECOVERY
    UPGRADE = cvsa_manager_pb2.CVSA_MAINTENANCE_OPERATION_TYPE_ENUM_UPGRADE
    DEBUG = cvsa_manager_pb2.CVSA_MAINTENANCE_OPERATION_TYPE_ENUM_DEBUG

    def __str__(self):
        return "CVSA_MAINTENANCE_OPERATION_TYPE_ENUM_" + str(self.name)


class VaultCredentialType(Enum):
    ADMIN = "admin-credentials"
    CATALYST_STORE_CLIENT = "catalyst-store-client-credentials"
    CATALYST_STORE = "catalyst-store-credentials"
    CATALYST_STORE_ENCRYPTION_KEY = "catalyst-store-encryption-key"
    CONSOLE = "console-credentials"


class CspAccountInfoStatus(Enum):
    STATUS_UNSPECIFIED = 0
    STATUS_REGISTERED = 1
    STATUS_UNREGISTERED = 2
    STATUS_UNREGISTERING = 3


class RequestFinishedStatus(Enum):
    STATUS_UNSPECIFIED = 0
    STATUS_OK = 1
    STATUS_ERROR = 2


class RequestType(Enum):
    BACKUP = cvsa_manager_pb2.CVSA_REQUEST_TYPE_BACKUP
    RESTORE = cvsa_manager_pb2.CVSA_REQUEST_TYPE_RESTORE
    DELETE = cvsa_manager_pb2.CVSA_REQUEST_TYPE_DELETE
    BACKUP_SINGLE_ASSET = cvsa_manager_pb2.CVSA_REQUEST_TYPE_BACKUP_SINGLE_ASSET

    def __str__(self):
        return "CVSA_REQUEST_TYPE_" + str(self.name)


class CvsaType(Enum):
    BACKUP = "backup"
    RESTORE = "restore"
    RESTORE_FLR = "restore-flr"
