"""
TC-14: Deploy cVSA instance with large protected data
    1. Verify that customer has not yet deployed cVSA or remove it.
    2. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    3. Check cVSACreatedEvent (at this point catalyst is configured, cloudbank is created ).
    4. Check cVSAStartedEvent (at this point cVSA is in running a state within AWS and monitoring is triggered)
    5. Check cVSAReadyEvent (At this point cVSA is ready)
    6. Validate Cloud compute resource created. Should be largest possible in region.
    7. Verify that S3 and EBS exists
    8. Verify that cloud bank exists on storeonce.
"""

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_deployed_cvsa, verify_not_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_ready_event,
    send_finished_event,
    verify_finished_event,
    verify_instance_type_and_volume_size,
    verify_created_event_backup,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc14(kafka_mgr: KafkaManager, aws: CloudVmManager):
    verify_not_deployed_cvsa(cloud_vm_mgr=aws, account_id=kafka_mgr.account_id)
    send_backup_requested_event(kafka_mgr, data_protected_gb=60_000)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=60_000)
    verify_created_event_backup(
        kafka_mgr,
        data_protected_gb=60_000,
        instance_details=CloudInstanceDetails.C6I_24XLARGE,
        backup_streams=19,
        volume_size_bytes=670_000_000_000,
    )
    verify_started_event(kafka_mgr)
    verify_ready_event(
        kafka_mgr,
        instance_details=CloudInstanceDetails.C6I_24XLARGE,
        backup_streams=19,
        volume_size_bytes=670_000_000_000,
    )
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=CloudInstanceDetails.C6I_24XLARGE,
        volume_size_bytes=670_000_000_000,
    )
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
