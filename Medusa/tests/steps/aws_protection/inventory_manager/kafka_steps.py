import logging
from typing import List, Union
from waiting import TimeoutExpired, wait
from kafka.protocol.message import Message as KafkaMessage
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.app_type import AppType
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.audit_event_states import AuditState
from lib.common.enums.protection_summary import ProtectionStatus
from lib.dscc.backup_recovery.aws_protection.inventory_manager.inventory_manager_models import (
    AssetDeleteEvent,
    AssetUpdateEvent,
    AssetStateInfo,
    AuditEvent,
    AuditResource,
)
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.kafka.eventfilters import EventFilter, event_filters_reduce
from lib.platform.kafka.kafka_manager import KafkaManager


logger = logging.getLogger()
config = ConfigManager.get_config()


def _event_filter_type(event_type: AtlantiaKafkaEvents) -> EventFilter:
    """Get the Event Filter Type

    Args:
        event_type (AtlantiaKafkaEvents): Atlantia Kafka Events object

    Returns:
        EventFilter: Event Filter type
    """

    def f(event: KafkaMessage) -> bool:
        headers = dict(map(lambda x: (x[0], x[1]), event.headers))
        return bytes(event_type.value, "utf-8") in headers["ce_type"]

    return f


def _event_filter(key: str, value: str) -> EventFilter:
    """Get Event Filter

    Args:
        key (str): Key tagged to Event Filter
        value (str): Value tagged to Event Filter

    Returns:
        EventFilter: Event Filter object
    """
    return lambda event: True if event.value.get(key) == value else False


def _associated_resource_event_filter(key: str, value: AuditResource) -> EventFilter:
    """Get Associated Resource Event Filter

    Args:
        key (str): Key tagged to associated resource event filter
        value (AuditResource): Value tagged to associated resource event filter

    Returns:
        EventFilter: Event Filter object
    """
    return lambda event: value == AuditResource.from_dict(event.value.get(key))


def get_latest_event(
    kafka_manager: KafkaManager,
    event_type: AtlantiaKafkaEvents,
    event_filters: List[EventFilter] = None,
    account_id: str = None,
    csp_id: str = None,
    id: str = None,
    region: str = None,
    scheduler_job_trigger_type: str = None,
    audit_event_code: str = None,
    audit_event_state: str = None,
    associated_resource: AuditResource = None,
) -> Union[KafkaMessage, bool]:
    """Retrieves the latest kafka events based on the event filters.

    This method is used by different Kafka events such as
    1. Asset Create/Delete/Update Event where account_id, csp_id and region filters are passed.
    2. Audit Event where audit_event_code and audit_event_state filters are passed.

    Args:
        kafka_manager (KafkaManager): Kafka Manager object
        event_type (AtlantiaKafkaEvents): Atlantia Kafka Events object
        event_filters (List[EventFilter], optional): Parameter filters for events. Defaults to None.
        account_id (str, optional): CSP Account ID. Defaults to None.
        csp_id (str, optional): CSP Asset ID. Defaults to None.
        id (str, optional): Event ID. Defaults to None.
        region (str, optional): Targeted region. Defaults to None.
        scheduler_job_trigger_type (str, optional): Type of triggered scheduler job. Defaults to None.
        audit_event_code (str, optional): Code for audit event. Defaults to None.
        audit_event_state (str, optional): State for audit event. Defaults to None.
        associated_resource (AuditResource, optional): Associated resource to latest event. Defaults to None.

    Returns:
        Union[KafkaMessage, bool]: Latest Event | False if not able to retrieve
    """
    # This function is derived from get_latest_event() found in the cVSA module:
    # .../steps/aws_protection/cvsa/kafka_steps.py
    if not event_filters:
        event_filters = []
    event_filters.append(_event_filter_type(event_type))
    if account_id:
        event_filters.append(_event_filter(key="accountId", value=account_id))
    if csp_id:
        event_filters.append(_event_filter(key="cspId", value=csp_id))
    if id:
        event_filters.append(_event_filter(key="id", value=id))
    if region:
        event_filters.append(_event_filter(key="region", value=region))
    if audit_event_code:
        event_filters.append(_event_filter(key="code", value=audit_event_code))
    if audit_event_state:
        event_filters.append(_event_filter(key="state", value=audit_event_state))
    if scheduler_job_trigger_type:
        event_filters.append(_event_filter(key="trigger_type", value=scheduler_job_trigger_type))
    if associated_resource:
        event_filters.append(_associated_resource_event_filter(key="associatedResource", value=associated_resource))

    try:
        messages = kafka_manager.read_messages(from_offset=kafka_manager.get_offsets())
        messages_filtered = event_filters_reduce(event_filters, messages)
        # TODO: Rethink our approach for selecting the event to compare.
        #   There should be only one logic for choosing the proper message.
        if len(messages_filtered) > 0:
            return messages_filtered[0]
    except AttributeError:
        pass
    logger.info(
        f"Event not found: {event_type}, from offset: {kafka_manager.get_offsets()}, \
                            customer id: {kafka_manager.account_id}, csp_id:{csp_id}, region: {region}"
    )
    return False


