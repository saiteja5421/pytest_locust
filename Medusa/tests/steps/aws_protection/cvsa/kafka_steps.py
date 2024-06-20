import json
import logging
from typing import List, Union

from kafka.protocol.message import Message as KafkaMessage
from waiting import TimeoutExpired, wait

from lib.common.enums.cvsa import (
    VaultCredentialType,
    MaintenanceAction,
    MaintenanceOperation,
    CloudRegions,
    CloudProvider,
)
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_models import ProtectionStoreDelete
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_models import ProtectionStoreUtilizationUpdate
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.eventfilters import EventFilter, event_filters_reduce
from lib.platform.kafka.eventfilters.cvsamanager import (
    event_filter_type,
    event_filter_cloud_region,
    event_filter_cvsa_id,
    event_filter_csp_cam_id,
    event_filter_maintenance_action,
    event_filter_maintenance_operation_type,
    event_filter_catalyst_gateway_id,
)
from lib.platform.kafka.kafka_manager import KafkaManager
from lib.platform.storeonce.storeonce import StoreOnce
from tests.steps.aws_protection.cvsa.cloud_steps import get_storeonce_ip
from tests.steps.aws_protection.cvsa.vault_steps import get_cvsa_credentials

logger = logging.getLogger()


def get_latest_events(
    kafka_manager: KafkaManager,
    event_type,
    cloud_region: CloudRegions = None,
    cvsa_id=None,
    csp_cam_id=None,
    event_filters: List[EventFilter] = None,
):
    if not event_filters:
        event_filters = []
    event_filters.insert(0, event_filter_type(event_type))
    if cvsa_id:
        event_filters.append(event_filter_cvsa_id(cvsa_id))
    if csp_cam_id:
        event_filters.append(event_filter_csp_cam_id(csp_cam_id))
    if cloud_region:
        event_filters.append(event_filter_cloud_region(cloud_region))
    messages = kafka_manager.read_messages(from_offset=kafka_manager.get_offsets())
    return event_filters_reduce(event_filters, messages)


def get_latest_event(
    kafka_manager: KafkaManager,
    event_type,
    cloud_region: CloudRegions = None,
    cvsa_id=None,
    csp_cam_id=None,
    event_filters: List[EventFilter] = None,
) -> Union[KafkaMessage, bool]:
    try:
        messages_filtered = get_latest_events(
            kafka_manager, event_type, cloud_region, cvsa_id, csp_cam_id, event_filters
        )
        # TODO: Rethink our approach for selecting the event to compare.
        #   There should be only one logic for choosing the proper message.
        if len(messages_filtered) > 0:
            return messages_filtered[0]
    except AttributeError:
        pass
    logger.info(
        f"Event not found: {event_type}, from offset: {kafka_manager.get_offsets()}, \
                            customer id: {kafka_manager.account_id}, region: {cloud_region}, cvsa_id:{cvsa_id}"
    )
    return False


def wait_for_event(
    kafka_manager: KafkaManager,
    event_type,
    cloud_region: CloudRegions = None,
    cvsa_id=None,
    csp_cam_id=None,
    timeout=1800,
    interval=30,
    event_filters=None,
):
    try:
        message = wait(
            lambda: get_latest_event(kafka_manager, event_type, cloud_region, cvsa_id, csp_cam_id, event_filters),
            timeout_seconds=timeout,
            sleep_seconds=interval,
        )
        logger.info(f"Message {event_type} found: {message}")
        kafka_manager.set_offset_at_event(message)
        return message
    except TimeoutExpired:
        for msg in kafka_manager.consumer:
            logger.error(f"Kafka messages on topic: {msg}")
        raise AssertionError(f"Kafka event {event_type} was not found in topic after {timeout} seconds.")


