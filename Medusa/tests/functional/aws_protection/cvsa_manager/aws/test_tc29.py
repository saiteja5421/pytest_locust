"""
TC29: Update cVSA instance version
    Prerequisites: At least three AMI images are available with different versions
    Verify cvsa instance
    Send some data to catalyst
    Send finished event
    Verify ec2 is in stopped state with reason maintanance
    Send finished event to update instance
    Verify instance stopped and terminated
    Verify new instance is created.
    Verify serial number is the same and the configuration is correct
    Verify that sent data is still available
    Verify that last version is taken to updated
    Verify update is successfully completed
"""

from pytest import mark

from lib.common.enums.cvsa import StopReason, MaintenanceAction, MaintenanceOperation
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import (
    get_amis_for_update,
    get_cvsa_version,
    _parse_ami_version,
    verify_deployed_cvsa,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
    verify_started_event,
    verify_ready_event,
    verify_created_event_backup,
)
from tests.steps.aws_protection.cvsa.kafka_steps import verify_maintenance_event
from tests.steps.aws_protection.cvsa.storeonce_steps import verify_cloud_stores, validate_cloud_store_data
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials
from tests.steps.aws_protection.cvsa.write_read_backup_steps import write_data_to_cvsa_cloud_store


@mark.order(2900)
@mark.cvsa_aws
@mark.cvsa_cloud
def test_tc29(kafka_mgr: KafkaManager, aws: CloudVmManager):
    amis = get_amis_for_update(cloud_vm_mgr=aws)
    older_ami = amis[0]
    newest_ami = amis[1]
    cvsa_event = create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1, ami=older_ami
    )
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    verify_stopped_event(kafka_mgr, reason=StopReason.IDLE)
    verify_maintenance_event(
        kafka_mgr,
        action=MaintenanceAction.START,
        operation_type=MaintenanceOperation.UPGRADE,
    )
    verify_started_event(kafka=kafka_mgr, timeout=Timeout.STARTED_EVENT_DURING_MAINTENANCE.value)
    verify_maintenance_event(
        kafka_mgr,
        action=MaintenanceAction.STOP,
        operation_type=MaintenanceOperation.UPGRADE,
    )
    cvsa_version = get_cvsa_version(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    assert cvsa_version == _parse_ami_version(newest_ami.name)
    verify_cloud_stores(kafka_mgr, aws, cvsa_event.catalyst_store)

    # check backup after upgrade
    send_backup_requested_event(kafka_mgr, data_protected_gb=1, cloud_provider=aws.name())
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1, cloud_provider=aws.name())
    verify_started_event(kafka_mgr)
    cvsa_model_upgrade = verify_ready_event(kafka_mgr, cloud_provider=aws.name())
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id, disaster_recovery=True)
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)
    write_data_to_cvsa_cloud_store(aws, kafka_mgr, cvsa_model_upgrade.catalyst_store)
    validate_cloud_store_data(aws, kafka_mgr)
