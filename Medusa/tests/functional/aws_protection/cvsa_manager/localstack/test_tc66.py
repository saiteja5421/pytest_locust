"""
TC66: Terminate orphaned instance while other instance with the same cvsaID exists
    - check if desired state orphans termination does not affect valid instances
"""

from pytest import mark

from lib.common.enums.cvsa import StopReason, TerminateReason
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import (
    verify_instance_terminated,
    create_orphaned_instance,
    verify_instance_running,
    verify_instance_state,
)
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
    verify_terminated_event,
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc66(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    cloud_instance_id = aws.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])[0].id
    orphaned_instance = create_orphaned_instance(kafka_mgr, cloud_vm_mgr=aws)

    verify_instance_running(aws, orphaned_instance.id)
    verify_stopped_event(kafka_mgr, reason=StopReason.ORPHANED)
    verify_terminated_event(kafka_mgr, reason=TerminateReason.ORPHANED, cloud_instance_id=orphaned_instance.id)
    verify_instance_terminated(aws, orphaned_instance.id)

    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr)
    verify_instance_state(aws, kafka_mgr.cvsa_id, CloudInstanceState.RUNNING)
