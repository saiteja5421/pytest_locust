"""
TC-52: Delete Request when Backup Request is not finished
    1. Create cVSA instance for customer without sending Finished Event.
    2. Send Delete Request.
    3. Verify error message.
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
)
from tests.steps.aws_protection.cvsa.housekeeping_request_steps import (
    send_housekeeping_requested_event,
    verify_housekeeping_requested_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc52(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_housekeeping_requested_event(kafka_mgr, data_protected_gb=0)
    verify_housekeeping_requested_event(kafka_mgr, data_protected_gb=0)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="parallel housekeeping/backup cvsa requested events not allowed",
    )
