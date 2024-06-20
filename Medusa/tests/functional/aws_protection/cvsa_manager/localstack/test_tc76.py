"""
TC76: Inflight requests should be invalidated during account unregistration
    1. Create a new instance, by sending backup request
    2. Send UnregisterEvent
    2. Expect RequestFinishedEvent which invalidates the pending request because of
       the unregistration
"""
from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cam_updates_kafka_steps import send_unregister_event, verify_unregister_event
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc76(kafka_mgr: KafkaManager, cam_updates_kafka: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)

    send_unregister_event(kafka_mgr, cam_updates_kafka)
    verify_unregister_event(kafka_mgr, cam_updates_kafka)

    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="request invalidated due customer unregistration",
    )
