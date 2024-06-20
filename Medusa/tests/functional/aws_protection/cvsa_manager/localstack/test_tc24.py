"""
TC24: Send Requested Event (simulated backup/restore request). Without customer id.
    1. Send cVSARequestedEvent with wrong customer id (from Backup Service, or e2e Test suite QA - Kafka client)
    2. Check the error message
    3. Check EBS, EC2, S3 instances
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import send_backup_requested_event
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    verify_no_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc24(aws: CloudVmManager, kafka_mgr: KafkaManager):
    csp_id = kafka_mgr.csp_account_id
    kafka_mgr.csp_account_id = bytes(str(" "), "utf-8")
    send_backup_requested_event(kafka_mgr, data_protected_gb=2001)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="cloud service provider id (cspAccountId) must not be empty",
    )
    kafka_mgr.csp_account_id = csp_id
    kafka_mgr.cam_account_id = bytes(str(" "), "utf-8")
    send_backup_requested_event(kafka_mgr, data_protected_gb=2001)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="cloud account id (camAccountId) must be valid uuid: invalid UUID length: 1",
    )
    verify_no_event(kafka_mgr, event_type="cvsa.v1.CVSAStartedEvent")
