"""
TC82: Maintenance Debug Mode allows to process requests
     1. Start backup instance,
     2. Trigger debug mode start,
     3. Wait for event maintenance debug event started,
     4. Start another backup instance,
     5. Verify ready event
"""

import logging

from pytest import mark

from lib.common.enums.cvsa import (
    MaintenanceAction,
    MaintenanceOperation,
)
from lib.common.enums.cvsa_rop import RopActions, InstanceState, MaintenanceMode
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from lib.platform.kafka.protobuf.ropcvsamanager.v1alpha1.cvsamanager_pb2_grpc import CVSAManagerCrossClusterServiceStub
from tests.functional.aws_protection.cvsa_manager.localstack.test_tc75 import (
    trigger_debug_mode,
)
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_ready_event,
)
from tests.steps.aws_protection.cvsa.grpc_steps import grpc_list_cvsas
from tests.steps.aws_protection.cvsa.kafka_steps import verify_maintenance_event


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc82(kafka_mgr: KafkaManager, aws: CloudVmManager, grpc_service_stub: CVSAManagerCrossClusterServiceStub):
    logging.info("Step 1. Start instance backup as prerequisite")
    create_new_cvsa_instance_and_validate(kafka_mgr, aws, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    logging.info("Step 2. Trigger debug mode start")
    trigger_debug_mode(kafka=kafka_mgr, stub_service=grpc_service_stub, rop_action=RopActions.ACTION_START)

    logging.info("Step 3. wait for event maintenance debug event started")
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.START,
        operation_type=MaintenanceOperation.DEBUG,
    )

    logging.info("Step 3.1 Verify if List endpoint returns valid information about the cVSA instance.")
    verify_valid_information_about_the_cvsa_instance(grpc_service_stub=grpc_service_stub, kafka_mgr=kafka_mgr)

    logging.info("Step 4. Start instance backup of 2nd instance")
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_ready_event(kafka_mgr)


def verify_valid_information_about_the_cvsa_instance(grpc_service_stub, kafka_mgr):
    list_cvsa_response = grpc_list_cvsas(grpc_service_stub=grpc_service_stub, cvsa_id=kafka_mgr.cvsa_id)
    maintenance_state = list_cvsa_response.cvsas[0].maintenance
    cvsa_state = list_cvsa_response.cvsas[0].state

    assert len(list_cvsa_response.cvsas) == 1, "Expected to get one cVSA instance while filtering by particular cVSA id"
    assert maintenance_state == MaintenanceMode.DEBUG, f"Debug mode is not ON, instead got {maintenance_state}"
    assert cvsa_state == InstanceState.RUNNING, f"Expected cVSA state is 'running', instead got {cvsa_state}"
