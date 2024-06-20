"""
TC75: Maintenance debug mode events are emitted
     1. Start backup instance,
     2. Trigger debug mode start,
     3. Wait for event maintenance debug event started,
     4. Trigger debug mode stop,
     5. Wait for event maintenance debug event stopped,
"""
import logging
from time import sleep

from pytest import mark
from waiting import wait

from lib.common.enums.cvsa import (
    MaintenanceAction,
    MaintenanceOperation,
    StopReason,
)
from lib.common.enums.cvsa_rop import RopActions, InstanceState, MaintenanceMode, ResponseResult
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from lib.platform.kafka.protobuf.ropcvsamanager.v1alpha1.cvsamanager_pb2_grpc import CVSAManagerCrossClusterServiceStub
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
)
from tests.steps.aws_protection.cvsa.grpc_steps import grpc_list_cvsas, grpc_trigger_cvsa_maintenance_operation
from tests.steps.aws_protection.cvsa.kafka_steps import verify_maintenance_event


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc75(kafka_mgr: KafkaManager, aws: CloudVmManager, grpc_service_stub: CVSAManagerCrossClusterServiceStub):
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
    list_cvsa_response = grpc_list_cvsas(grpc_service_stub=grpc_service_stub, cvsa_id=kafka_mgr.cvsa_id)
    maintenance_state = list_cvsa_response.cvsas[0].maintenance
    cvsa_state = list_cvsa_response.cvsas[0].state

    assert len(list_cvsa_response.cvsas) == 1, "Expected to get one cVSA instance while filtering by particular cVSA id"
    assert maintenance_state == MaintenanceMode.DEBUG, f"Debug mode is not ON, instead got {maintenance_state}"
    assert cvsa_state == InstanceState.RUNNING, f"Expected cVSA state is 'running', instead got {cvsa_state}"

    logging.info("Step 4. Trigger debug mode stop")
    trigger_debug_mode(kafka=kafka_mgr, stub_service=grpc_service_stub, rop_action=RopActions.ACTION_STOP)

    logging.info("Step 5. Wait for event maintenance debug event stopped,")
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.STOP,
        operation_type=MaintenanceOperation.DEBUG,
    )

    logging.info("Step 5.1 Verify if List endpoint returns valid information about the cVSA instance.")
    verify_maintenance_state(grpc_service_stub, kafka_mgr.cvsa_id, MaintenanceMode.OFF)
    verify_stopped_event(kafka_mgr, reason=StopReason.IDLE)


def trigger_debug_mode(kafka, stub_service, rop_action=RopActions.ACTION_START):
    while True:
        response = grpc_trigger_cvsa_maintenance_operation(
            grpc_service_stub=stub_service, cvsa_id=kafka.cvsa_id, action=rop_action
        )
        sleep(5)
        if response.result == ResponseResult.ACCEPTED:
            break


def verify_maintenance_state(
    grpc_service_stub: CVSAManagerCrossClusterServiceStub, cvsa_id: str, mode: MaintenanceMode
):
    def verify_maintenance_state_iter():
        try:
            list_cvsa_response = grpc_list_cvsas(grpc_service_stub=grpc_service_stub, cvsa_id=cvsa_id)
            if len(list_cvsa_response.cvsas) == 0:
                logging.info(f"Step 5.1: verify_maintenance_state: empty list_cvsas response")
                return False
            maintenance_state = list_cvsa_response.cvsas[0].maintenance
            if maintenance_state != mode:
                logging.info(
                    f"Step 5.1: verify_maintenance_state condition not met: want={mode}, got={maintenance_state}"
                )
                return False
            return True
        except Exception as e:
            logging.error(f"Step 5.1: verify_maintenance_state failed: {e}")

    wait(
        lambda: verify_maintenance_state_iter(),
        timeout_seconds=300,
        sleep_seconds=5,
    )
