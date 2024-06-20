"""
TC75: RDA IDA is enabled on real cVSA Instance
    1. Start backup instance,
    2. Trigger debug mode start, [gRPC CALL]
    3. Wait for event maintenance debug event started, // cvsa manager emits event
    4. Wait for cVSA to respond with idaStatus: true
    5. Set 'idaStatus: false' from tests,
    6. Wait for cVSA to respond with idaStatus: true (should be fixed by desired state)
    7. Trigger debug mode stop,  [gRPC CALL]
    8. Wait for event maintenance debug event stopped,
"""

import logging
from time import sleep

from pytest import mark

from lib.common.enums.cvsa import (
    MaintenanceAction,
    MaintenanceOperation,
    StopReason,
)
from lib.common.enums.cvsa_rop import ResponseResult, RopActions, MaintenanceMode, InstanceState
from lib.platform.aws_boto3.aws_factory import AWS
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
from tests.steps.aws_protection.cvsa.storeonce_steps import get_cvsa_storeonce


@mark.cvsa_aws
@mark.cvsa_cloud
def test_tc75(kafka_mgr: KafkaManager, aws: CloudVmManager, grpc_service_stub: CVSAManagerCrossClusterServiceStub):
    logging.info("Step 1. Start instance backup as prerequisite")
    create_new_cvsa_instance_and_validate(kafka_mgr, aws, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    logging.info("Step 2. Trigger debug mode start")
    trigger_debug_mode(kafka=kafka_mgr, stub_service=grpc_service_stub, mode=RopActions.ACTION_START)

    logging.info("Step 3. Wait for event maintenance debug event started,")
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.START,
        operation_type=MaintenanceOperation.DEBUG,
    )

    logging.info("Step 3.1 Verify if List endpoint returns valid information about the cVSA instance.")
    list_cvsa_response = grpc_list_cvsas(grpc_service_stub=grpc_service_stub, cvsa_id=kafka_mgr.cvsa_id)
    assert len(list_cvsa_response.cvsas) == 1, "Expected to get one cvsa instance while filtering by particular cvsa id"
    maintenance_state = list_cvsa_response.cvsas[0].maintenance
    cvsa_state = list_cvsa_response.cvsas[0].state
    assert len(list_cvsa_response.cvsas) == 1, "Expected to get one cvsa instance while filtering by particular cvsa id"
    assert maintenance_state == MaintenanceMode.DEBUG, f"Debug mode is not ON, instead got {maintenance_state}"
    assert cvsa_state == InstanceState.RUNNING, f"CVSA state is not running, instead got {cvsa_state}"

    logging.info("Step 4. wait for cVSA to respond with idaStatus: true")
    storeonce = get_cvsa_storeonce(aws, kafka_mgr)
    wait_for_ida_status_true(storeonce=storeonce)

    logging.info("Step 5. Set 'idaStatus: false' from tests,")
    storeonce.set_ida_status(status=False)

    logging.info("Step 6. Wait for cVSA to respond with idaStatus: true")
    # cVSA Manager should fix intermittent changes in the idaStatus when debug mode is enabled.
    wait_for_ida_status_true(storeonce=storeonce)

    logging.info("Step 7. Trigger debug mode stop")
    trigger_debug_mode(kafka=kafka_mgr, stub_service=grpc_service_stub, mode=RopActions.ACTION_STOP)

    logging.info("Step 8. Wait for event maintenance debug event stopped")
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.STOP,
        operation_type=MaintenanceOperation.DEBUG,
    )

    logging.info("Step 8.1 Verify if List endpoint returns valid information about the cVSA instance.")
    list_cvsa_response = grpc_list_cvsas(grpc_service_stub=grpc_service_stub, cvsa_id=kafka_mgr.cvsa_id)
    assert len(list_cvsa_response.cvsas) == 1, "Expected to get one cvsa instance while filtering by particular cvsa id"
    maintenance_state = list_cvsa_response.cvsas[0].maintenance
    assert maintenance_state == MaintenanceMode.OFF, f"Debug mode is not OFF, instead got {maintenance_state}"
    verify_stopped_event(kafka_mgr, reason=StopReason.IDLE)


def wait_for_ida_status_true(storeonce) -> None:
    attempt = 0
    while True:
        ida_status = storeonce.get_ida_status()
        if ida_status is True:
            break
        else:
            attempt += 1
            sleep(10)
        assert attempt < 90, f"cVSA didn't respond with idaStatus: true after 15 minutes"


def set_ida_status(storeonce, status=False) -> None:
    attempt = 0
    while True:
        storeonce.set_ida_status(status=status)
        if storeonce.get_ida_status() == status:
            break
        else:
            attempt += 1
            sleep(10)
        assert attempt < 90, f"cVSA didn't respond with idaStatus: {status} after 15 minutes"


def trigger_debug_mode(kafka, stub_service, mode=RopActions.ACTION_STOP) -> None:
    attempt = 0
    while True:
        response = grpc_trigger_cvsa_maintenance_operation(
            grpc_service_stub=stub_service, cvsa_id=kafka.cvsa_id, action=mode
        )
        if response.result == ResponseResult.ACCEPTED:
            break
        else:
            attempt += 1
            sleep(10)
        assert attempt < 90, f"cVSA didn't respond with result == ACCEPTED after 15 minutes, for {mode}"
