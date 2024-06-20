"""
TC-59: Verify that:
 * store report events are emitted for other instances
 * lifecycle events (like CVSAStoppedEvent) sent with the invalid source are ignored, so report events are still emitted
 * store report events are not emitted for Read Only Replicas
"""

import logging
from pytest import fixture, mark

from lib.common.enums.cvsa import TerminateReason
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cvsa_manager_restore_steps import (
    create_read_only_replica,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_terminated_event,
    create_new_cvsa_instance_and_validate,
    send_cvsa_stopped_event,
)
from tests.steps.aws_protection.cvsa.kafka_steps import (
    verify_no_billing_event_is_emitted,
    verify_no_store_deleted_event_is_emitted,
    verify_billing_events_are_emitted,
)


@fixture(scope="function")
def billing_kafka(kafka_mgr):
    return KafkaManager("atlas.reports.events", tc_id=59, account_id=kafka_mgr.account_id)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc59(kafka_mgr, billing_kafka, aws: CloudVmManager):
    logging.info("Step 1. Create cVSA instance and verify that store report events are emitted")
    cvsa_instance = create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    verify_billing_events_are_emitted(billing_kafka, cvsa_instance.cvsa_id, 1)

    logging.info("Step 2. Send CVSAStoppedEvent and verify that cvsa-manager ignores it because of the invalid source")
    # When CVSAStoppedEvent is received from the correct source (this is an internal event, so it should be produced
    # only by the cvsa-manager itself), the monitoring workflow is stopped, and billing events are not emitted.
    # Here we produce CVSAStoppedEvent with a different value in the 'ce_source' header than expected by cvsa-manager,
    # so billing events are expected to still be emitted.
    send_cvsa_stopped_event(kafka_mgr, cvsa_instance.cvsa_id)
    verify_billing_events_are_emitted(billing_kafka, cvsa_instance.cvsa_id, 2)
    send_finished_event(kafka_mgr)

    logging.info("Step 3. Create RO replica and verify that store report events are not emitted for this instance")
    read_only_cvsa = create_read_only_replica(kafka_mgr)
    verify_no_billing_event_is_emitted(billing_kafka, read_only_cvsa.cvsa_id)
    send_finished_event(kafka_mgr)
    verify_terminated_event(kafka_mgr, TerminateReason.READ_ONLY_REQUEST_FINISHED)
    verify_no_store_deleted_event_is_emitted(billing_kafka, read_only_cvsa.cvsa_id)
