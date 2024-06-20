"""
TC05: Backup/restore request when cVSA Instance need resize. Check if the volume was resized. Upscale of EBS volume
    1. Verify that EBS size and cloudbank.
    2. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA)
    2. Check cVSAStoppedEvent
    3. Check cVSAStartedEvent  (to ensure that instance is running, happens always)
    5. Check cVSAResizedEvent
    6. Check cVSAReadyEvent
    7. Verify that EBS size was changed
"""

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_created_event,
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_resize_event,
    wait_for_event,
    verify_instance_type_and_volume_size,
)
from tests.steps.aws_protection.cvsa.restore_request_steps import (
    send_restore_requested_event,
    verify_restore_requested_event,
)


@mark.order(500)
@mark.cvsa_localstack
@mark.cvsa_localstack_pr
@mark.parametrize(
    "prev_protected_data_gb, changed_bytes, protected_data_gb, volume_usage, instance_details, streams, expected_volume_size, request_method",
    [
        (1, 0.2, 5_000, 0, CloudInstanceDetails.C6I_2XLARGE, 8, 65e9, send_backup_requested_event),
        (1_000, 200, 5_000, 69e9, CloudInstanceDetails.C6I_2XLARGE, 8, 143.1e9, send_backup_requested_event),
        (1_000, 1_000, 5_000, 69e9, CloudInstanceDetails.C6I_2XLARGE, 8, 151.9e9, send_backup_requested_event),
        (1_000, 0, 60_000, 0, CloudInstanceDetails.C6I_24XLARGE, 20, 672.2e9, send_backup_requested_event),
        (10_000, 5_000, 60_000, 100e9, CloudInstanceDetails.C6I_24XLARGE, 21, 835e9, send_backup_requested_event),
        (0, 0, 10, 0, CloudInstanceDetails.R6I_LARGE, 8, 50e9, send_restore_requested_event),
        (0, 0, 5_000, 0, CloudInstanceDetails.C6I_4XLARGE, 8, 50e9, send_restore_requested_event),
    ],
)
def test_tc05(
    kafka_mgr,
    aws: CloudVmManager,
    prev_protected_data_gb,
    changed_bytes,
    protected_data_gb,
    volume_usage,
    instance_details,
    streams,
    expected_volume_size,
    request_method,
):
    billing_kafka = start_billing_events_consumer(kafka_mgr)
    prepare_cvsa_instance(kafka_mgr, aws, int(volume_usage))
    wait_for_monitoring_workflow(billing_kafka)
    if request_method == send_backup_requested_event:
        send_backup_request(kafka_mgr, prev_protected_data_gb, changed_bytes, protected_data_gb)
        verify_resize(kafka_mgr, protected_data_gb, instance_details, int(expected_volume_size), streams)
    if request_method == send_restore_requested_event:
        send_restore_request(kafka_mgr, prev_protected_data_gb)
    verify_instance_type_and_volume_size(
        aws,
        kafka_mgr.cvsa_id,
        instance_details,
        volume_size_bytes=int(expected_volume_size),
        strict_instance_details=True,
    )


def start_billing_events_consumer(cvsa_kafka: KafkaManager) -> KafkaManager:
    billing_kafka = KafkaManager("atlas.reports.events", tc_id=5)
    billing_kafka.account_id = cvsa_kafka.account_id
    return billing_kafka


def prepare_cvsa_instance(kafka_mgr: KafkaManager, aws: CloudVmManager, volume_usage: int):
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws,
        kafka_mgr=kafka_mgr,
        data_protected_gb=1,
        instance_details=CloudInstanceDetails.R6I_LARGE,
        headers={
            "ce_forcedvolumeusage": bytes(str(volume_usage), "utf-8"),
        },
    )
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)


def wait_for_monitoring_workflow(billing_kafka: KafkaManager):
    event_type = "cloud.catalyst.gateway.utilization.update"
    wait_for_event(kafka_manager=billing_kafka, event_type=event_type)


def send_restore_request(kafka_mgr: KafkaManager, protected_data_gb):
    send_restore_requested_event(
        kafka_mgr,
        data_protected_gb=protected_data_gb,
    )
    verify_restore_requested_event(
        kafka_mgr,
        data_protected_gb=protected_data_gb,
    )
    verify_created_event(kafka_mgr, backup_streams=None, restore_streams=8)
    verify_started_event(kafka_mgr)


def send_backup_request(kafka_mgr: KafkaManager, prev_protected_data_gb, changed_bytes, protected_data_gb):
    send_backup_requested_event(
        kafka_mgr,
        data_protected_gb=protected_data_gb,
        data_protected_previous_gb=prev_protected_data_gb,
        data_protected_previous_changed_bytes=changed_bytes,
    )
    verify_backup_requested_event(
        kafka_mgr,
        data_protected_gb=protected_data_gb,
        data_protected_previous_gb=prev_protected_data_gb,
        data_protected_previous_changed_gb=changed_bytes,
    )
    verify_started_event(kafka_mgr)


def verify_resize(
    kafka_mgr: KafkaManager,
    protected_data_gb,
    instance_details,
    expected_volume_size,
    backup_streams,
):
    verify_resize_event(
        kafka_mgr,
        data_protected_gb=protected_data_gb,
        instance_details=instance_details,
        volume_size_bytes=expected_volume_size,
        backup_streams=backup_streams,
        strict_instance_details=True,
    )
    verify_ready_event(
        kafka_mgr,
        instance_details=instance_details,
        volume_size_bytes=expected_volume_size,
        backup_streams=backup_streams,
        strict_instance_details=True,
    )
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
