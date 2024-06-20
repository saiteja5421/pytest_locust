import logging

from storage_proto.cloudobjectstores.v1 import stores_pb2
from storage_proto.cloudobjectstores.v1.service_pb2_grpc import CloudObjectStoreManagerServiceStub

from lib.common.enums.cvsa_rop import RopActions
from lib.platform.kafka.protobuf.ropcvsamanager.v1alpha1 import cvsamanager_pb2 as ropcvsamanager_pb2
from tests.functional.aws_protection.cvsa_manager.constants import (
    get_cvsa_manager_grpc_metadata,
    get_grpc_cloud_object_store_service_stub,
)


def get_object_stores_by_cvsa_id(service_stub: CloudObjectStoreManagerServiceStub, cvsa_id: str):
    label = stores_pb2.Label(key="cvsa-id", value=cvsa_id)
    request = stores_pb2.ListObjectStoresRequest(filter={"labels": [label]}, service_id="cvsa-manager")
    object_stores = service_stub.ListObjectStores(request=request)
    return object_stores


def grpc_list_cvsas(grpc_service_stub, cvsa_id: str):
    listed_cvsas = grpc_service_stub.ListCVSAs(
        request=ropcvsamanager_pb2.ListCVSAsRequest(filter={"cvsa_id": cvsa_id}),
        metadata=get_cvsa_manager_grpc_metadata(),
    )
    return listed_cvsas


def grpc_trigger_cvsa_maintenance_operation(grpc_service_stub, cvsa_id: str, action: RopActions):
    response = grpc_service_stub.TriggerCVSAMaintenanceOperation(
        request=ropcvsamanager_pb2.TriggerCVSAMaintenanceOperationRequest(
            cvsa_id=cvsa_id, operation=RopActions.DEBUG, action=action
        ),
        metadata=get_cvsa_manager_grpc_metadata(),
    )
    return response


def is_cosm_enabled() -> bool:
    try:
        get_grpc_cloud_object_store_service_stub()
        logging.info("COSM is enabled")
        return True
    except Exception as e:
        logging.error(f"COSM is not enabled due to an error: {e}")
        return False
