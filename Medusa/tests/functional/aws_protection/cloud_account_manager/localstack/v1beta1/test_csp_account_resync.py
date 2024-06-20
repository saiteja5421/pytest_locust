import logging
import uuid

from pytest import fixture, mark

from lib.common.config.config_manager import ConfigManager
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
import tests.steps.aws_protection.cloud_account_manager.kafka_steps as KafkaSteps
from lib.common.enums.provided_users import ProvidedUser
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.csp_account import (
    CSPAccount,
)
from lib.common.enums.csp_type import CspType
from lib.platform.kafka.kafka_manager import KafkaManager, TopicEncoding
from tests.e2e.aws_protection.context import Context


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


@fixture(scope="module")
def csp_accounts(context: Context):
    # Create new CSP Accounts
    i = 0
    stop = 5
    csp_accounts: list[CSPAccount] = []

    while i < stop:
        csp_id = "arn:aws:iam::12341234123" + str(i) + ":"
        csp_account_name = "MyAccount-" + str(uuid.uuid4())
        csp_account: CSPAccount = context.cam_client_v1beta1.create_csp_account(
            csp_id=csp_id, name=csp_account_name, csp_type=CspType.AWS
        )
        csp_accounts.append(csp_account)
        i += 1

    yield csp_accounts

    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")

    # Delete CSP Accounts
    i = 0
    while i < stop:
        context.cam_client_v1beta1.delete_csp_account(account_id=csp_accounts[i].id)
        i += 1

    logger.info(10 * "=" + "Teardown Complete!" + 10 * "=")


##############################################################################################################
# FUNCTIONAL TESTS
##############################################################################################################


@mark.cam_localstack_serial2
def test_resync_csp_accounts(context: Context, csp_accounts: list[CSPAccount]):
    """
        Functional test that tests the CSP Account resync by forcing a resync through REST

    Args:
        context (Context): test execution context
        csp_accounts (list): fixture that creates and yields a list of new CSP accounts
    """
    # Step 1 - Fixture takes care of creating the accounts

    # Step 2 - Force a CSP account resync through REST and validate the kakfa messages sent
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.CSP_CAM_UPDATES.value,
        topic_encoding=TopicEncoding.PROTOBUF,
        host=config["KAFKA"]["host"],
        account_id="8922afa6723011ebbe01ca32d32b6b77".encode("utf-8"),
    )

    context.cam_client_v1beta1.resync_csp_accounts()

    # Read and verify Kafka messages
    for csp_account in csp_accounts:
        logger.info(f"Verifying msg for account: {csp_account.csp_id}")
        KafkaSteps.verify_account_info_repeat_event(
            kafka_manager=kafka_manager,
            event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_REPEAT_EVENT_TYPE,
            csp_id=csp_account.csp_id,
            # id=csp_account.id.encode("utf-8"),
        )
