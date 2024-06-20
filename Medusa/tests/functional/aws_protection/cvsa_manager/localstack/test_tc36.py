"""
TC36: Edge cases for processing first Backup/Restore/Housekeeping events.
    Restore request before first backup is invalid.
    Backup requests with data protected previous bytes > 0, without prior successful backup request, is valid.
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_not_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_backup_requested_event,
    verify_created_event_backup,
    verify_finished_event,
    verify_ready_event,
    send_finished_event,
)
from tests.steps.aws_protection.cvsa.restore_request_steps import send_restore_requested_event
from tests.steps.aws_protection.cvsa.housekeeping_request_steps import send_housekeeping_requested_event


@mark.order(3600)
@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc36(kafka_mgr, aws: CloudVmManager):
    # Restore without existing Cloud Store is invalid (TC-36).
    send_restore_requested_event(kafka_mgr, data_protected_gb=0)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="restore request cannot be performed without existing configured cVSA",
    )
    # Ensure no cVSA instance was created (as request were invalid).
    verify_not_deployed_cvsa(aws, account_id=kafka_mgr.account_id)

    # First backup request with data protected old bytes > 0 is valid.
    send_backup_requested_event(kafka_mgr, data_protected_gb=1, data_protected_previous_gb=1)
    verify_created_event_backup(kafka_mgr, data_protected_gb=1)
    verify_ready_event(kafka_mgr)
    send_finished_event(kafka_mgr)
