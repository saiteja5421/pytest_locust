"""
TC22: Validate error when cVSA image is not available
    1. Send CVSABackupBatchRequestedEvent with non-existent AMI ID requested (using forcedbehaviors)
    2. Check error message
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_dataclasses import CloudImage
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_not_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc22(kafka_mgr: KafkaManager, aws):
    send_backup_requested_event(kafka_mgr, data_protected_gb=2001, ami="abracadabra")
    verify_backup_requested_event(kafka_mgr, data_protected_gb=2001)
    expected_error = "failed to get image"
    verify_finished_event(kafka_mgr, result=RequestFinishedStatus.STATUS_ERROR, error_msg=expected_error, timeout=120)
    verify_not_deployed_cvsa(cloud_vm_mgr=aws, account_id=kafka_mgr.account_id)
