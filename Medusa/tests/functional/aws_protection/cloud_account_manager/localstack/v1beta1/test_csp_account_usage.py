import logging
import uuid
import random

from pytest import fixture, mark
from waiting import wait

import lib.platform.kafka.protobuf.cloud_account_manager.account_use_pb2 as account_use_pb2

from lib.common.config.config_manager import ConfigManager
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.common.enums.provided_users import ProvidedUser
from tests.steps.aws_protection.v1beta1.cloud_account_manager_steps import (
    delete_csp_account_expect_failure,
)
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.csp_account import (
    CSPAccount,
)
from lib.common.enums.csp_type import CspType
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.common_steps import send_kafka_message


##############################################################################################################
# MODULE VARIABLES AND TEST SETTINGS
##############################################################################################################

config = ConfigManager.get_config()
logger = logging.getLogger()


##############################################################################################################
# FIXTURES
##############################################################################################################


@fixture(scope="module")
def context():
    context = Context(test_provided_user=ProvidedUser.user_one, initialize_minimal=True)
    return context


##############################################################################################################
# FUNCTIONAL TESTS
##############################################################################################################

logger = logging.getLogger()
start = 100000000000
stop = 1000000000000
csp_id = "arn:aws:iam::" + str(random.randrange(start, stop)) + ":"
csp_account_name = "MyAccount-" + str(uuid.uuid4())
service1 = "service1"
service2 = "service2"


@mark.cam_localstack_serial3
def test_csp_account_usage(context: Context):
    logger.info("Create a new CSP Account")
    created_csp_account: CSPAccount = context.cam_client_v1beta1.create_csp_account(
        csp_id=csp_id, name=csp_account_name, csp_type=CspType.AWS
    )

    logger.info("Fetching created account")
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(
        account_id=created_csp_account.id
    )
    assert created_csp_account.name == fetched_csp_account.name
    assert fetched_csp_account.services == []

    logger.info("Add a service subscription by sending ACLM kafka message")
    send_account_use_by_service_event(context, fetched_csp_account, service1, True)

    logger.info("Fetching updated account")
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(
        account_id=created_csp_account.id
    )
    assert fetched_csp_account.services == [service1]

    logger.info("Attempt to unregister the account which should fail")
    delete_csp_account_expect_failure(context=context, account_id=fetched_csp_account.id)

    logger.info("Add another service subscription")
    send_account_use_by_service_event(context, fetched_csp_account, service2, True)

    logger.info("Fetching updated account")
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(
        account_id=created_csp_account.id
    )
    assert fetched_csp_account.services == [service1, service2]

    logger.info("Try adding duplicate service subscription")
    send_account_use_by_service_event(context, fetched_csp_account, service2, True)

    logger.info("Fetching updated account")
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(
        account_id=created_csp_account.id
    )
    assert fetched_csp_account.services == [service1, service2]

    logger.info("Remove a service subscription")
    send_account_use_by_service_event(context, fetched_csp_account, service1, False)

    logger.info("Fetching updated account")
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(
        account_id=created_csp_account.id
    )
    assert fetched_csp_account.services == [service2]

    logger.info("Attempt to unregister the account which should fail")
    delete_csp_account_expect_failure(context=context, account_id=fetched_csp_account.id)

    logger.info("Remove the last service subscription")
    send_account_use_by_service_event(context, fetched_csp_account, service2, False)

    logger.info("Fetching updated account")
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(
        account_id=created_csp_account.id
    )
    assert fetched_csp_account.services == []

    logger.info("Attempt to unregister the account which should succeed")
    context.cam_client_v1beta1.delete_csp_account(account_id=fetched_csp_account.id)


def send_account_use_by_service_event(context: Context, csp_account: CSPAccount, service: str, subscribe: bool):
    """
        Send CspAccountUseByService event to CAM.

    Args:
        context (Context): test execution context
        csp_account (CSPAccount): The CSP Account whose usage is being modified
        service (str): The service to subscribe or unsubscribe
        subscribe (bool): Whether to subscribe or unsubscribe from the account
    """
    requested_event = account_use_pb2.CspAccountUseByService()
    requested_event.account_id = str(csp_account.id)
    requested_event.service_name = service
    requested_event.is_in_use = subscribe

    logger.info(f"requested_event = {requested_event}")

    kafka_manager = KafkaManager(topic=AtlantiaKafkaTopics.CSP_CAM_COMMANDS.value, host=config["KAFKA"]["host"])
    send_kafka_message(
        kafka_manager=kafka_manager,
        requested_event=requested_event,
        event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_USE_BY_SERVICE_EVENT_TYPE.value,
        customer_id=context.get_customer_id(),
    )

    def _wait_for_message_consume():
        current_offset, _ = kafka_manager.consumer_group_offset("cam_client_v1beta1", 0)
        return current_offset >= end_offset

    _, end_offset = kafka_manager.consumer_group_offset("cam_client_v1beta1", 0)

    # wait for Kafka message processing
    wait(_wait_for_message_consume, timeout_seconds=120, sleep_seconds=1)
