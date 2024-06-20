"""
TC23: cVSA is unhealthy so CVSAReadyEvent is not sent
    Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    Break configuration in storeonce for one of the components.
    Check storage overview, catalyst stores, appliance summary, local storage overview state emitted by health monitor.
    Check error message
"""

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    verify_started_event,
    verify_created_event_backup,
)
from tests.steps.aws_protection.cvsa.kafka_steps import wait_for_event_not_emitted


@mark.order(2300)
@mark.cvsa_localstack_custom_timeout
def test_tc23(aws: CloudVmManager, kafka_mgr: KafkaManager):
    send_backup_requested_event(
        kafka_mgr,
        data_protected_gb=2001,
        headers={
            "ce_forcedunhealthystore": bytes("true", "utf-8"),
        },
    )
    verify_backup_requested_event(kafka_mgr, data_protected_gb=2001)
    verify_created_event_backup(kafka_mgr, data_protected_gb=2001, instance_details=CloudInstanceDetails.M6I_XLARGE)
    verify_started_event(kafka_mgr)
    wait_for_event_not_emitted(kafka_mgr, "cvsa.v1.CVSAReadyEvent", timeout=60)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="request invalidated due to soft timeout",
        timeout=7200,
    )
