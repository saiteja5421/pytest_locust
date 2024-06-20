"""
TC-53: Send restore when main cVSA instance is stopped
    Verify that read only replica does not affect main CVSA instance
"""

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_models import CvsaEvent
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_state
from tests.steps.aws_protection.cvsa.cvsa_manager_restore_steps import (
    create_main_cvsa_instance,
    create_read_only_replica,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_instance_type_and_volume_size,
)
from tests.steps.aws_protection.cvsa.restore_aws_steps import verify_restore_cvsa
from tests.steps.aws_protection.cvsa.vault_steps import get_credentials_for_copy


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc53(kafka_mgr: KafkaManager, aws_eu_west: CloudVmManager):
    main_cvsa = create_main_cvsa_instance(kafka_mgr, aws_eu_west)
    read_only_replica = create_read_only_replica(kafka_mgr)

    verify_instances(kafka_mgr, aws_eu_west, backup_instance_model=main_cvsa, restore_instance_model=read_only_replica)
    verify_main_cvsa_state(aws_eu_west, main_cvsa.cvsa_id)


def verify_instances(
    kafka_mgr: KafkaManager, aws: CloudVmManager, backup_instance_model: CvsaEvent, restore_instance_model: CvsaEvent
):
    assert backup_instance_model.cvsa_id != restore_instance_model.cvsa_id
    assert backup_instance_model.catalyst_store == restore_instance_model.catalyst_store

    backup_instance_credentials = get_credentials_for_copy(backup_instance_model.cvsa_id)
    restore_instance_credentials = get_credentials_for_copy(restore_instance_model.cvsa_id)
    assert backup_instance_credentials == restore_instance_credentials

    verify_restore_cvsa(aws, kafka_mgr, restore_instance_model.cvsa_id)


def verify_main_cvsa_state(aws: CloudVmManager, cvsa_id: str):
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws,
        instance_details=CloudInstanceDetails.R6I_LARGE,
        cvsa_id=cvsa_id,
    )
    verify_instance_state(aws, cvsa_id, CloudInstanceState.STOPPED)
