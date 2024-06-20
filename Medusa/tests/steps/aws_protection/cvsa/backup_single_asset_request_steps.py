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
from tests.steps.aws_protection.cvsa.kafka_steps import wait_for_event
from tests.steps.aws_protection.cvsa.requested_event_base import set_requested_event_base

logger = logging.getLogger()


def send_backup_single_asset_requested_event(
    kafka_manager: KafkaManager,
    headers: dict = None,
    cloud_region: CloudRegions = AWS_REGION_1_ENUM,
    ami=None,
    update_offsets=True,
):
    kafka_manager.correlation_id = kafka_manager.generate_key()
    if not headers:
        headers = {}

    headers.update(
        {
            "ce_id": kafka_manager.account_id,
            "ce_type": b"cvsa.v1.CVSABackupSingleAssetRequestedEvent",
            "ce_partitionkey": kafka_manager.account_id,
            "ce_customerid": kafka_manager.account_id,
        }
    )
    if ami is not None:
        headers["ce_forcedcvsaimageid"] = bytes(ami, "utf-8")
    requested_event = cvsa_manager_pb2.CVSABackupSingleAssetRequestedEvent()
    set_requested_event_base(kafka_manager, requested_event, cloud_region)
    logger.info(f"Send message: cvsa.v1.CVSABackupSingleAssetRequestedEvent, customer_id: {kafka_manager.account_id}")
    kafka_manager.send_message(requested_event, headers, update_offsets=update_offsets)


def verify_backup_single_asset_requested_event(
    kafka: KafkaManager,
    cloud_region: CloudRegions = AWS_REGION_1_ENUM,
    ami=None,
):
    event_type = "cvsa.v1.CVSABackupSingleAssetRequestedEvent"
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
    logger.info(f"Message found cvsa.v1.CVSABackupSingleAssetRequestedEvent: {message}")
    message_base = message.value["base"]
    if ami is not None:
        headers = dict(map(lambda x: (x[0], x[1]), message.headers))
        assert headers["ce_forcedcvsaimageid"] == bytes(ami, "utf-8")
    assert message_base["cloudProvider"] == str(CloudProvider.AWS)
    assert message_base["cloudRegion"] == str(cloud_region)
    assert message_base["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)
    assert message_base["camAccountId"] == kafka.cam_account_id.decode("utf-8")
    assert message_base["cspAccountId"] == kafka.csp_account_id.decode("utf-8")
    assert message_base["correlationId"] == kafka.correlation_id.decode("utf-8")
    logger.info("Message verified cvsa.v1.CVSABackupSingleAssetRequestedEvent")
