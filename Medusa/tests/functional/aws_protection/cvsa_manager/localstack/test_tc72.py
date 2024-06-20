"""
TC72: Send and verify old BackupSingleAsset event type
    Scenario based on TC64
"""

from pytest import mark

from lib.common.enums.cvsa import RequestType
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_created_event,
    verify_started_event,
    verify_ready_event,
    send_finished_event,
    verify_finished_event,
    send_requested_event,
    verify_requested_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc72(aws: CloudVmManager, kafka_mgr: KafkaManager):
    send_requested_event(kafka_mgr, data_protected_gb=0, request_type=RequestType.BACKUP_SINGLE_ASSET)
    verify_requested_event(kafka_mgr, data_protected_gb=0, request_type=RequestType.BACKUP_SINGLE_ASSET)
    verify_created_event(kafka_mgr, backup_streams=None, restore_streams=None)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr, backup_streams=None)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
