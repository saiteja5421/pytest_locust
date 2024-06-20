"""
TC-03: Backup/restore request when cVSA instance is properly sized and not running.
    1. Stop the instance by AWS API
    2. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - Kafka client)
    3. Check cVSAStartedEvent (at this point cVSA is in running state within AWS and monitoring is triggered)
    4. cVSAReadyEvent (At this point cVSA is ready to serve the request)
    5. Validate Cloud compute resource created.
    6. Verify that cVSA is running and ready
"""

from pytest import mark

from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import turn_off_cvsa_instance, verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc03(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    turn_off_cvsa_instance(cloud_vm_mgr=aws, customer_id=kafka_mgr.account_id)
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr)
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
