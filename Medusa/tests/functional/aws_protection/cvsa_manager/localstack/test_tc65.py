"""
TC65: Requests sent after account unregistration should be rejected
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_ready_event,
    verify_finished_event,
    verify_created_event_backup,
)
from tests.steps.aws_protection.cvsa.cam_updates_kafka_steps import send_unregister_event, verify_unregister_event


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc65(kafka_mgr: KafkaManager, cam_updates_kafka: KafkaManager, aws: AWS):
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_created_event_backup(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr)

    send_unregister_event(kafka_mgr, cam_updates_kafka)
    verify_unregister_event(kafka_mgr, cam_updates_kafka)

    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="requester: account unregistered",
    )
