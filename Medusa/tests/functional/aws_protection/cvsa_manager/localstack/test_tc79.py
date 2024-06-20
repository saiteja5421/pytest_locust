"""
TC79: CVSAUnprotectRequestedEvent scenarios
    1. Send CVSAUnprotectRequestedEvent with AccountUnprotectedByDPM or AccountUnprotectedByACLM
    2. Expect handling the unprotect request for the account not registered earlier in the cVSA Manager
       and receiving CVSAUnprotectRequestFinishedEvent
    3. Send CspAccountInfo(Status=Unregistered)
    4. Send CspAccountInfo(Status=Registered) to test explicit re-registration
    5. Create a new instance, by sending backup request
    6. Send CVSAUnprotectRequestedEvent with AccountUnprotectedByDPM or AccountUnprotectedByACLM
    7. Expect RequestFinishedEvent which invalidates the pending request because of
       the unregistration
    8. Expect finished event for unprotect
    9. Verify backup requested event and expect ready event, meaning that request was processed successfully
    10. Send CVSAUnprotectRequestedEvent with a header forcing unprotect cleanup to fail
    11. Expect CVSAUnprotectRequestFinishedEvent with status Error
TC83: Resilient cleanup process
    1. Send CspAccountInfo(Status=Unregistered) for the existing account. Use forced behavior to force one-time failure
    of the cleanup process
    2. Expect that cleanup process is triggered again and resources are cleaned correctly
"""

import copy

from pytest import mark

from lib.common.enums.cvsa import RequestFinishedStatus, TerminateReason
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cam_updates_kafka_steps import (
    send_register_event,
    verify_register_event,
    send_unregister_event,
    verify_unregister_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
    verify_terminated_event,
    verify_ready_event,
)
from tests.steps.aws_protection.cvsa.unprotect_requested_event import (
    send_unprotect_requested_event,
    verify_unprotect_requested_event,
    verify_finished_event_for_unprotect,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
@mark.parametrize("state_type", ["DPM", "ACLM"])
def test_tc79(
    kafka_mgr: KafkaManager,
    cam_updates_kafka: KafkaManager,
    aws: CloudVmManager,
    state_type: str,
):
    # Verify that CVSAUnprotectRequestedEvent can be successfully handled
    # even if account was previously not registered in the cVSA Manager
    send_unprotect_requested_event(kafka_mgr, state_type=state_type)
    verify_unprotect_requested_event(kafka_mgr, state_type=state_type)
    verify_finished_event_for_unprotect(kafka_mgr)

    # Send CspAccountInfo(Unregistered) to verify re-registration scenario in the next step
    send_unregister_event(kafka_mgr, cam_updates_kafka)
    verify_unregister_event(kafka_mgr, cam_updates_kafka)
    # Send CVSAUnprotectRequestedEvent again to know when the cleanup is finished
    # and account can be re-registered.
    send_unprotect_requested_event(kafka_mgr, state_type=state_type)
    verify_unprotect_requested_event(kafka_mgr, state_type=state_type)
    verify_finished_event_for_unprotect(kafka_mgr)

    # Send CspAccountInfo(Registered) to "reset" the unprotect status of the account
    send_register_event(kafka_mgr, cam_updates_kafka)
    verify_register_event(kafka_mgr, cam_updates_kafka)

    # Create new instance
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    backup_kafka_mgr = copy.copy(kafka_mgr)

    # Verify that unprotect clean up is performed
    send_unprotect_requested_event(kafka_mgr, state_type=state_type)
    verify_unprotect_requested_event(kafka_mgr, state_type=state_type)

    verify_finished_event(
        backup_kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="request invalidated due customer unregistration",
    )

    verify_terminated_event(kafka_mgr, reason=TerminateReason.CUSTOMER_UNREGISTER)
    verify_finished_event_for_unprotect(kafka_mgr)

    # Verify that Backup request can be processed after the Unprotect Event
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_ready_event(kafka_mgr)

    # Send CVSAUnprotectRequestedEvent and force the failure of the cleanup process (using Forced Behavior)
    # Verify that CVSAUnprotectFinished with ERROR status received
    send_unprotect_requested_event(
        kafka_mgr,
        state_type=state_type,
        headers={
            "ce_forcedfailedunreg": bytes("true", "utf-8"),
        },
    )
    verify_unprotect_requested_event(kafka_mgr, state_type=state_type)
    verify_finished_event_for_unprotect(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="failed due to forced behavior",
    )

    # Send CspAccountInfo(Unregistered) and force the one-time failure of the cleanup process (using Forced Behavior)
    # Verify that cleanup process is triggered again and this time it succeeds
    send_unregister_event(
        kafka_mgr,
        cam_updates_kafka,
        headers={
            "ce_forcedfailedunreg": bytes("true", "utf-8"),
        },
    )
    verify_unregister_event(kafka_mgr, cam_updates_kafka)
    verify_terminated_event(kafka_mgr, reason=TerminateReason.CUSTOMER_UNREGISTER)
