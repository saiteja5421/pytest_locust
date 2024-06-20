import logging

import assertpy

import lib.platform.kafka.protobuf.cvsa_manager.cvsa_manager_pb2 as cvsa_manager_pb2
from lib.common.enums.cvsa import (
    CloudProvider,
    ProtectedAssetType,
    CloudRegions,
)
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_correlation_id
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import get_default_region
from tests.steps.aws_protection.cvsa.kafka_steps import wait_for_event
from tests.steps.aws_protection.cvsa.requested_event_base import set_requested_event_base
from utils.size_conversion import gb_to_bytes

logger = logging.getLogger()


def send_backup_requested_event(
    kafka_manager: KafkaManager,
    data_protected_gb,
    data_protected_previous_gb=0,
    headers: dict = None,
    cloud_region: CloudRegions = None,
    ami=None,
    update_offsets=True,
    data_protected_previous_changed_bytes=0,
    target_duration_seconds=None,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    kafka_manager.correlation_id = kafka_manager.generate_key()
    if not headers:
        headers = {}

    headers.update(
        {
            "ce_id": kafka_manager.account_id,
            "ce_type": b"cvsa.v1.CVSABackupBatchRequestedEvent",
            "ce_partitionkey": kafka_manager.account_id,
            "ce_customerid": kafka_manager.account_id,
        }
    )
    if ami is not None:
        headers["ce_forcedcvsaimageid"] = bytes(ami, "utf-8")
    requested_event = cvsa_manager_pb2.CVSABackupBatchRequestedEvent()
    set_requested_event_base(kafka_manager, requested_event, cloud_region=cloud_region, cloud_provider=cloud_provider)
    requested_event.data_protected_new_bytes = gb_to_bytes(data_protected_gb)
    requested_event.data_protected_previous_bytes = gb_to_bytes(data_protected_previous_gb)
    requested_event.data_protected_previous_changed_bytes = gb_to_bytes(data_protected_previous_changed_bytes)
    if target_duration_seconds:
        requested_event.target_duration_seconds = target_duration_seconds
    uint64_fields = [
        "dataProtectedNewBytes",
        "dataProtectedPreviousBytes",
        "dataProtectedPreviousChangedBytes",
        "targetDurationSeconds",
    ]
    logger.info(f"Send message: cvsa.v1.CVSABackupBatchRequestedEvent, customer_id: {kafka_manager.account_id}")
    kafka_manager.send_message(requested_event, headers, uint64_fields, update_offsets=update_offsets)


def send_backup_requested_event_ms365(
    kafka_manager: KafkaManager,
    data_protected_gb=0,
    data_protected_previous_gb=0,
    data_protected_previous_changed_bytes=0,
    headers: dict = None,
    cloud_region: CloudRegions = None,
    ami=None,
    update_offsets=True,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    kafka_manager.correlation_id = kafka_manager.generate_key()
    if not headers:
        headers = {}

    headers.update(
        {
            "ce_id": kafka_manager.account_id,
            "ce_type": b"cvsa.v1.CVSAMicrosoft365BackupBatchRequestedEvent",
            "ce_partitionkey": kafka_manager.account_id,
            "ce_customerid": kafka_manager.account_id,
        }
    )
    if ami is not None:
        headers["ce_forcedcvsaimageid"] = bytes(ami, "utf-8")
    requested_event = cvsa_manager_pb2.CVSAMicrosoft365BackupBatchRequestedEvent()
    set_requested_event_base(kafka_manager, requested_event, cloud_region=cloud_region, cloud_provider=cloud_provider)
    requested_event.data_protected_new_bytes = gb_to_bytes(data_protected_gb)
    requested_event.data_protected_previous_bytes = gb_to_bytes(data_protected_previous_gb)
    requested_event.data_protected_previous_changed_bytes = gb_to_bytes(data_protected_previous_changed_bytes)
    logger.info(
        f"Send message: cvsa.v1.CVSAMicrosoft365BackupBatchRequestedEvent, customer_id: {kafka_manager.account_id}"
    )
    uint64_fields = [
        "dataProtectedNewBytes",
        "dataProtectedPreviousBytes",
        "dataProtectedPreviousChangedBytes",
    ]
    kafka_manager.send_message(requested_event, headers, uint64_fields, update_offsets=update_offsets)


def verify_backup_requested_event(
    kafka: KafkaManager,
    data_protected_gb,
    data_protected_previous_gb=0,
    data_protected_previous_changed_gb=0,
    cloud_region: CloudRegions = None,
    ami=None,
    target_duration_seconds=None,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    event_type = "cvsa.v1.CVSABackupBatchRequestedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, region: {cloud_region}. from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    message = wait_for_event(
        kafka,
        event_type,
        cloud_region=cloud_region,
        event_filters=[event_filter_correlation_id(kafka.correlation_id)],
        timeout=Timeout.REQUESTED_EVENT.value,
    )
    logger.info(f"Message found cvsa.v1.CVSABackupBatchRequestedEvent: {message}")
    message_base = message.value["base"]
    if ami is not None:
        headers = dict(map(lambda x: (x[0], x[1]), message.headers))
        assert headers["ce_forcedcvsaimageid"] == bytes(ami, "utf-8")
    assert message_base["cloudProvider"] == str(cloud_provider)
    assert message_base["cloudRegion"] == str(cloud_region), f'{message_base["cloudRegion"]} != {str(cloud_region)}'
    assert message_base["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)
    assert message.value["dataProtectedNewBytes"] == gb_to_bytes(data_protected_gb)
    assert message_base["camAccountId"] == kafka.cam_account_id.decode("utf-8")
    assert message_base["cspAccountId"] == kafka.csp_account_id.decode("utf-8")
    assert message_base["correlationId"] == kafka.correlation_id.decode("utf-8")
    if target_duration_seconds:
        assert message.value["targetDurationSeconds"] == target_duration_seconds
    if data_protected_previous_gb:
        assert message.value["dataProtectedPreviousBytes"] == gb_to_bytes(data_protected_previous_gb)
    if data_protected_previous_changed_gb:
        assert message.value["dataProtectedPreviousChangedBytes"] == gb_to_bytes(data_protected_previous_changed_gb)
    logger.info("Message verified cvsa.v1.CVSABackupBatchRequestedEvent")


def verify_backup_requested_event_ms365(
    kafka: KafkaManager,
    data_protected_gb,
    data_protected_previous_gb=0,
    data_protected_previous_changed_gb=0,
    cloud_region: CloudRegions = None,
    ami=None,
    target_duration_seconds=None,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    event_type = "cvsa.v1.CVSAMicrosoft365BackupBatchRequestedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, region: {cloud_region}. from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    message = wait_for_event(
        kafka,
        event_type,
        cloud_region=cloud_region,
        event_filters=[event_filter_correlation_id(kafka.correlation_id)],
        timeout=Timeout.REQUESTED_EVENT.value,
    )
    logger.info(f"Message found cvsa.v1.CVSAMicrosoft365BackupBatchRequestedEvent: {message}")
    message_base = message.value["base"]
    if ami is not None:
        headers = dict(map(lambda x: (x[0], x[1]), message.headers))
        assert headers["ce_forcedcvsaimageid"] == bytes(ami, "utf-8")
    assert message_base["cloudProvider"] == str(cloud_provider)
    assert message_base["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)
    assertpy.assert_that(message_base["cloudRegion"]).is_equal_to(str(cloud_region))
    assert message_base["camAccountId"] == kafka.cam_account_id.decode("utf-8")
    assert message_base["cspAccountId"] == kafka.csp_account_id.decode("utf-8")
    assert message_base["correlationId"] == kafka.correlation_id.decode("utf-8")
    if target_duration_seconds:
        assert message.value["targetDurationSeconds"] == target_duration_seconds
    if data_protected_previous_gb:
        assert message.value["dataProtectedPreviousBytes"] == gb_to_bytes(data_protected_previous_gb)
    if data_protected_previous_changed_gb:
        assert message.value["dataProtectedPreviousChangedBytes"] == gb_to_bytes(data_protected_previous_changed_gb)
    logger.info("Message verified cvsa.v1.CVSAMicrosoft365BackupBatchRequestedEvent")
