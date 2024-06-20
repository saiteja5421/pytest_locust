import logging
from typing import Union

import lib.platform.kafka.protobuf.cvsa_manager.cvsa_manager_pb2 as cvsa_manager_pb2
from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import (
    RequestType,
    AwsRegions,
    CloudProvider,
    ProtectedAssetType,
    CloudVolumeType,
)
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_allowed_instances import get_instance_details_by_name, is_allowed
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_models import CvsaEvent
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.kafka.eventfilters import EventFilter
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_correlation_id
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import AWS_REGION_1_ENUM
from tests.steps.aws_protection.cvsa.assertions import assert_volume_bytes_size
from tests.steps.aws_protection.cvsa.kafka_steps import wait_for_event
from utils.size_conversion import gb_to_bytes

logger = logging.getLogger()


def verify_restore_message_data(cvsa_model, instance_details=CloudInstanceDetails.R6I_LARGE, restore_streams=8):
    instance_details: CloudInstanceDetails = instance_details.value
    assert cvsa_model.address
    if cvsa_model.cloud_resources.compute_type == instance_details.instance_type:
        assert cvsa_model.cloud_resources.compute_type == instance_details.instance_type
        assert cvsa_model.cloud_resources.cpu == instance_details.cpu
        assert cvsa_model.cloud_resources.ram == instance_details.ram
        logger.info(f"Ec2 type correctly sized, wanted: {instance_details}, given: {cvsa_model.cloud_resources}")
    else:
        logger.error(
            f"Given instance type not match requested instance type. Given: {cvsa_model.cloud_resources},"
            f" Requested: {instance_details}"
        )
        given_instance = get_instance_details_by_name(cvsa_model.cloud_resources.compute_type)
        assert is_allowed(
            instance_details, given_instance
        ), f"Instance is oversized, wanted: {instance_details}, given: {given_instance}"
        assert cvsa_model.cloud_resources.compute_type == given_instance.value.instance_type
        assert cvsa_model.cloud_resources.cpu == given_instance.value.cpu
        assert cvsa_model.cloud_resources.ram == given_instance.value.ram
    assert cvsa_model.cloud_resources.backup_streams is None
    assert cvsa_model.cloud_resources.restore_streams == restore_streams
    assert_volume_bytes_size(int(cvsa_model.cloud_resources.data_volume.size_bytes), 50000000000)
    if cvsa_model.cloud_provider == str(CloudProvider.AWS):
        assert cvsa_model.cloud_resources.data_volume.type == str(CloudVolumeType.AWS_GP3)
    else:
        assert cvsa_model.cloud_resources.data_volume.type == str(CloudVolumeType.AZURE_PREMIUMSSD)


def send_restore_requested_event(
    kafka_manager: KafkaManager,
    recovery_gigabytes: int = 0,
    headers: dict = None,
    cloud_region: AwsRegions = AWS_REGION_1_ENUM,
    cloud_provider: CloudProvider = CloudProvider.AWS,
):
    kafka_manager.correlation_id = kafka_manager.generate_key()
    if not headers:
        headers = {}

    headers.update(
        {
            "ce_id": kafka_manager.account_id,
            "ce_type": b"cvsa.v1.CVSARequestedEvent",
            "ce_partitionkey": kafka_manager.account_id,
            "ce_customerid": kafka_manager.account_id,
        }
    )
    requested_event = cvsa_manager_pb2.CVSARequestedEvent()
    requested_event.correlation_id = kafka_manager.correlation_id.decode("utf-8")
    requested_event.csp_account_id = kafka_manager.csp_account_id.decode("utf-8")
    requested_event.cam_account_id = kafka_manager.cam_account_id.decode("utf-8")
    requested_event.data_protected_recovered_bytes = gb_to_bytes(recovery_gigabytes)
    requested_event.request_type = RequestType.RESTORE.value
    requested_event.cloud_provider = cloud_provider.value
    requested_event.cloud_region = cloud_region.value
    requested_event.protected_asset_type = cvsa_manager_pb2.PROTECTED_ASSET_TYPE_ENUM_AWS_EBS
    uint64_fields = [
        "dataProtectedNewBytes",
        "dataProtectedPreviousBytes",
        "dataProtectedPreviousChangedBytes",
        "dataProtectedRecoveredBytes",
        "targetDurationSeconds",
    ]
    logger.info(f"Send message: cvsa.v1.CVSARequestedEvent, customer_id: {kafka_manager.account_id}")
    kafka_manager.send_message(requested_event, headers, uint64_fields, update_offsets=True)