def wait_for_event_not_emitted(
    kafka_manager: KafkaManager,
    event_type,
    cloud_region: CloudRegions = None,
    cvsa_id=0,
    csp_cam_id=None,
    timeout=900,
    interval=30,
):
    try:
        logger.info(f"Verifying that {event_type} is not emitted for {timeout} seconds.")
        messages = wait(
            lambda: get_latest_event(kafka_manager, event_type, cloud_region, cvsa_id, csp_cam_id),
            timeout_seconds=timeout,
            sleep_seconds=interval,
        )
        logger.error(f"Message {event_type} found: {messages}")
        raise AssertionError(f"Kafka event {event_type} was found in topic after {timeout} seconds.")
    except TimeoutExpired:
        logger.info(f"Kafka event {event_type} was not emitted in topic after {timeout} seconds.")


def verify_deleted_event(
    cvsa_kafka: KafkaManager,
    reports_kafka: KafkaManager,
    cloud_store_id: str,
    cloud_store_name: str,
    cloud_provider: CloudProvider,
):
    event_type = "cloud.catalyst.gateway.store.deleted"
    logger.info(
        f"Searching for message: event: {event_type}. "
        f"from offset: {reports_kafka.get_offsets()}, cam account id: {cvsa_kafka.cam_account_id}"
    )
    message = wait_for_event(
        kafka_manager=reports_kafka, event_type=event_type, timeout=Timeout.STORE_DELETED_EVENT.value
    )
    response = ProtectionStoreDelete.from_dict(json.loads(message.value))
    assert response.app_type.upper() == cloud_provider.name
    assert response.account_id == cvsa_kafka.cam_account_id.decode("utf-8")
    assert response.csp_id == cvsa_kafka.csp_account_id.decode("utf-8")
    assert response.catalyst_gateway_id == cvsa_kafka.cvsa_id
    assert response.cloud_store_id == cloud_store_id
    assert response.cloud_store_name == cloud_store_name
    logger.info("Message verified Deleted Event")


def verify_billing_event(
    cvsa_kafka: KafkaManager,
    billing_kafka: KafkaManager,
    cloud_vm_mgr: CloudVmManager,
    region: str,
    cloud_store_name: str,
    amount=0,
):
    def _verify_amount(m, a):
        if len(m) > a:
            return m

    event_type = "cloud.catalyst.gateway.utilization.update"
    logger.info(f"Searching for event Billing Event {event_type},")
    messages = wait(
        lambda: _verify_amount(get_latest_events(billing_kafka, event_type), amount),
        timeout_seconds=900,
        sleep_seconds=10,
    )
    storeonce_ip = get_storeonce_ip(cloud_vm_mgr, cvsa_kafka.cvsa_id)
    credential = get_cvsa_credentials(cvsa_id=cvsa_kafka.cvsa_id, credential_type=VaultCredentialType.ADMIN)
    response = ProtectionStoreUtilizationUpdate.from_dict(json.loads(messages[-1].value)[0])
    storeonce = StoreOnce(host=storeonce_ip, username=credential.username, password=credential.password)
    cloud_store = storeonce.get_cloud_store()
    assert len(response.cloud_stores) == 1
    assert response.account_id == cvsa_kafka.cam_account_id.decode("UTF-8")
    assert response.csp_id == cvsa_kafka.csp_account_id.decode("UTF-8")
    assert response.app_type == "AWS"
    assert response.cloud_stores[0].cloud_store_id == cloud_store.cloud_store_details.cloud_store_id
    assert response.cloud_stores[0].cloud_store_name == cloud_store_name
    assert response.catalyst_gateway_id == cvsa_kafka.cvsa_id
    assert response.catalyst_gateway_name == cvsa_kafka.cvsa_id
    assert response.cloud_stores[0].region == region
    assert (
        response.cloud_stores[0].cloud_user_bytes == cloud_store.user_bytes
    ), f"{response.cloud_stores[0].cloud_user_bytes} != {cloud_store.user_bytes}"
    assert (
        response.cloud_stores[0].cloud_disk_bytes == cloud_store.cloud_store_details.cloud_disk_bytes
    ), f"{response.cloud_stores[0].cloud_disk_bytes} != {cloud_store.cloud_store_details.cloud_disk_bytes}"
    logger.info("Message verified Billing Event")
    return len(messages)


