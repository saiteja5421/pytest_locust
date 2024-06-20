import logging

import lib.platform.kafka.protobuf.cloud_account_manager.account_pb2 as cam_pb2
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.kafka.kafka_manager import KafkaManager
from lib.platform.kafka.eventfilters.cvsamanager import event_filter_csp_account_info_status
from tests.steps.aws_protection.cvsa.kafka_steps import wait_for_event
from lib.common.enums.cvsa import CspAccountInfoStatus

logger = logging.getLogger()


def send_unregister_event(cvsa_kafka: KafkaManager, cam_updates_kafka: KafkaManager, headers: dict = None):
    unregister_event = cam_pb2.CspAccountInfo()

    if not headers:
        headers = {}
    headers.update(
        {
            "ce_id": cvsa_kafka.account_id,
            "ce_type": b"csp.cloudaccountmanager.v1.CspAccountInfo",
            "ce_partitionkey": cvsa_kafka.account_id,
            "ce_customerid": cvsa_kafka.account_id,
        }
    )
    unregister_event.id = cvsa_kafka.cam_account_id
    unregister_event.name = f"cVSA_Manager_Tests_Unregister_{cvsa_kafka.cvsa_id}"
    unregister_event.paused = False
    unregister_event.service_provider_id = cvsa_kafka.csp_account_id
    unregister_event.status = cam_pb2._CSPACCOUNTINFO_STATUS.values_by_name["STATUS_UNREGISTERED"].number
    unregister_event.type = cam_pb2._CSPACCOUNTINFO_TYPE.values_by_name["TYPE_AWS"].number
    unregister_event.validation_status = cam_pb2._CSPACCOUNTINFO_VALIDATIONSTATUS.values_by_name[
        "VALIDATION_STATUS_FAILED"
    ].number
    cam_updates_kafka.account_id = cvsa_kafka.account_id
    cam_updates_kafka.trace_id = cvsa_kafka.trace_id
    logger.info(f"Send message: Unregister Account, customer_id: {cvsa_kafka.account_id}")
    cam_updates_kafka.send_message(event=unregister_event, user_headers=headers)


def verify_unregister_event(cvsa_kafka: KafkaManager, cam_updates_kafka: KafkaManager):
    event_type = "csp.cloudaccountmanager.v1.CspAccountInfo"
    logger.info(
        f"Searching for message: event: {event_type}. "
        f"from offset: {cam_updates_kafka.get_offsets()}, cam account id: {cvsa_kafka.cam_account_id}"
    )
    cam_updates_kafka.account_id = cvsa_kafka.account_id
    message = wait_for_event(
        kafka_manager=cam_updates_kafka,
        event_type=event_type,
        csp_cam_id=cvsa_kafka.cam_account_id,
        event_filters=[event_filter_csp_account_info_status(CspAccountInfoStatus.STATUS_UNREGISTERED)],
        timeout=Timeout.UNREGISTER_EVENT.value,
    )
    unregister_event = cam_pb2.CspAccountInfo()
    unregister_event.ParseFromString(message.value)
    assert unregister_event.id == cvsa_kafka.cam_account_id.decode("utf-8")
    assert unregister_event.name == f"cVSA_Manager_Tests_Unregister_{cvsa_kafka.cvsa_id}"
    assert unregister_event.paused is False
    assert unregister_event.service_provider_id == cvsa_kafka.csp_account_id.decode("utf-8")
    assert unregister_event.status == CspAccountInfoStatus.STATUS_UNREGISTERED.value
    assert unregister_event.type == cam_pb2._CSPACCOUNTINFO_TYPE.values_by_name["TYPE_AWS"].number
    assert (
        unregister_event.validation_status
        == cam_pb2._CSPACCOUNTINFO_VALIDATIONSTATUS.values_by_name["VALIDATION_STATUS_FAILED"].number
    )
    logger.info("Message verified Unregister Account")


def send_register_event(cvsa_kafka: KafkaManager, cam_updates_kafka: KafkaManager):
    register_event = cam_pb2.CspAccountInfo()
    headers = {
        "ce_id": cvsa_kafka.account_id,
        "ce_type": b"csp.cloudaccountmanager.v1.CspAccountInfo",
        "ce_partitionkey": cvsa_kafka.account_id,
        "ce_customerid": cvsa_kafka.account_id,
    }
    register_event.id = cvsa_kafka.cam_account_id
    register_event.name = f"cVSA_Manager_Tests_Register_{cvsa_kafka.cvsa_id}"
    register_event.paused = False
    register_event.service_provider_id = cvsa_kafka.csp_account_id
    register_event.status = cam_pb2._CSPACCOUNTINFO_STATUS.values_by_name["STATUS_REGISTERED"].number
    register_event.type = cam_pb2._CSPACCOUNTINFO_TYPE.values_by_name["TYPE_AWS"].number
    cam_updates_kafka.account_id = cvsa_kafka.account_id
    cam_updates_kafka.trace_id = cvsa_kafka.trace_id
    logger.info(f"Send message: Register Account, customer_id: {cvsa_kafka.account_id}")
    cam_updates_kafka.send_message(event=register_event, user_headers=headers)


def verify_register_event(cvsa_kafka: KafkaManager, cam_updates_kafka: KafkaManager):
    event_type = "csp.cloudaccountmanager.v1.CspAccountInfo"
    logger.info(
        f"Searching for message: event: {event_type}. "
        f"from offset: {cam_updates_kafka.get_offsets()}, cam account id: {cvsa_kafka.cam_account_id}"
    )
    cam_updates_kafka.account_id = cvsa_kafka.account_id
    message = wait_for_event(
        kafka_manager=cam_updates_kafka,
        event_type=event_type,
        csp_cam_id=cvsa_kafka.cam_account_id,
        event_filters=[event_filter_csp_account_info_status(CspAccountInfoStatus.STATUS_REGISTERED)],
        timeout=Timeout.REGISTER_EVENT.value,
    )
    register_event = cam_pb2.CspAccountInfo()
    register_event.ParseFromString(message.value)
    assert register_event.id == cvsa_kafka.cam_account_id.decode("utf-8")
    assert register_event.name == f"cVSA_Manager_Tests_Register_{cvsa_kafka.cvsa_id}"
    assert register_event.paused is False
    assert register_event.service_provider_id == cvsa_kafka.csp_account_id.decode("utf-8")
    assert register_event.status == CspAccountInfoStatus.STATUS_REGISTERED.value
    assert register_event.type == cam_pb2._CSPACCOUNTINFO_TYPE.values_by_name["TYPE_AWS"].number
    logger.info("Message verified Register Account")
