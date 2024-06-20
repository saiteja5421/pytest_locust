"""
TC64: Send and verify BackupSingleAsset and Housekeeping events
"""

from pytest import mark

from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_single_asset_request_steps import (
    send_backup_single_asset_requested_event,
    verify_backup_single_asset_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_created_event,
    verify_started_event,
    verify_ready_event,
    send_finished_event,
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.housekeeping_request_steps import (
    send_housekeeping_requested_event,
    verify_housekeeping_requested_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc64(aws: CloudVmManager, kafka_mgr: KafkaManager):
    send_backup_single_asset_requested_event(kafka_mgr)
    verify_backup_single_asset_requested_event(kafka_mgr)
    verify_created_event(kafka_mgr, backup_streams=None, restore_streams=None)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr, backup_streams=None)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    send_housekeeping_requested_event(kafka_mgr, data_protected_gb=1)
    verify_housekeeping_requested_event(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr, backup_streams=None)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
