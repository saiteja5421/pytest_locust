"""
TC63: Backup and restore requests using new RequestedEvents
"""

from pytest import mark

from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_ready_event,
    send_finished_event,
    verify_finished_event,
    verify_created_event_backup,
    verify_created_event,
)
from tests.steps.aws_protection.cvsa.restore_request_steps import (
    send_restore_requested_event,
    verify_restore_requested_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc63(aws: CloudVmManager, kafka_mgr: KafkaManager):
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_created_event_backup(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr)

    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    send_restore_requested_event(kafka_mgr, data_protected_gb=1)
    verify_restore_requested_event(kafka_mgr, data_protected_gb=1)
    verify_created_event(
        kafka_mgr,
        backup_streams=None,
        restore_streams=8,
    )
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr, backup_streams=None, restore_streams=8)
