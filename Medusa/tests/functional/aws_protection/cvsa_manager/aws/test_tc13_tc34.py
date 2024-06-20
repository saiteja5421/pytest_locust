"""
TC13: Backup/restore request in the same time - same customer, same region
    Request 1:
    Verify that customer has cVSA instance.
    Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    Check cVSACreatedEvent (at this point catalyst is configured, cloudbank is created ).
    Check cVSAStartedEvent (at this point cVSA is in running state within AWS and monitoring is triggered)
    Check cVSAReadyEvent (At this point cVSA is ready)
    Validate Cloud compute resource created.
    Verify that S3 and EBS exists
    Verify that cloud bank exists on storeonce.
    Request 2:
    Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    Check cVSAStartedEvent (at this point cVSA is in running state within AWS and monitoring is triggered)
    Check cVSAReadyEvent (At this point cVSA is ready)
    Validate Cloud compute resource created.
    Verify that the same S3 and EBS exists
    Verify that cloud bank exists on storeonce.
TC34: Send cVSARequestedEvent request for backup (with required resize) first and cVSARequestedEvent restore second.
    Start restore backup request
    Start backup request with resizing required
    Verify that restore is not interrupted and backup will start after restore
"""
import logging

from pytest import fixture, mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_trace_id
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    verify_no_event,
    verify_resize_event,
    verify_started_event,
    verify_ready_event,
    send_finished_event,
    verify_finished_event,
    verify_created_event,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events
from tests.steps.aws_protection.cvsa.restore_request_steps import (
    send_restore_requested_event,
    verify_restore_requested_event,
)


@fixture(scope="function")
def kafka_mgr(aws: CloudVmManager):
    kafka_mgr_1 = new_kafka_lifecycle_events(tc_id=34)
    kafka_mgr_2 = new_kafka_lifecycle_events(tc_id=34)
    kafka_mgr_2.account_id = kafka_mgr_1.account_id
    kafka_mgr_2.cam_account_id = kafka_mgr_1.cam_account_id
    kafka_mgr_2.csp_account_id = kafka_mgr_1.csp_account_id
    yield kafka_mgr_1, kafka_mgr_2
    logger = logging.getLogger()
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    cleanup_cvsa_instance(kafka_mgr_1, aws)
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")


@mark.order(3400)
@mark.cvsa_aws
@mark.cvsa_cloud
def test_tc13_tc34(kafka_mgr, aws: CloudVmManager):
    # Kafka 1 - restore, Kafka 2 - backup with resize <- different correlation id
    kafka_mgr_1, kafka_mgr_2 = kafka_mgr
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr_1, data_protected_gb=1)
    send_finished_event(kafka_mgr_1)
    verify_finished_event(kafka_mgr_1)
    kafka_mgr_2.cvsa_id = kafka_mgr_1.cvsa_id

    # Backup request
    send_backup_requested_event(kafka_mgr_2, data_protected_gb=4000)
    verify_backup_requested_event(kafka_mgr_2, data_protected_gb=4000)

    # Restore request
    send_restore_requested_event(kafka_mgr_1, data_protected_gb=0)
    verify_restore_requested_event(kafka_mgr_1, data_protected_gb=None)

    # Verify backup request process
    verify_started_event(kafka_mgr_2, event_filters=[event_filter_trace_id(kafka_mgr_2.trace_id)])
    verify_resize_event(
        kafka_mgr_2,
        data_protected_gb=4000,
        volume_size_bytes=54_225_644_953,
        instance_details=CloudInstanceDetails.C6I_2XLARGE,
    )
    verify_ready_event(kafka=kafka_mgr_2, volume_size_bytes=54_225_644_953)

    # Verify restore request process
    verify_created_event(kafka_mgr_1, backup_streams=None, restore_streams=8)
    verify_started_event(kafka_mgr_1, event_filters=[event_filter_trace_id(kafka_mgr_1.trace_id)])
    verify_ready_event(kafka=kafka_mgr_1, volume_size_bytes=None, backup_streams=None, restore_streams=8)

    # Verify no event stopped on restore
    verify_no_event(kafka_mgr_1, event_type="cvsa.v1.CVSAStoppedEvent")

    # Verify no event stopped on backup
    verify_no_event(kafka_mgr_2, event_type="cvsa.v1.CVSAStoppedEvent")
