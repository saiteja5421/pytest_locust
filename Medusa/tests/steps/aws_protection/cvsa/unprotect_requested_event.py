import lib.platform.kafka.protobuf.cvsa_manager.cvsa_manager_pb2 as events_pb2

from lib.common.enums.cvsa import RequestFinishedStatus, CloudRegions
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_correlation_id
from lib.platform.kafka.kafka_manager import KafkaManager, logger
from tests.functional.aws_protection.cvsa_manager.constants import AWS_REGION_1_ENUM
from tests.steps.aws_protection.cvsa.kafka_steps import wait_for_event


def send_unprotect_requested_event(cvsa_kafka: KafkaManager, state_type: str = "ACLM", headers: dict = None):
    cvsa_kafka.correlation_id = cvsa_kafka.generate_key()

    if not headers:
        headers = {}
    headers.update(
        {
            "ce_id": cvsa_kafka.account_id,
            "ce_type": b"cvsa.v1.CVSAUnprotectRequestedEvent",
            "ce_partitionkey": cvsa_kafka.account_id,
            "ce_customerid": cvsa_kafka.account_id,
        }
    )
    state = f"CVSA_UNPROTECT_REQUEST_REASON_ENUM_{state_type}"
    unprotect_event = events_pb2.CVSAUnprotectRequestedEvent()
    unprotect_event.cam_account_id = cvsa_kafka.cam_account_id
    unprotect_event.csp_account_id = cvsa_kafka.csp_account_id
    unprotect_event.correlation_id = cvsa_kafka.correlation_id
    unprotect_event.reason = events_pb2._CVSAUNPROTECTREQUESTREASON.values_by_name[state].number
    logger.info(f"Send message: cvsa.v1.CVSAUnprotectRequestedEvent, customer_id: {cvsa_kafka.account_id}")
    cvsa_kafka.send_message(event=unprotect_event, user_headers=headers)


def verify_unprotect_requested_event(
    cvsa_kafka: KafkaManager,
    state_type: str = "ACLM",
    cloud_region: CloudRegions = AWS_REGION_1_ENUM,
):
    event_type = "cvsa.v1.CVSAUnprotectRequestedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, from offset: {cvsa_kafka.get_offsets()}, customer id: {cvsa_kafka.account_id}"
    )
    message = wait_for_event(
        cvsa_kafka,
        event_type,
        cloud_region=cloud_region,
        event_filters=[event_filter_correlation_id(cvsa_kafka.correlation_id)],
        timeout=Timeout.REQUESTED_EVENT.value,
    )
    state = f"CVSA_UNPROTECT_REQUEST_REASON_ENUM_{state_type}"
    logger.info(f"Message found {event_type}: {message}")
    # unprotect_event = events_pb2.CVSAUnprotectRequestedEvent()
    unprotect_event = message.value
    assert unprotect_event["reason"] == events_pb2._CVSAUNPROTECTREQUESTREASON.values_by_name[state].name
    assert unprotect_event["cspAccountId"] == cvsa_kafka.csp_account_id.decode("utf-8")
    assert unprotect_event["camAccountId"] == cvsa_kafka.cam_account_id.decode("utf-8")
    assert unprotect_event["correlationId"] == cvsa_kafka.correlation_id.decode("utf-8")
    logger.info(f"Message verified {event_type}")


def verify_finished_event_for_unprotect(
    cvsa_kafka: KafkaManager,
    cloud_region: CloudRegions = AWS_REGION_1_ENUM,
    result: RequestFinishedStatus = RequestFinishedStatus.STATUS_OK,
    error_msg: str = "",
):
    event_type = "cvsa.v1.CVSAUnprotectFinishedEvent"
    logger.info(
        f"Searching for message: event: {event_type}, from offset: {cvsa_kafka.get_offsets()}, customer id: {cvsa_kafka.account_id}"
    )
    message = wait_for_event(
        cvsa_kafka,
        event_type,
        cloud_region=cloud_region,
        event_filters=[event_filter_correlation_id(cvsa_kafka.correlation_id)],
        timeout=Timeout.UNPROTECT_FINISHED_EVENT.value,
    )
    logger.info(f"Message found {event_type}: {message}")
    # unprotect_event = events_pb2.CVSAUnprotectFinishedEvent()
    unprotect_event = message.value
    assert unprotect_event["result"] == result.name
    assert unprotect_event["correlationId"] == cvsa_kafka.correlation_id.decode("utf-8")
    assert unprotect_event["camAccountId"] == cvsa_kafka.cam_account_id.decode("utf-8")
    if error_msg:
        assert error_msg in unprotect_event["errorMsg"]
    logger.info(f"Message verified {event_type}")
