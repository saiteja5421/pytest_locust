import logging
from typing import Union, Optional

from assertpy import assert_that
from pytest_check import check

import lib.platform.kafka.protobuf.cvsa_manager.cvsa_manager_pb2 as cvsa_manager_pb2
from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import (
    RequestFinishedStatus,
    RequestType,
    AwsRegions,
    StopReason,
    TerminateReason,
    CloudProvider,
    ProtectedAssetType,
    CloudVolumeType,
    CloudRegions,
)
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_allowed_instances import is_allowed, get_instance_details_by_name
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_models import CvsaEvent
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.cloud.cloud_dataclasses import CloudImage
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.eventfilters import EventFilter
from lib.platform.kafka.eventfilters.cvsamanager import (
    event_filter_correlation_id,
    event_filter_stop_reason,
    event_filter_terminate_reason,
    event_filter_cloud_instance_id,
)
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import AWS_REGION_1_ENUM
from tests.steps.aws_protection.cvsa.assertions import assert_volume_bytes_size
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
    send_backup_requested_event_ms365,
    verify_backup_requested_event_ms365,
)
from tests.steps.aws_protection.cvsa.cloud_steps import (
    verify_instance_type_and_volume_size,
    get_default_region,
    get_default_instance,
)
from tests.steps.aws_protection.cvsa.cloud_steps import (
    verify_not_deployed_cvsa,
    verify_deployed_cvsa,
)
from tests.steps.aws_protection.cvsa.kafka_steps import (
    get_latest_event,
    wait_for_event,
)
from tests.steps.aws_protection.cvsa.logging_steps import set_logged_cvsa_id
from utils.size_conversion import gb_to_bytes

logger = logging.getLogger()


