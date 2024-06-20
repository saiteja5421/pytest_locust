import logging

import lib.platform.kafka.protobuf.cvsa_manager.cvsa_manager_pb2 as cvsa_manager_pb2
from lib.common.enums.cvsa import (
    CloudProvider,
    ProtectedAssetType,
    CloudRegions,
)
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_correlation_id
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import AWS_REGION_1_ENUM
from tests.steps.aws_protection.cvsa.cloud_steps import get_default_region
from tests.steps.aws_protection.cvsa.kafka_steps import wait_for_event
from tests.steps.aws_protection.cvsa.requested_event_base import set_requested_event_base
from utils.size_conversion import gb_to_bytes

logger = logging.getLogger()


def send_housekeeping_requested_event(
    kafka_manager: KafkaManager,
    data_protected_gb,
    headers: dict = None,
    update_offsets=True,
    target_duration_seconds=None,
    cloud_provider: CloudProvider = CloudProvider.AWS,
):
    cloud_region = get_default_region(cloud_provider=cloud_provider)
    kafka_manager.correlation_id = kafka_manager.generate_key()
    if not headers:
        headers = {}

    headers.update(
        {
            "ce_id": kafka_manager.account_id,
            "ce_type": b"cvsa.v1.CVSAHousekeepingBatchRequestedEvent",
            "ce_partitionkey": kafka_manager.account_id,
            "ce_customerid": kafka_manager.account_id,
        }
    )
    requested_event = cvsa_manager_pb2.CVSAHousekeepingBatchRequestedEvent()
    set_requested_event_base(kafka_manager, requested_event, cloud_region, cloud_provider)
    requested_event.data_protected_bytes = gb_to_bytes(data_protected_gb)
    if target_duration_seconds:
        requested_event.target_duration_seconds = target_duration_seconds
    uint64_fields = [
        "dataProtectedBytes",
        "targetDurationSeconds",
    ]
    logger.info(f"Send message: cvsa.v1.CVSAHousekeepingBatchRequestedEvent, customer_id: {kafka_manager.account_id}")
    kafka_manager.send_message(requested_event, headers, uint64_fields, update_offsets=update_offsets)


def verify_housekeeping_requested_event(
    kafka: KafkaManager,
    data_protected_gb=0,
    cloud_provider: CloudProvider = CloudProvider.AWS,
):
    cloud_region = get_default_region(cloud_provider=cloud_provider)
    event_type = "cvsa.v1.CVSAHousekeepingBatchRequestedEvent"
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
    logger.info(f"Message found cvsa.v1.CVSAHousekeepingBatchRequestedEvent: {message}")
    message_base = message.value["base"]
    assert message_base["cloudProvider"] == str(cloud_provider)
    assert message_base["cloudRegion"] == str(cloud_region)
    assert message_base["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)
    assert message_base["camAccountId"] == kafka.cam_account_id.decode("utf-8")
    assert message_base["cspAccountId"] == kafka.csp_account_id.decode("utf-8")
    assert message_base["correlationId"] == kafka.correlation_id.decode("utf-8")
    if data_protected_gb:
        assert message.value["dataProtectedBytes"] == gb_to_bytes(data_protected_gb)
    logger.info("Message verified cvsa.v1.CVSAHousekeepingBatchRequestedEvent")


def send_housekeeping_requested_event_ms365(
    kafka_manager: KafkaManager,
    headers: dict = None,
    cloud_region: CloudRegions = AWS_REGION_1_ENUM,
    update_offsets=True,
):
    kafka_manager.correlation_id = kafka_manager.generate_key()
    if not headers:
        headers = {}

    headers.update(
        {
            "ce_id": kafka_manager.account_id,
            "ce_type": b"cvsa.v1.CVSAMicrosoft365HousekeepingBatchRequestedEvent",
            "ce_partitionkey": kafka_manager.account_id,
            "ce_customerid": kafka_manager.account_id,
        }
    )
    requested_event = cvsa_manager_pb2.CVSAMicrosoft365HousekeepingBatchRequestedEvent()
    set_requested_event_base(kafka_manager, requested_event, cloud_region)
    logger.info(
        f"Send message: cvsa.v1.CVSAMicrosoft365HousekeepingBatchRequestedEvent, customer_id: {kafka_manager.account_id}"
    )
    kafka_manager.send_message(requested_event, headers, update_offsets=update_offsets)
