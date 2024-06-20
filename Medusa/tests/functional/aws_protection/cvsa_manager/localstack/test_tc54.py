"""
TC-54: Send two restore requests. Verify that there are created two different read only replicas
       Verify deletion of Read Only Replica after restore request is finished
"""

import logging

from pytest import fixture, mark

from lib.common.enums.cvsa import StopReason
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_models import CvsaEvent
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_trace_id
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.assertions import assert_volumes_deleted, assert_one_cvsa_created
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_terminated
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_restore_steps import (
    create_main_cvsa_instance,
    verify_restore_created_event,
    send_restore_requested_event,
    verify_restore_requested_event,
    verify_restore_ready_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events


@fixture(scope="function")
def kafka_mgr(aws):
    kafka_mgr_main = new_kafka_lifecycle_events(tc_id=54)
    kafka_mgr_ro_1 = new_kafka_lifecycle_events(tc_id=54, account_id=kafka_mgr_main.account_id)
    kafka_mgr_ro_2 = new_kafka_lifecycle_events(tc_id=54, account_id=kafka_mgr_main.account_id)
    kafka_mgr_ro_1.csp_account_id = kafka_mgr_main.csp_account_id
    kafka_mgr_ro_1.cam_account_id = kafka_mgr_main.cam_account_id
    kafka_mgr_ro_2.csp_account_id = kafka_mgr_main.csp_account_id
    kafka_mgr_ro_2.cam_account_id = kafka_mgr_main.cam_account_id
    yield kafka_mgr_main, kafka_mgr_ro_1, kafka_mgr_ro_2
    logger = logging.getLogger()
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    cleanup_cvsa_instance(kafka_mgr_main, aws)
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc54(kafka_mgr, aws: CloudVmManager):
    kafka_mgr_main, kafka_mgr_ro_1, kafka_mgr_ro_2 = kafka_mgr
    create_main_cvsa_instance(kafka_mgr_main, aws)

    send_restore_requested_event(kafka_mgr_ro_1, recovery_gigabytes=1)
    send_restore_requested_event(kafka_mgr_ro_2, recovery_gigabytes=1)

    first_read_only_replica = verify_read_only_replica(kafka_mgr_ro_1)
    second_read_only_replica = verify_read_only_replica(kafka_mgr_ro_2)

    verify_instances(first_read_only_replica, second_read_only_replica)

    send_finished_event_for_restore(kafka_mgr_ro_1, aws)
    send_finished_event_for_restore(kafka_mgr_ro_2, aws)


def verify_read_only_replica(kafka_mgr: KafkaManager) -> CvsaEvent:
    verify_restore_requested_event(kafka_mgr, 1)
    verify_restore_created_event(kafka_mgr, event_filters=[event_filter_trace_id(kafka_mgr.trace_id)])
    return verify_restore_ready_event(kafka_mgr)


def verify_instances(first_instance: CvsaEvent, second_instance: CvsaEvent):
    assert first_instance.cvsa_id != second_instance.cvsa_id
    assert first_instance.address != second_instance.address

    assert first_instance.cloud_region == second_instance.cloud_region
    assert first_instance.cloud_provider == second_instance.cloud_provider
    assert first_instance.catalyst_store == second_instance.catalyst_store


def send_finished_event_for_restore(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager):
    instance = assert_one_cvsa_created(kafka_mgr, cloud_vm_mgr)

    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    verify_stopped_event(kafka_mgr, reason=StopReason.IDLE)
    verify_instance_terminated(cloud_vm_mgr, instance.id)
    assert_volumes_deleted(cloud_vm_mgr, volumes=[*instance.data_disks, instance.os_disk])
