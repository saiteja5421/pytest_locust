"""
TC-51: Delete Request as first request for client (no cVSA backup request before)
    Send Delete Request.
    Verify error message.
"""

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.housekeeping_request_steps import (
    send_housekeeping_requested_event,
    verify_housekeeping_requested_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc51(aws: CloudVmManager, kafka_mgr):
    send_housekeeping_requested_event(kafka_mgr, data_protected_gb=0)
    verify_housekeeping_requested_event(kafka_mgr, data_protected_gb=0)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="housekeeping request cannot be performed without existing configured cVSA",
    )