def send_requested_event(
    kafka_manager: KafkaManager,
    data_protected_gb=0,
    data_protected_previous_gb=0,
    headers: dict = None,
    request_type: RequestType = RequestType.BACKUP,
    cloud_region: AwsRegions = AWS_REGION_1_ENUM,
    ami=None,
    update_offsets=True,
    data_protected_previous_changed_gb=0,
    data_protected_recovered_gb: int = 0,
    target_duration_seconds=None,
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
    if ami is not None:
        headers["ce_forcedcvsaimageid"] = bytes(ami, "utf-8")
    requested_event = cvsa_manager_pb2.CVSARequestedEvent()
    requested_event.correlation_id = kafka_manager.correlation_id.decode("utf-8")
    requested_event.csp_account_id = kafka_manager.csp_account_id.decode("utf-8")
    requested_event.cam_account_id = kafka_manager.cam_account_id.decode("utf-8")
    requested_event.data_protected_new_bytes = gb_to_bytes(data_protected_gb)
    requested_event.data_protected_previous_bytes = gb_to_bytes(data_protected_previous_gb)
    requested_event.data_protected_previous_changed_bytes = gb_to_bytes(data_protected_previous_changed_gb)
    requested_event.data_protected_recovered_bytes = gb_to_bytes(data_protected_recovered_gb)
    requested_event.request_type = request_type.value
    requested_event.cloud_provider = cvsa_manager_pb2.CLOUD_PROVIDER_ENUM_AWS
    requested_event.cloud_region = cloud_region.value
    requested_event.protected_asset_type = cvsa_manager_pb2.PROTECTED_ASSET_TYPE_ENUM_AWS_EBS
    if target_duration_seconds:
        requested_event.target_duration_seconds = target_duration_seconds
    uint64_fields = [
        "dataProtectedNewBytes",
        "dataProtectedPreviousBytes",
        "dataProtectedPreviousChangedBytes",
        "dataProtectedRecoveredBytes",
        "targetDurationSeconds",
    ]
    logger.info(f"Send message: cvsa.v1.CVSARequestedEvent, customer_id: {kafka_manager.account_id}")
    kafka_manager.send_message(requested_event, headers, uint64_fields, update_offsets=update_offsets)


def send_finished_event(
    kafka_manager: KafkaManager,
    headers: dict = None,
    cloud_region: CloudRegions = None,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    if not headers:
        headers = {
            "ce_id": kafka_manager.account_id,
            "ce_type": b"cvsa.v1.CVSARequestFinishedEvent",
            "ce_partitionkey": kafka_manager.account_id,
            "ce_customerid": kafka_manager.account_id,
        }
    finished_event = cvsa_manager_pb2.CVSARequestFinishedEvent()
    finished_event.cloud_provider = cloud_provider.value
    finished_event.cloud_region = cloud_region.value
    finished_event.protected_asset_type = cvsa_manager_pb2.PROTECTED_ASSET_TYPE_ENUM_AWS_EBS
    finished_event.result = 1
    finished_event.cam_account_id = kafka_manager.cam_account_id.decode("utf-8")
    finished_event.csp_account_id = kafka_manager.csp_account_id.decode("utf-8")
    finished_event.correlation_id = kafka_manager.correlation_id.decode("utf-8")
    logger.info(f"Send message: cvsa.v1.CVSARequestFinishedEvent, customer_id: {kafka_manager.account_id}")
    kafka_manager.send_message(finished_event, headers)


def verify_finished_event(
    kafka: KafkaManager,
    cloud_region: CloudRegions = None,
    result=RequestFinishedStatus.STATUS_OK,
    error_msg=None,
    timeout=None,
    event_filters=None,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    if event_filters is None:
        event_filters = [event_filter_correlation_id(kafka.correlation_id)]

    event_type = "cvsa.v1.CVSARequestFinishedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, region:{cloud_region}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    message = wait_for_event(
        kafka,
        event_type,
        cloud_region=cloud_region,
        timeout=Timeout.REQUEST_FINISHED_EVENT.value if not timeout else timeout,
        event_filters=event_filters,
    )
    logger.info(f"Message found cvsa.v1.CVSARequestFinishedEvent: {message}")
    assert message.value["cloudProvider"] == str(cloud_provider)
    assert message.value["cloudRegion"] == str(cloud_region)
    assert message.value["result"] == result.name
    if result == RequestFinishedStatus.STATUS_OK and cloud_provider == CloudProvider.AWS:
        assert message.value["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)  # todo: check for Azure
    elif result != RequestFinishedStatus.STATUS_OK and cloud_provider == CloudProvider.AWS:
        assert error_msg in message.value["errorMsg"]
    assert message.value["camAccountId"] == kafka.cam_account_id.decode("utf-8")
    assert message.value["cspAccountId"] == kafka.csp_account_id.decode("utf-8")
    assert message.value["correlationId"] == kafka.correlation_id.decode("utf-8")
    logger.info("Message verified cvsa.v1.CVSARequestFinishedEvent")


def verify_requested_event(
    kafka: KafkaManager,
    data_protected_gb=0,
    data_protected_previous_gb=0,
    request_type: RequestType = RequestType.BACKUP,
    cloud_region: CloudRegions = None,
    ami=None,
    data_protected_previous_changed_gb=0,
    data_protected_recovered_gb=0,
    target_duration_seconds=None,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    event_type = "cvsa.v1.CVSARequestedEvent"
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
    logger.info(f"Message found cvsa.v1.CVSARequestedEvent: {message}")
    if ami is not None:
        headers = dict(map(lambda x: (x[0], x[1]), message.headers))
        assert headers["ce_forcedcvsaimageid"] == bytes(ami, "utf-8")
    assert message.value["cloudProvider"] == str(cloud_provider)
    assert message.value["cloudRegion"] == str(cloud_region)
    if cloud_provider == CloudProvider.AWS:
        assert message.value["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)  # todo: check for Azure
    if data_protected_previous_gb:
        assert message.value["dataProtectedPreviousBytes"] == gb_to_bytes(data_protected_previous_gb)
    if data_protected_previous_changed_gb:
        assert message.value["dataProtectedPreviousChangedBytes"] == gb_to_bytes(data_protected_previous_changed_gb)
    if request_type == RequestType.BACKUP:
        assert message.value["dataProtectedNewBytes"] == gb_to_bytes(data_protected_gb)
    if request_type == RequestType.RESTORE and data_protected_recovered_gb:
        assert message.value["dataProtectedRecoveredBytes"] == gb_to_bytes(data_protected_recovered_gb)
    if target_duration_seconds:
        assert message.value["targetDurationSeconds"] == target_duration_seconds
    assert message.value["camAccountId"] == kafka.cam_account_id.decode("utf-8")
    assert message.value["cspAccountId"] == kafka.csp_account_id.decode("utf-8")
    assert message.value["correlationId"] == kafka.correlation_id.decode("utf-8")
    assert message.value["requestType"] == str(request_type)
    logger.info("Message verified cvsa.v1.CVSARequestedEvent")


def verify_started_event(kafka, timeout=None, event_filters: Union[list[EventFilter], None] = None):
    event_type = "cvsa.v1.CVSAStartedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, cvsa_id: {kafka.cvsa_id}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    message = wait_for_event(
        kafka,
        event_type,
        cvsa_id=kafka.cvsa_id,
        timeout=Timeout.STARTED_EVENT.value if not timeout else timeout,
        event_filters=event_filters,
    )
    logger.info(f"Message found cvsa.v1.CVSAStartedEvent: {message}")
    assert message.value["cvsaId"] == kafka.cvsa_id
    logger.info("Message verified cvsa.v1.CVSAStartedEvent")


def verify_stopped_event(kafka, reason: StopReason = StopReason.RESIZE):
    event_type = "cvsa.v1.CVSAStoppedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, cvsa_id: {kafka.cvsa_id}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    timeout = Timeout.STOPPED_EVENT.value
    if reason == StopReason.IDLE:
        timeout = Timeout.STOPPED_EVENT_IDLE.value
    elif reason == StopReason.ORPHANED:
        timeout = Timeout.STOPPED_EVENT_ORPHANED.value
    message = wait_for_event(
        kafka, event_type, cvsa_id=kafka.cvsa_id, timeout=timeout, event_filters=[event_filter_stop_reason(reason)]
    )
    logger.info(f"Message found cvsa.v1.CVSAStoppedEvent: {message}")
    assert message.value["reason"] == str(
        reason
    ), f"Reason message: {message.value['reason']}, Reason expected: {reason}"
    if kafka.cvsa_id is not None:
        assert (
            message.value["cvsaId"] == kafka.cvsa_id
        ), f"cvsa_id msg: {message.value['cvsaId']}, cvsa_id expected: {kafka.cvsa_id}"
    logger.info("Message verified cvsa.v1.CVSAStoppedEvent")


def verify_terminated_event(kafka: KafkaManager, reason: TerminateReason, cloud_instance_id=None):
    event_type = "cvsa.v1.CVSATerminatedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, cvsa_id: {kafka.cvsa_id}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    timeout = Timeout.TERMINATED_EVENT.value
    event_filters = [event_filter_terminate_reason(reason)]
    if cloud_instance_id:
        event_filters += [event_filter_cloud_instance_id(cloud_instance_id)]
    message = wait_for_event(kafka, event_type, cvsa_id=kafka.cvsa_id, timeout=timeout, event_filters=event_filters)
    logger.info(f"Message found cvsa.v1.CVSATerminatedEvent: {message}")
    assert message.value["reason"] == str(
        reason
    ), f"Reason message: {message.value['reason']}, Reason expected: {reason}"
    assert (
        message.value["cvsaId"] == kafka.cvsa_id
    ), f"cvsa_id msg: {message.value['cvsaId']}, cvsa_id expected: {kafka.cvsa_id}"
    logger.info("Message verified cvsa.v1.CVSATerminatedEvent")


def verify_no_event(kafka: KafkaManager, event_type):
    logger.info(
        f"Searching that message is not in topic: {event_type}, cvsa_id: {kafka.cvsa_id}, \
        from offset: {kafka.get_offsets()}, customer id: {kafka.account_id}"
    )
    event = get_latest_event(kafka, event_type, cvsa_id=kafka.cvsa_id)
    if event:
        raise AssertionError(f"Kafka event {event_type} was found in topic - should not be present.")
    logger.info(f"Message event {event_type} should not be present - Success")
    return True


def verify_resize_event(
    kafka,
    data_protected_gb,
    instance_details=CloudInstanceDetails.R6I_LARGE,
    backup_streams=8,
    volume_size_bytes=50_000_000_000,
    strict_instance_details=False,
    restore_streams: Optional[int] = None,
    cloud_provider: CloudProvider = CloudProvider.AWS,
):
    instance_details: CloudInstanceDetails = instance_details.value
    event_type = "cvsa.v1.CVSAResizedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, cvsa_id: {kafka.cvsa_id}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    message = wait_for_event(kafka, event_type, cvsa_id=kafka.cvsa_id, timeout=Timeout.RESIZED_EVENT.value)
    logger.info(f"Message found cvsa.v1.CVSAResizedEvent: {message}")
    with check:
        if message.value["to"]["computeType"] == instance_details.instance_type or strict_instance_details:
            assert message.value["to"]["computeType"] == instance_details.instance_type
            assert message.value["to"]["cpu"] == instance_details.cpu
            assert message.value["to"]["ram"] == instance_details.ram
        else:
            given_instance = get_instance_details_by_name(message.value["to"]["computeType"])
            is_allowed_bool = is_allowed(instance_details, given_instance)
            is_allowed_desc = f"Instance is oversized, wanted: {instance_details}, given: {given_instance}"
            assert_that(is_allowed_bool, is_allowed_desc).is_true()
            assert message.value["to"]["computeType"] == given_instance.value.instance_type
            assert message.value["to"]["cpu"] == given_instance.value.cpu
            assert message.value["to"]["ram"] == given_instance.value.ram
        message_size_bytes_int = int(message.value["to"]["dataVolume"]["sizeBytes"])
        assert_volume_bytes_size(message_size_bytes_int, int(volume_size_bytes))
        if cloud_provider == CloudProvider.AWS:
            assert message.value["to"]["dataVolume"]["type"] == str(CloudVolumeType.AWS_GP3)
            assert message.value["protectedData"]["protectedAssetType"] == str(ProtectedAssetType.AWS_EBS)
        else:
            assert message.value["to"]["dataVolume"]["type"] == str(CloudVolumeType.AZURE_PREMIUMSSD)
        message_backup_streams = message.value["to"]["backupStreams"]
        assert_that(message_backup_streams, f"backup_streams: {instance_details}").is_equal_to(backup_streams)
        if restore_streams:
            assert message.value["to"]["restoreStreams"] == restore_streams
        assert message.value["protectedData"]["backupWindowHours"] == 8
        data_prot_gb = message.value["protectedData"]["dataProtectedBytes"]
        assert_that(int(data_prot_gb), f"data_protected:{instance_details}").is_equal_to(gb_to_bytes(data_protected_gb))
        kafka.cvsa_id = message.value["cvsaId"]
    logger.info("Message verified  cvsa.v1.CVSAResizedEvent")


def verify_created_event(
    kafka,
    verify_protected_asset=True,
    instance_details: CloudInstanceDetails = None,
    backup_streams: Optional[int] = 8,
    volume_size_bytes=50_000_000_000,
    cloud_region: CloudRegions = None,
    strict_instance_details=False,
    restore_streams: Optional[int] = None,
    cloud_provider=CloudProvider.AWS,
):
    if instance_details is None:
        instance_details = get_default_instance(cloud_provider=cloud_provider)
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    event_type = "cvsa.v1.CVSACreatedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, region: {cloud_region}, from offset: {kafka.get_offsets()}, \
                  customer id: {kafka.account_id}"
    )
    message = wait_for_event(kafka, event_type, cloud_region=cloud_region, timeout=Timeout.STARTED_EVENT.value)
    logger.info(f"Message found cvsa.v1.CVSACreatedEvent: {message}")
    cvsa_model = CvsaEvent.from_message(message)
    kafka.cvsa_id = cvsa_model.cvsa_id
    set_logged_cvsa_id(kafka)
    verify_message_data(
        cvsa_model=cvsa_model,
        instance_details=instance_details,
        backup_streams=backup_streams,
        volume_size_bytes=volume_size_bytes,
        strict_instance_details=strict_instance_details,
        restore_streams=restore_streams,
        cloud_provider=cloud_provider,
    )
    assert cvsa_model.cloud_provider == str(cloud_provider)
    assert cvsa_model.cloud_region == str(cloud_region)
    if verify_protected_asset is not None:
        assert int(cvsa_model.protected_data.backup_window_hours) == 8
        if cloud_provider == CloudProvider.AWS:
            assert cvsa_model.protected_data.protected_asset_type == str(ProtectedAssetType.AWS_EBS)
    logger.info("Message verified cvsa.v1.CVSACreatedEvent")
    return cvsa_model


def verify_created_event_backup(
    kafka,
    verify_protected_asset=True,
    instance_details: CloudInstanceDetails = None,
    backup_streams: Optional[int] = 8,
    volume_size_bytes=50_000_000_000,
    cloud_region: CloudRegions = None,
    strict_instance_details=False,
    restore_streams: Optional[int] = None,
    data_protected_gb=0,
    cloud_provider=CloudProvider.AWS,
):
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    if instance_details is None:
        instance_details = get_default_instance(cloud_provider=cloud_provider)

    cvsa_model = verify_created_event(
        kafka,
        verify_protected_asset=verify_protected_asset,
        instance_details=instance_details,
        backup_streams=backup_streams,
        volume_size_bytes=volume_size_bytes,
        cloud_region=cloud_region,
        strict_instance_details=strict_instance_details,
        restore_streams=restore_streams,
        cloud_provider=cloud_provider,
    )
    dpb = 0 if not cvsa_model.protected_data.data_protected_bytes else cvsa_model.protected_data.data_protected_bytes
    db_bytes_int_actual = int(dpb)
    db_bytes_int_expected = gb_to_bytes(data_protected_gb)
    assert db_bytes_int_actual == db_bytes_int_expected, f"{db_bytes_int_actual} != {db_bytes_int_expected}"
    return cvsa_model


def verify_ready_event(
    kafka,
    instance_details: CloudInstanceDetails = None,
    backup_streams: Optional[int] = 8,
    volume_size_bytes=50_000_000_000,
    cloud_region: CloudRegions = None,
    strict_instance_details=False,
    restore_streams: Optional[int] = None,
    cloud_provider=CloudProvider.AWS,
):
    if instance_details is None:
        instance_details = get_default_instance(cloud_provider=cloud_provider)
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_provider)
    event_type = "cvsa.v1.CVSAReadyEvent"
    message = wait_for_event(
        kafka,
        event_type,
        cvsa_id=kafka.cvsa_id,
        timeout=Timeout.READY_EVENT.value,
        event_filters=[event_filter_correlation_id(kafka.correlation_id)],
    )
    logger.info(message)
    cvsa_model = CvsaEvent.from_message(message)
    verify_message_data(
        cvsa_model=cvsa_model,
        instance_details=instance_details,
        backup_streams=backup_streams,
        volume_size_bytes=volume_size_bytes,
        strict_instance_details=strict_instance_details,
        restore_streams=restore_streams,
        cloud_provider=cloud_provider,
    )
    assert cvsa_model.catalyst_store, "catalyst_store is empty"
    assert cvsa_model.correlation_id == kafka.correlation_id.decode(
        "utf-8"
    ), f"invalid correlation_id; got: {cvsa_model.correlation_id}, want: {kafka.correlation_id}"
    assert message.value["cloudProvider"] == str(cloud_provider)
    assert message.value["cloudRegion"] == str(cloud_region)
    assert cvsa_model.cvsa_id == kafka.cvsa_id, f"invalid cvsa_id; got {cvsa_model.cvsa_id}, want: {kafka.cvsa_id}"
    assert cvsa_model.cam_account_id == kafka.cam_account_id.decode("utf-8")
    return cvsa_model


def verify_message_data(
    cvsa_model,
    instance_details: CloudInstanceDetails = None,
    backup_streams: Optional[int] = 8,
    volume_size_bytes=50_000_000_000,
    strict_instance_details=False,
    restore_streams: Optional[int] = None,
    cloud_provider=CloudProvider.AWS,
):
    if instance_details is None:
        instance_details = get_default_instance(cloud_provider=cloud_provider)

    instance_details_value = instance_details.value
    assert cvsa_model.address
    cloud_resources = cvsa_model.cloud_resources
    with check:
        if cloud_resources.compute_type == instance_details_value.instance_type or strict_instance_details:
            assert (
                cloud_resources.compute_type == instance_details_value.instance_type
            ), f"{cloud_resources.compute_type} == {instance_details_value.instance_type}"
            assert cloud_resources.cpu == instance_details_value.cpu, f"{cloud_resources} != {instance_details_value}"
            assert cloud_resources.ram == instance_details_value.ram
            logger.info(f"Ec2 type correctly sized, wanted: {instance_details_value}, given: {cloud_resources}")
        else:
            logger.error(
                f"Given instance type not match requested instance type. Given: {cloud_resources},"
                f" Requested: {instance_details_value}"
            )
            given_instance = get_instance_details_by_name(cloud_resources.compute_type)
            assert is_allowed(
                instance_details, given_instance
            ), f"Instance is oversized, wanted: {instance_details}, given: {given_instance}"
            assert cloud_resources.compute_type == given_instance.value.instance_type
            assert cloud_resources.cpu == given_instance.value.cpu
            assert cloud_resources.ram == given_instance.value.ram
        if backup_streams:
            assert_that(cloud_resources.backup_streams, f"backup_streams in {cloud_resources}").is_equal_to(
                backup_streams
            )
        if restore_streams:
            assert_that(cloud_resources.restore_streams, f"restore_streams in {cloud_resources}").is_equal_to(
                restore_streams
            )
        if volume_size_bytes:
            assert_volume_bytes_size(int(cloud_resources.data_volume.size_bytes), volume_size_bytes)
        if cloud_provider == CloudProvider.AWS:
            assert cloud_resources.data_volume.type == str(CloudVolumeType.AWS_GP3)
        elif cloud_provider == CloudProvider.AZURE:
            assert cloud_resources.data_volume.type == str(
                CloudVolumeType.AZURE_PREMIUMSSD
            ), cloud_resources.data_volume


def create_new_cvsa_instance_and_validate(
    kafka_mgr: KafkaManager,
    cloud_vm_mgr: CloudVmManager,
    data_protected_gb: int,
    instance_details: CloudInstanceDetails = None,
    backup_streams=8,
    volume_size_bytes=50_000_000_000,
    cloud_region: CloudRegions = None,
    ami: CloudImage = None,
    headers: dict = None,
    target_duration_seconds=None,
    strict_instance_details=False,
    verify_not_deployed=True,
):
    if not instance_details:
        instance_details = get_default_instance(cloud_provider=cloud_vm_mgr.name())
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_vm_mgr.name())
    if verify_not_deployed:
        verify_not_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, account_id=kafka_mgr.account_id)
    ami_id = ami.id if ami else None
    send_backup_requested_event(
        kafka_mgr,
        data_protected_gb=data_protected_gb,
        ami=ami_id,
        headers=headers,
        cloud_region=cloud_region,
        target_duration_seconds=target_duration_seconds,
        cloud_provider=cloud_vm_mgr.name(),
    )
    verify_backup_requested_event(
        kafka_mgr,
        data_protected_gb=data_protected_gb,
        cloud_region=cloud_region,
        ami=ami_id,
        target_duration_seconds=target_duration_seconds,
        cloud_provider=cloud_vm_mgr.name(),
    )
    verify_created_event_backup(
        kafka_mgr,
        instance_details=instance_details,
        backup_streams=backup_streams,
        volume_size_bytes=volume_size_bytes,
        cloud_region=cloud_region,
        strict_instance_details=strict_instance_details,
        data_protected_gb=data_protected_gb,
        cloud_provider=cloud_vm_mgr.name(),
    )
    verify_started_event(kafka_mgr)
    cvsa_model = verify_ready_event(
        kafka_mgr,
        instance_details=instance_details,
        backup_streams=backup_streams,
        volume_size_bytes=volume_size_bytes,
        cloud_region=cloud_region,
        strict_instance_details=strict_instance_details,
        cloud_provider=cloud_vm_mgr.name(),
    )
    ami_version = ami.version if ami else None
    verify_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka_mgr.cvsa_id, ami_version=ami_version)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=cloud_vm_mgr,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=instance_details,
        volume_size_bytes=volume_size_bytes,
        strict_instance_details=strict_instance_details,
    )
    return cvsa_model