def wait_for_event(
    kafka_manager: KafkaManager,
    event_type: AtlantiaKafkaEvents,
    region: str = None,
    account_id: str = None,
    csp_id: str = None,
    id: str = None,
    scheduler_job_trigger_type: any = None,
    timeout: int = 300,
    interval: int = 1,
    audit_event_code: str = None,
    audit_event_state: str = None,
    event_filters: str = None,
    set_offset_after_event: bool = True,
    associated_resource: AuditResource = None,
) -> Union[KafkaMessage, bool]:
    """Wait for an event to complete

    Args:
        kafka_manager (KafkaManager): Kafka Manager object
        event_type (AtlantiaKafkaEvents): Event type
        region (str, optional): Targeted region. Defaults to None.
        account_id (str, optional): CSP Account ID. Defaults to None.
        csp_id (str, optional): CSP Asset ID. Defaults to None.
        id (str, optional): Event ID. Defaults to None.
        scheduler_job_trigger_type (any, optional): Type of scheduler job. Defaults to None.
        timeout (int, optional): Duration to run until. Defaults to 300.
        interval (int, optional): Time in between. Defaults to 1.
        audit_event_code (str, optional): Expected Audit event code. Defaults to None.
        audit_event_state (str, optional): Expected Audit event state. Defaults to None.
        event_filters (str, optional): Parameter filters for events. Defaults to None.
        set_offset_after_event (bool, optional): Offsets post-event. Defaults to True.
        associated_resource (AuditResource, optional): Audit resource that is associated. Defaults to None.

    Raises:
        AssertionError: Assert

    Returns:
        KafkaMessage: Message of latest event
        bool: False if latest event message was not found
    """
    # This function is derived from wait_for_event() found in the cVSA module:
    # .../steps/aws_protection/cvsa/kafka_steps.py

    # Log message event type and partition current/end offsets
    partition_offsets = []
    assignments = kafka_manager.consumer.assignment()
    end_offsets = kafka_manager.consumer.end_offsets(assignments)
    for end_offset in end_offsets:
        position = kafka_manager.consumer.position(end_offset)
        partition_offsets.append(
            f"partition={end_offset.partition}, current_offset={position}, end_offset={end_offsets[end_offset]}"
        )
    logger.info(f"Waiting for message: event={event_type}, {partition_offsets}")

    try:
        message = wait(
            lambda: get_latest_event(
                kafka_manager=kafka_manager,
                event_type=event_type,
                region=region,
                account_id=account_id,
                csp_id=csp_id,
                id=id,
                audit_event_code=audit_event_code,
                audit_event_state=audit_event_state,
                scheduler_job_trigger_type=scheduler_job_trigger_type,
                event_filters=event_filters,
                associated_resource=associated_resource,
            ),
            timeout_seconds=timeout,
            sleep_seconds=interval,
        )
        logger.info(f"Message {event_type} found: {message}")
        if set_offset_after_event:
            kafka_manager.set_offset_after_event(message)
        return message
    except TimeoutExpired:
        for msg in kafka_manager.consumer:
            logger.error(f"Kafka messages on topic: {msg}")
        raise AssertionError(f"Kafka event {event_type} was not found in topic after {timeout} seconds.")


def verify_asset_update_event(
    aws: AWS,
    kafka_manager: KafkaManager,
    event_type: AtlantiaKafkaEvents,
    csp_id: str,
    account_id: str = None,
    protection_status: ProtectionStatus = ProtectionStatus.UNPROTECTED,
    recovery_point_exists: bool = False,
    policy_assigned: bool = False,
    expected_name: str = "",
    set_offset_after_event=True,
):
    """Verify Asset Update Event information

    Args:
        aws (AWS): AWS object
        kafka_manager (KafkaManager): Kafka Manager object
        event_type (AtlantiaKafkaEvents): Event type
        csp_id (str): CSP asset ID
        account_id (str, optional): CSP Account ID. Defaults to None.
        protection_status (ProtectionStatus, optional): Expected Protection Status. Defaults to ProtectionStatus.UNPROTECTED.
        recovery_point_exists (bool, optional): Expected recovery point existence. Defaults to False.
        policy_assigned (bool, optional): Expected policy assigned. Defaults to False.
        expected_name (str, optional): Expected name. Defaults to "".
        set_offset_after_event (bool, optional): Offsets post-event. Defaults to True.
    """
    if account_id is None:
        account_id = config["ATLANTIA-API"]["region-one-account-id"]

    # Loop twice to ignore possibility of a single spurious protection status event (details below).
    # TODO: Should future updates to Inventory Manager complete processing of Kafka events, in the
    # order they are received, this workaround for a spurious protection status should be removed.
    for i in range(2):
        message = wait_for_event(
            kafka_manager=kafka_manager,
            event_type=event_type,
            account_id=account_id,
            region=aws._aws_session_manager.region_name,
            csp_id=csp_id,
            set_offset_after_event=set_offset_after_event,
        )

        # Validate asset update event properties
        response: AssetUpdateEvent = AssetUpdateEvent.from_dict(message.value)
        assert response.app_type == AppType.aws.value
        if (
            event_type == AtlantiaKafkaEvents.REPORT_INSTANCE_CREATE_EVENT_TYPE
            or event_type == AtlantiaKafkaEvents.REPORT_VOLUME_CREATE_EVENT_TYPE
        ):
            assert response.generation == 0
        else:
            assert response.generation > 0
        if expected_name == "":
            assert response.name == response.csp_id
        else:
            assert response.name == expected_name
        assert response.region == aws._aws_session_manager.region_name
        assert response.recovery_point_exists is recovery_point_exists
        assert response.policy_assigned is policy_assigned

        # Only on the first attempt, if an unexpected protection status is received, a warning is logged and the
        # loop continues to validate against the next received protection status.  See DCS-5718 for a discussion
        # of how a spurious protection status can get generated if Kafka events are processed in a different
        # order than they were received.
        if i == 0 and response.protection_status != protection_status.value:
            logger.warn(
                "Spurious protection status received and ignored"
                + f", csp_id={csp_id}"
                + f", expected={protection_status.value}"
                + f", received={response.protection_status}"
            )
            continue

        # At this point, retries are exhausted.  Received protection status should match expected protection status.
        assert response.protection_status == protection_status.value, (
            "Unexpected protection status received"
            + f", csp_id={csp_id}"
            + f", expected={protection_status.value}"
            + f", received={response.protection_status}"
        )
        break

    logger.info("Verified asset update event")


