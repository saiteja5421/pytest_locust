"""
TC69: Perform Disaster Recovery if Upgrade failed and instance is still in the maintenance state
"""

import logging

from pytest import mark

from lib.common.enums.cvsa import MaintenanceAction, MaintenanceOperation
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import (
    get_amis_for_update,
    get_data_volume,
    verify_volume_deleted,
)
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
    verify_started_event,
    verify_ready_event,
)
from tests.steps.aws_protection.cvsa.kafka_steps import verify_maintenance_event

logger = logging.getLogger()


@mark.cvsa_localstack
def test_tc69(kafka_mgr: KafkaManager, aws: CloudVmManager):
    older_ami, newest_ami = get_amis_for_update(cloud_vm_mgr=aws)
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws,
        kafka_mgr=kafka_mgr,
        data_protected_gb=1,
        ami=older_ami,
        headers={"ce_forcedfailedupgrade": bytes("true", "utf-8")},
    )
    data_volume = get_data_volume(aws, kafka_mgr.cvsa_id)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    verify_failed_upgrade(kafka_mgr)
    verify_successfull_disaster_recovery(kafka_mgr)

    verify_volume_deleted(aws, data_volume.name)

    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr)


def verify_failed_upgrade(kafka_mgr: KafkaManager):
    number_of_workflow_retries = 3
    for i in range(number_of_workflow_retries):
        logger.info(f"Verifying failed upgrade (retry #{i + 1}) customer id: {kafka_mgr.account_id}")
        verify_maintenance_event(
            kafka_mgr,
            action=MaintenanceAction.START,
            operation_type=MaintenanceOperation.UPGRADE,
        )
        verify_maintenance_event(
            kafka_mgr,
            action=MaintenanceAction.ERROR,
            operation_type=MaintenanceOperation.UPGRADE,
        )


def verify_successfull_disaster_recovery(kafka_mgr: KafkaManager):
    verify_maintenance_event(
        kafka_mgr,
        action=MaintenanceAction.START,
        operation_type=MaintenanceOperation.DISASTER_RECOVERY,
    )
    verify_maintenance_event(
        kafka_mgr,
        action=MaintenanceAction.STOP,
        operation_type=MaintenanceOperation.DISASTER_RECOVERY,
    )
