from enum import IntEnum

from lib.platform.kafka.protobuf.ropcvsamanager.v1alpha1 import cvsamanager_pb2 as ropcvsamanager_pb2


class RopActions:
    DEBUG = (
        ropcvsamanager_pb2.TriggerCVSAMaintenanceOperationRequest.TriggerCVSAMaintenanceOperationTypeEnum.TRIGGER_CVSA_MAINTENANCE_OPERATION_TYPE_ENUM_DEBUG
    )
    ACTION_START = (
        ropcvsamanager_pb2.TriggerCVSAMaintenanceOperationRequest.TriggerCVSAMaintenanceOperationActionEnum.TRIGGER_CVSA_MAINTENANCE_OPERATION_ACTION_ENUM_START
    )
    ACTION_STOP = (
        ropcvsamanager_pb2.TriggerCVSAMaintenanceOperationRequest.TriggerCVSAMaintenanceOperationActionEnum.TRIGGER_CVSA_MAINTENANCE_OPERATION_ACTION_ENUM_STOP
    )


class MaintenanceMode(IntEnum):
    OFF = 1
    DEBUG = 4


class InstanceState(IntEnum):
    RUNNING = 1


class ResponseResult(IntEnum):
    ACCEPTED = 1
