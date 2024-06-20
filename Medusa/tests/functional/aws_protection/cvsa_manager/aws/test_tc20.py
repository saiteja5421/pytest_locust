"""
TC20: Validate retry policy of the workflow and activities by stopping EC2
"""

from pytest import mark

from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import (
    wait_for_instance_to_be_deployed,
    turn_off_cvsa_instance,
    turn_on_cvsa_instance,
    verify_deployed_cvsa,
    verify_not_deployed_cvsa,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    send_finished_event,
    verify_finished_event,
    verify_instance_type_and_volume_size,
    verify_ready_event,
    verify_created_event_backup,
)
from tests.steps.aws_protection.cvsa.storeonce_steps import verify_storeonce_system
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials


@mark.order(2000)
@mark.cvsa_aws
@mark.cvsa_cloud
def test_tc20(kafka_mgr: KafkaManager, aws: CloudVmManager):
    verify_not_deployed_cvsa(cloud_vm_mgr=aws, account_id=kafka_mgr.account_id)
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    wait_for_instance_to_be_deployed(aws, kafka_mgr.cam_account_id)
    turn_off_cvsa_instance(aws, kafka_mgr.account_id)
    turn_on_cvsa_instance(aws, kafka_mgr.account_id)
    verify_created_event_backup(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr)
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)
    verify_instance_type_and_volume_size(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_storeonce_system(kafka_mgr, aws)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
