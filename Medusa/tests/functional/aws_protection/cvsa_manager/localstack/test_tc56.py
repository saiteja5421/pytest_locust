"""
TC-56: Send restore request. Verify that read only replica is deleted after request invalidation
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_state
from tests.steps.aws_protection.cvsa.cvsa_manager_restore_steps import (
    create_main_cvsa_instance,
    create_read_only_replica,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import verify_finished_event
from tests.steps.aws_protection.cvsa.kafka_steps import verify_no_maintenance_event


@mark.cvsa_localstack_custom_timeout
def test_tc56(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_main_cvsa_instance(kafka_mgr, aws)
    read_only_replica = create_read_only_replica(kafka_mgr)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="request invalidated due to soft timeout",
        timeout=7200,
    )
    verify_no_maintenance_event(kafka_mgr, timeout=180)
    verify_instance_state(aws, read_only_replica.cvsa_id, CloudInstanceState.TERMINATED)
