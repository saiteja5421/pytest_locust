"""
TC83: Re-registration:
     1. Start backup instance,
     2. Send UnregisterEvent
     3. Verify instance terminated
     4. Send register event
     5. Start backup instance again
     6. Verify ready event
"""

from pytest import mark

from lib.common.enums.cvsa import StopReason, TerminateReason
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cam_updates_kafka_steps import (
    send_unregister_event,
    verify_unregister_event,
    send_register_event,
    verify_register_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_terminated
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    verify_stopped_event,
    verify_terminated_event,
    verify_ready_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc83(kafka_mgr: KafkaManager, cam_updates_kafka: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)

    cloud_instance_id = aws.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])[0].id

    send_unregister_event(kafka_mgr, cam_updates_kafka)
    verify_unregister_event(kafka_mgr, cam_updates_kafka)
    verify_stopped_event(kafka_mgr, reason=StopReason.CUSTOMER_UNREGISTER)
    verify_terminated_event(kafka_mgr, reason=TerminateReason.CUSTOMER_UNREGISTER)
    verify_instance_terminated(aws, cloud_instance_id)

    send_register_event(kafka_mgr, cam_updates_kafka)
    verify_register_event(kafka_mgr, cam_updates_kafka)

    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_ready_event(kafka_mgr)