def verify_restore_requested_event(
    kafka: KafkaManager,
    recovery_bytes,
    cloud_region: AwsRegions = AWS_REGION_1_ENUM,
    cloud_provider: CloudProvider = CloudProvider.AWS,
):
    event_type = "cvsa.v1.CVSARequestedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, region: {cloud_region}. from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}, correlation id: {kafka.correlation_id} for restore"
    )
    message = wait_for_event(
        kafka,
        event_type,
        cloud_region=cloud_region,
        event_filters=[event_filter_correlation_id(kafka.correlation_id)],
        timeout=Timeout.REQUESTED_EVENT.value,
    )
    logger.info(f"Message found cvsa.v1.CVSARequestedEvent for restore: {message}")

    assert message.value["cloudProvider"] == str(cloud_provider)
    assert message.value["cloudRegion"] == str(cloud_region)
    assert message.value["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)
    assert message.value["dataProtectedRecoveredBytes"] == gb_to_bytes(recovery_bytes)
    assert message.value["camAccountId"] == kafka.cam_account_id.decode("utf-8")
    assert message.value["cspAccountId"] == kafka.csp_account_id.decode("utf-8")
    assert message.value["correlationId"] == kafka.correlation_id.decode("utf-8")
    assert message.value["requestType"] == str(RequestType.RESTORE)
    logger.info("Message verified cvsa.v1.CVSARequestedEvent for restore")


def verify_restore_created_event(
    kafka,
    instance_details=CloudInstanceDetails.R6I_LARGE,
    restore_streams=8,
    cloud_region: AwsRegions = AWS_REGION_1_ENUM,
    event_filters: Union[list[EventFilter], None] = None,
    cloud_provider: CloudProvider = CloudProvider.AWS,
):
    event_type = "cvsa.v1.CVSACreatedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, region: {cloud_region}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id} for restore"
    )
    message = wait_for_event(
        kafka,
        event_type,
        cloud_region=cloud_region,
        timeout=Timeout.STARTED_EVENT.value,
        event_filters=event_filters,
    )
    logger.info(f"Message found cvsa.v1.CVSACreatedEvent for restore: {message}")
    cvsa_model = CvsaEvent.from_message(message)
    kafka.cvsa_id = cvsa_model.cvsa_id
    verify_restore_message_data(cvsa_model, instance_details, restore_streams)
    assert cvsa_model.cloud_provider == str(cloud_provider), f"{cvsa_model.cloud_provider} != {str(cloud_provider)}"
    assert cvsa_model.cloud_region == str(cloud_region)
    assert cvsa_model.protected_data.data_protected_bytes is 0
    assert cvsa_model.protected_data.protected_asset_type == str(ProtectedAssetType.AWS_EBS)
    logger.info("Message verified cvsa.v1.CVSACreatedEvent for restore")
    return cvsa_model


def verify_restore_ready_event(
    kafka,
    instance_details=CloudInstanceDetails.R6I_LARGE,
    restore_streams=8,
    cloud_region: AwsRegions = AWS_REGION_1_ENUM,
    cloud_provider: CloudProvider = CloudProvider.AWS,
):
    event_type = "cvsa.v1.CVSAReadyEvent"
    logger.info(
        f"Searching for message: event: {event_type}, region: {cloud_region}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}, correlation id: {kafka.correlation_id} for restore"
    )
    message = wait_for_event(
        kafka,
        event_type,
        cvsa_id=kafka.cvsa_id,
        timeout=Timeout.READY_EVENT.value,
        event_filters=[event_filter_correlation_id(kafka.correlation_id)],
    )
    logger.info(f"Message found cvsa.v1.CVSAReadyEvent for restore: {message}")
    cvsa_model = CvsaEvent.from_message(message)
    kafka.cvsa_id = cvsa_model.cvsa_id
    verify_restore_message_data(cvsa_model, instance_details, restore_streams)
    assert cvsa_model.catalyst_store, "catalyst_store is empty"
    assert cvsa_model.correlation_id == kafka.correlation_id.decode(
        "utf-8"
    ), f"invalid correlation_id; got: {cvsa_model.correlation_id}, want: {kafka.correlation_id}"
    assert message.value["cloudProvider"] == str(cloud_provider)
    assert message.value["cloudRegion"] == str(cloud_region)
    assert cvsa_model.cvsa_id == kafka.cvsa_id, f"invalid cvsa_id; got {cvsa_model.cvsa_id}, want: {kafka.cvsa_id}"
    return cvsa_model
