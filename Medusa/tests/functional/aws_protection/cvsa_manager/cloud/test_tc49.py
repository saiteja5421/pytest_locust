"""
TC49: Delete Request when customer already performed at least one backup request
    Create cVSA instance for customer.
    Send FinishedEvent.
    Send Delete Request.
    Verify Started Event.
    Verify Ready Event.
"""

from pytest import mark

from lib.platform.cloud.cloud_vm_manager import CloudVmManager, cloud_vm_managers_names
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.housekeeping_request_steps import (
    send_housekeeping_requested_event,
    verify_housekeeping_requested_event,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials


@mark.order(200)
@mark.cvsa_aws
@mark.cvsa_cloud
@mark.cvsa_azure
@mark.parametrize("cloud_vm_mgr", cloud_vm_managers_names())
def test_tc49(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager, request):
    cloud_vm_mgr = request.getfixturevalue(cloud_vm_mgr)

    create_new_cvsa_instance_and_validate(cloud_vm_mgr=cloud_vm_mgr, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
    verify_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())

    send_housekeeping_requested_event(kafka_mgr, data_protected_gb=0, cloud_provider=cloud_vm_mgr.name())
    verify_housekeeping_requested_event(kafka_mgr, data_protected_gb=0, cloud_provider=cloud_vm_mgr.name())

    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr, backup_streams=None, cloud_provider=cloud_vm_mgr.name())
    verify_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka_mgr.cvsa_id)
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)

    send_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
    verify_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
