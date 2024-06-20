"""
TC60: Verify that instance which changes its health status to unhealthy is stopped
"""

from pytest import mark

from lib.common.enums.cvsa import StopReason, RequestFinishedStatus
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
    verify_started_event,
)


@mark.cvsa_localstack_custom_timeout
def test_tc60(kafka_mgr, aws_eu_west):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws_eu_west, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    send_backup_requested_event(
        kafka_mgr,
        data_protected_gb=1,
        headers={
            "ce_forcedunhealthystore": bytes("true", "utf-8"),
        },
    )
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        timeout=7200,
        error_msg="request invalidated due to soft timeout",
    )
    verify_stopped_event(kafka_mgr, reason=StopReason.UNHEALTHY)
