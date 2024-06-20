"""
TC71: Validate old Delete event type Request when customer already performed at least one backup request
    Scenario based on TC49.
"""

from pytest import mark

from lib.common.enums.cvsa import RequestType
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_requested_event,
    verify_requested_event,
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc71(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    send_requested_event(kafka_mgr, data_protected_gb=0, request_type=RequestType.DELETE)
    verify_requested_event(kafka_mgr, data_protected_gb=0, request_type=RequestType.DELETE)

    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr, backup_streams=None)
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)

    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