def create_new_ms365_cvsa_instance_and_validate(
    kafka_mgr: KafkaManager,
    cloud_vm_mgr: CloudVmManager,
    data_protected_gb: int = 0,
    volume_size_bytes: int = None,
    instance_details: CloudInstanceDetails = None,
    cloud_region: CloudRegions = None,
):
    if not instance_details:
        instance_details = get_default_instance(cloud_provider=cloud_vm_mgr.name())
    if not cloud_region:
        cloud_region = get_default_region(cloud_provider=cloud_vm_mgr.name())
    send_backup_requested_event_ms365(
        kafka_mgr,
        data_protected_gb=data_protected_gb,
        cloud_provider=cloud_vm_mgr.name(),
        cloud_region=cloud_region,
    )
    verify_backup_requested_event_ms365(
        kafka_mgr,
        data_protected_gb=data_protected_gb,
        cloud_provider=cloud_vm_mgr.name(),
        cloud_region=cloud_region,
    )
    verify_created_event_backup(
        kafka_mgr,
        cloud_provider=cloud_vm_mgr.name(),
        instance_details=instance_details,
        volume_size_bytes=volume_size_bytes,
        cloud_region=cloud_region,
        data_protected_gb=data_protected_gb,
    )
    verify_ready_event(
        kafka_mgr,
        cloud_provider=cloud_vm_mgr.name(),
        instance_details=instance_details,
        volume_size_bytes=volume_size_bytes,
        cloud_region=cloud_region,
    )
    verify_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka_mgr.cvsa_id)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=cloud_vm_mgr,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=instance_details,
        volume_size_bytes=volume_size_bytes,
    )
    send_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
    verify_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())


def send_cvsa_stopped_event(kafka_manager: KafkaManager, cvsa_id: str):
    headers = {
        "ce_id": kafka_manager.account_id,
        "ce_type": b"cvsa.v1.CVSAStoppedEvent",
        "ce_partitionkey": kafka_manager.account_id,
        "ce_customerid": kafka_manager.account_id,
    }
    cvsa_stopped_event = cvsa_manager_pb2.CVSAStoppedEvent()
    cvsa_stopped_event.cvsa_id = cvsa_id
    logger.info(f"Send message: cvsa.v1.CVSAStoppedEvent, customer_id: {kafka_manager.account_id}")
    kafka_manager.send_message(cvsa_stopped_event, headers)
