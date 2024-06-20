"""
TC47: Requests are invalidated due to timeouts
    1. Send backup and FLR requests (some of them with forcing NOT_IDLE state)
    2. Expect requests invalidation with different error types (soft, hard, FLR timeouts)
"""

from pytest import fixture, mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    send_finished_event,
    create_new_cvsa_instance_and_validate,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events
from tests.steps.aws_protection.cvsa.restore_granular_file_kafka_steps import (
    send_restore_granular_file_requested_event,
    verify_restore_granular_file_requested_event,
)


@fixture(scope="function")
def kafka_mgr(aws):
    kafka_mgr_1 = new_kafka_lifecycle_events(tc_id=47)
    kafka_mgr_2 = new_kafka_lifecycle_events(tc_id=47)
    kafka_mgr_3 = new_kafka_lifecycle_events(tc_id=47)
    yield kafka_mgr_1, kafka_mgr_2, kafka_mgr_3

    cleanup_cvsa_instance(kafka_mgr_1, aws)
    cleanup_cvsa_instance(kafka_mgr_2, aws)
    cleanup_cvsa_instance(kafka_mgr_3, aws)


@mark.cvsa_localstack_custom_timeout
def test_tc47(kafka_mgr: KafkaManager, aws):
    kafka_mgr_1, kafka_mgr_2, kafka_mgr_3 = kafka_mgr

    send_requests(kafka_mgr_1, kafka_mgr_2, kafka_mgr_3, aws)
    verify_finished_events(kafka_mgr_1, kafka_mgr_2, kafka_mgr_3)


def send_requests(kafka_mgr_1, kafka_mgr_2, kafka_mgr_3, aws):
    # Send backup request and expect invalidation due to soft timeout
    # (specified time elapsed and created instance is idle)
    send_backup_requested_event(kafka_mgr_1, data_protected_gb=2001)
    verify_backup_requested_event(kafka_mgr_1, data_protected_gb=2001)

    # Send second backup request and expect invalidation due to hard timeout
    # (using forced behavior we force NOT_IDLE state of the instance, so the
    # soft timeout cannot be used)
    send_backup_requested_event(
        kafka_mgr_2,
        data_protected_gb=2001,
        headers={
            "ce_forcednotidle": bytes("true", "utf-8"),
        },
    )
    verify_backup_requested_event(kafka_mgr_2, data_protected_gb=2001)

    # Perform one successful backup request to send FLR request then
    # and not fail on the request validation step
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr_3, data_protected_gb=1)
    send_finished_event(kafka_mgr_3)
    verify_finished_event(kafka_mgr_3)

    # Send FLR (File Level Recovery) request and expect invalidation due to FLR-specific hard timeout
    # (we force NOT_IDLE state to avoid invalidation due to soft timeout)
    send_restore_granular_file_requested_event(
        kafka_mgr_3,
        data_protected_volume_gb=1,
        data_protected_volume_count=1,
        headers={
            "ce_forcednotidle": bytes("true", "utf-8"),
        },
    )
    verify_restore_granular_file_requested_event(kafka_mgr_3, data_protected_volume_gb=1, data_protected_volume_count=1)


def verify_finished_events(kafka_mgr_1, kafka_mgr_2, kafka_mgr_3):
    verify_finished_event(
        kafka_mgr_1,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="request invalidated due to soft timeout",
        timeout=7200,
    )
    verify_finished_event(
        kafka_mgr_2,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="request invalidated due to hard timeout",
        timeout=7200,
    )
    verify_finished_event(
        kafka_mgr_3,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="request invalidated due to FLR timeout",
        timeout=7200,
    )