def verify_asset_delete_event(
    kafka_manager: KafkaManager,
    event_type: AtlantiaKafkaEvents,
    csp_id: str,
    account_id: str = None,
    set_offset_after_event=True,
):
    """Verify Asset Delete Event

    Args:
        kafka_manager (KafkaManager): Kafka Manager object
        event_type (AtlantiaKafkaEvents): Event type
        csp_id (str): CSP Asset ID
        account_id (str, optional): CSP Account ID. Defaults to None.
        set_offset_after_event (bool, optional): Set offset post-event. Defaults to True.
    """
    if account_id is None:
        account_id = config["ATLANTIA-API"]["region-one-account-id"]

    message = wait_for_event(
        kafka_manager=kafka_manager,
        event_type=event_type,
        account_id=account_id,
        csp_id=csp_id,
        set_offset_after_event=set_offset_after_event,
    )

    # Validate asset delete event properties
    response: AssetDeleteEvent = AssetDeleteEvent.from_dict(message.value)
    assert response.app_type == AppType.aws.value
    logger.info("Verified asset deletion event")


def verify_asset_state_info_event(
    kafka_manager: KafkaManager,
    event_type: AtlantiaKafkaEvents,
    type: str,
    id: str,
    state: str,
    account_id: str = None,
    set_offset_after_event=True,
):
    """Verify Asset State information of Event

    Args:
        kafka_manager (KafkaManager): Kafka Manager object
        event_type (AtlantiaKafkaEvents): Event type
        type (str): Asset type
        id (str): Asset ID
        state (str): Asset state
        account_id (str, optional): CSP Account ID. Defaults to None.
        set_offset_after_event (bool, optional): Set offset post-event. Defaults to True.
    """
    if account_id is None:
        account_id = config["ATLANTIA-API"]["region-one-account-id"]

    message = wait_for_event(
        kafka_manager=kafka_manager,
        event_type=event_type,
        id=id,
        set_offset_after_event=set_offset_after_event,
    )

    # Validate asset state event properties
    response: AssetStateInfo = AssetStateInfo.from_dict(message.value)
    assert response.type == type
    assert str(response.id) == id
    assert response.state == state
    logger.info("Verified asset state event")


def verify_audit_event(
    kafka_manager: KafkaManager,
    event_type: AtlantiaKafkaEvents,
    code: str,
    customer_id: str,
    permission: str,
    state: str = AuditState.SUCCESS.value,
    id: any = None,
    associated_resource: AuditResource = None,
    set_offset_after_event=True,
):
    """Verify Audit Event

    Args:
        kafka_manager (KafkaManager): Kafka Manager object
        event_type (AtlantiaKafkaEvents): Event type
        code (str): Expected code
        customer_id (str): CSP Customer ID
        permission (str): Expected permission
        state (str, optional): Expected State. Defaults to AuditState.SUCCESS.value.
        id (any, optional): Event ID. Defaults to None.
        associated_resource (AuditResource, optional): Audit resource that is associated.. Defaults to None.
        set_offset_after_event (bool, optional): Set offset post-event. Defaults to True.
    """
    message = wait_for_event(
        kafka_manager=kafka_manager,
        event_type=event_type,
        id=id,
        audit_event_code=code,
        audit_event_state=state,
        associated_resource=associated_resource,
        set_offset_after_event=set_offset_after_event,
    )

    # Validate audit event properties
    response: AuditEvent = AuditEvent.from_dict(message.value)
    assert str(response.customer_id) == customer_id
    assert str(response.permission) == str(permission)
    logger.info("Verified audit event")
