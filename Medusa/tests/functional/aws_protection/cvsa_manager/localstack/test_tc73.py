"""
TC73: Granular File Restore {small, large}
    1. Perform backup to prepare env for the granular file restore (backup is a prerequisite),
    2. Send RestoreGranularFileEvent,
    3. Assert if new Read Only instance was created
    4. Send RequestFinished for granular file restore request,
    5. Validate that related read only instance was terminated,
    - it may be subject for change in the future
"""
import logging

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import TerminateReason, CvsaType
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.assertions import assert_object_store_count
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_terminated, verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    verify_created_event,
    verify_ready_event,
    verify_terminated_event,
    create_new_cvsa_instance_and_validate,
)
from tests.steps.aws_protection.cvsa.grpc_steps import is_cosm_enabled
from tests.steps.aws_protection.cvsa.restore_granular_file_kafka_steps import (
    send_restore_granular_file_requested_event,
    verify_restore_granular_file_requested_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
@mark.parametrize(
    "volumes_to_restore, expected_instance_type",
    [
        (1, CloudInstanceDetails.M6I_XLARGE),
        (2, CloudInstanceDetails.C6I_2XLARGE),
        (32, CloudInstanceDetails.C6I_32XLARGE),
    ],
)
def test_tc73(
    kafka_mgr: KafkaManager, aws: CloudVmManager, volumes_to_restore, expected_instance_type: CloudInstanceDetails
):
    logging.info("Step 1. Perform backup as prerequisite")
    create_new_cvsa_instance_and_validate(kafka_mgr, aws, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    logging.info("Step 2. Send RestoreGranularFileEvent")
    send_restore_granular_file_requested_event(
        kafka_mgr, data_protected_volume_gb=1, data_protected_volume_count=volumes_to_restore
    )
    verify_restore_granular_file_requested_event(
        kafka_mgr, data_protected_volume_gb=1, data_protected_volume_count=volumes_to_restore
    )
    verify_created_event(
        kafka_mgr,
        instance_details=expected_instance_type,
        backup_streams=None,
        restore_streams=volumes_to_restore,
    )
    verify_ready_event(
        kafka_mgr,
        instance_details=expected_instance_type,
        backup_streams=None,
        restore_streams=volumes_to_restore,
    )
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id, cvsa_type=CvsaType.RESTORE_FLR)

    logging.info("Step 3. Assert if new Read Only instance was created")
    tag_read_only = Tag(Key="cvsa-is-read-only", Value="true")
    tag_customer = Tag(Key="cvsa-application-customer-id", Value=kafka_mgr.account_id)
    read_only_replicas = aws.list_instances(
        tags=[tag_customer, tag_read_only], states=[CloudInstanceState.RUNNING, CloudInstanceState.PENDING]
    )
    logging.info(f"read_only_replicas={read_only_replicas}")
    assert len(read_only_replicas) == 1, f"One read only instance is expected, got {len(read_only_replicas)}"
    assert read_only_replicas[0].instance_type == expected_instance_type.value.instance_type
    if is_cosm_enabled():
        assert_object_store_count(cvsa_id=read_only_replicas[0].id, count=0)

    logging.info("Step 4. Send request finished for granular file restore request")
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    logging.info("Step 5. Validate that related read only instance was terminated")
    verify_terminated_event(
        kafka_mgr, reason=TerminateReason.READ_ONLY_REQUEST_FINISHED, cloud_instance_id=read_only_replicas[0].id
    )
    verify_instance_terminated(aws, read_only_replicas[0].id)