def verify_no_store_report_event_is_emitted(kafka_mgr: KafkaManager, event_type: str, cvsa_id: str):
    timeout_seconds = 180
    try:
        logger.info(f"Verifying that {event_type} event is not emitted for {timeout_seconds} seconds.")
        messages = wait(
            lambda: get_latest_event(
                kafka_mgr,
                event_type,
                event_filters=[event_filter_catalyst_gateway_id(cvsa_id)],
            ),
            timeout_seconds=timeout_seconds,
            sleep_seconds=30,
        )
        logger.error(f"Message {event_type} found: {messages}")
        raise AssertionError(f"Event {event_type} was found in topic.")
    except TimeoutExpired:
        logger.info(f"Event {event_type} was not emitted in topic after {timeout_seconds} seconds.")


def verify_no_billing_event_is_emitted(kafka_mgr: KafkaManager, cvsa_id: str):
    return verify_no_store_report_event_is_emitted(
        kafka_mgr,
        "cloud.catalyst.gateway.utilization.update",
        cvsa_id,
    )


def verify_billing_events_are_emitted(kafka_mgr: KafkaManager, cvsa_id: str, number_of_events: int):
    def _verify_amount(m, a):
        if len(m) >= a:
            return m

    timeout_seconds = 180
    event_type = "cloud.catalyst.gateway.utilization.update"
    logger.info(f"Searching for event Billing Event {event_type},")

    messages = wait(
        lambda: _verify_amount(
            get_latest_events(
                kafka_mgr,
                event_type,
                event_filters=[event_filter_catalyst_gateway_id(cvsa_id)],
            ),
            number_of_events,
        ),
        timeout_seconds=timeout_seconds,
        sleep_seconds=30,
    )
    logger.info(f"Messages {event_type} found: {messages}, number of messages={len(messages)}")


def verify_no_store_deleted_event_is_emitted(kafka_mgr: KafkaManager, cvsa_id: str):
    return verify_no_store_report_event_is_emitted(
        kafka_mgr,
        "cloud.catalyst.gateway.store.deleted",
        cvsa_id,
    )


def verify_no_maintenance_event(kafka: KafkaManager, timeout: int = 900):
    event_type = "cvsa.v1.CVSAMaintenanceEvent"
    logger.info(f"Verifying that {event_type} is not emitted.")
    wait_for_event_not_emitted(kafka, event_type, timeout=timeout)


def verify_maintenance_event(kafka_mgr: KafkaManager, action: MaintenanceAction, operation_type: MaintenanceOperation):
    event_type = "cvsa.v1.CVSAMaintenanceEvent"
    logger.info(
        f"Searching for message: event: {event_type}, action: {action}, operation: {operation_type}, "
        + f"from offset: {kafka_mgr.get_offsets()}, customer id: {kafka_mgr.account_id}"
    )
    if operation_type == MaintenanceOperation.DISASTER_RECOVERY:
        if action == MaintenanceAction.START:
            timeout = Timeout.MAINTENANCE_EVENT_DR_START.value
        elif action == MaintenanceAction.STOP:
            timeout = Timeout.MAINTENANCE_EVENT_DR_STOP.value
    elif operation_type == MaintenanceOperation.UPGRADE:
        if action == MaintenanceAction.START:
            timeout = Timeout.MAINTENANCE_EVENT_UPGRADE_START.value
        elif action == MaintenanceAction.STOP:
            timeout = Timeout.MAINTENANCE_EVENT_UPGRADE_STOP.value
        elif action == MaintenanceAction.ERROR:
            timeout = Timeout.MAINTENANCE_EVENT_UPGRADE_ERROR.value
    elif operation_type == MaintenanceOperation.DEBUG:
        timeout = Timeout.MAINTENANCE_EVENT_DEBUG.value

    message = wait_for_event(
        kafka_mgr,
        event_type,
        cvsa_id=kafka_mgr.cvsa_id,
        timeout=timeout,
        event_filters=[
            event_filter_maintenance_operation_type(operation_type),
            event_filter_maintenance_action(action),
            event_filter_cvsa_id(kafka_mgr.cvsa_id),
        ],
    )
    logger.info(f"Message found and verified {event_type}: {message}")
