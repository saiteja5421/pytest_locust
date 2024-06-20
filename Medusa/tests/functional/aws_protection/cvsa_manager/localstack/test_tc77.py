"""
TC77: Test maximum number of parallel read only requests per customer region
    - when threshold is reached, all next requests should be rejected
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_cam_id, event_filter_customer_id
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.common_steps import get_max_parallel_ro_requests
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    send_finished_event,
    create_new_cvsa_instance_and_validate,
)
from tests.steps.aws_protection.cvsa.restore_kafka_steps import (
    send_restore_requested_event,
)

MAX_RO_REQUESTS = get_max_parallel_ro_requests()


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc77(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    for i in range(0, MAX_RO_REQUESTS + 1):
        send_restore_requested_event(kafka_mgr, 1)

    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg=f"requester: parallel restore requests are limited to {MAX_RO_REQUESTS} per customer region",
        event_filters=[event_filter_cam_id(kafka_mgr.cam_account_id), event_filter_customer_id(kafka_mgr.account_id)],
    )
