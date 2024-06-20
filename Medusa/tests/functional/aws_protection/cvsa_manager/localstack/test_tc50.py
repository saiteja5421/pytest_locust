"""
TC-50: Delete Request when customer have bigger instance for backup earlier
    Create cVSA instance for customer with bigger instance type than default.
    Send FinishedEvent.
    Send Delete Request.
    Verify Started Event.
    Verify Ready Event.
    Verify cVSA instance that instance type size does not changed.
"""

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_instance_type_and_volume_size,
)
from tests.steps.aws_protection.cvsa.housekeeping_request_steps import (
    send_housekeeping_requested_event,
    verify_housekeeping_requested_event,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc50(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws,
        kafka_mgr=kafka_mgr,
        data_protected_gb=2001,
        instance_details=CloudInstanceDetails.M6I_XLARGE,
    )
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    send_housekeeping_requested_event(kafka_mgr, data_protected_gb=0)
    verify_housekeeping_requested_event(kafka_mgr, data_protected_gb=0)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr, backup_streams=None)
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=CloudInstanceDetails.M6I_XLARGE,
    )
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
