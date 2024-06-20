"""
TC16: cVSA instance goes idle after backup/restore request
    1. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    2. Check cVSAStartedEvent (at this point cVSA is in running state within AWS and monitoring is triggered)
    3. Check cVSAReadyEvent (At this point cVSA is ready)
    4. Check CVSARequestFinishedEvent (backup is done)
    5. Wait until cVSA EC2 instance is stopped
TC26: Generate support bundle on instance shutdown
    Verify that cVSA is running
    Send FinishedEvent
    Verify StoppedEvent
    Verify that cVSA instance is stopped
    Turn on cVSA instance
    Verify that Support Bundle is created and exists
    Send RequestedEvent
    Verify ReadyEvent
    Send FinishedEvent
    Verify StoppedEvent
    Verify that cVSA instance is stopped
    Turn on cVSA instance
    Verify that second Support Bundle is created and exists
"""

from pytest import mark

from lib.common.enums.cvsa import StopReason
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_state, turn_on_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
)
from tests.steps.aws_protection.cvsa.storeonce_steps import verify_storeonce_system, verify_support_bundle


@mark.order(1600)
@mark.cvsa_aws
@mark.cvsa_cloud
def test_tc16_tc26(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    verify_storeonce_system(kafka_mgr, aws)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    verify_stopped_event(kafka_mgr, reason=StopReason.IDLE)
    verify_instance_state(aws, kafka_mgr.cvsa_id, CloudInstanceState.STOPPED, timeout_seconds=1500)
    turn_on_cvsa_instance(aws, kafka_mgr.account_id)
    verify_support_bundle(kafka_mgr, aws, bundle_count=1)
