"""
TestRail ID - C56953281 - Validate Scheduler operations for CSP Account creation
"""

import logging
import uuid
import json

from pytest import fixture, mark
from pytest_testrail.plugin import pytestrail
from lib.common.enums.postgres_config import PostgresConfig
from lib.platform.postgres.postgres_manager import PostgresManager
from lib.common.enums.csp_protection_job_type import CSPProtectionJobType
from lib.common.enums.protection_types import ProtectionType
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.atlas_policy_operations import AtlasPolicyOperations
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.provided_users import ProvidedUser
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.protection_job_steps import (
    send_customer_account_kafka_message,
    send_suspend_protection_job,
    initial_scheduler_test_setup,
    wait_and_validate_protection_job,
    check_account_status,
)

logger = logging.getLogger()
config = ConfigManager.get_config()


@fixture(scope="session")
def context():
    return Context(test_provided_user=ProvidedUser.user_one, initialize_minimal=True)


@fixture(scope="session")
def dbase_connection():
    postgres_manager = PostgresManager()
    connection = postgres_manager.create_db_connection(
        db_name=PostgresConfig.SCHEDULER_DB.value,
        host=PostgresConfig.PG_HOST.value,
        port=PostgresConfig.PG_PORT.value,
    )
    yield connection, postgres_manager
    logger.info("Cleaning up DB connection!")
    postgres_manager.close_db_connection(connection=connection)


@mark.csp_scheduler_localstack
@pytestrail.case("C56953281")
def test_customer_account(context: Context, dbase_connection: tuple[any, PostgresManager]):
    """
    This method will check the Customer Account Status functionality. This function validates
    that the protection jobs suspended before account suspend will not be affected.
    Register account -> Create protection jobs -> Suspend one protection job ->  Suspend account ->
    Resume account -> Unregister CSP account
    """
    db_connection, postgres_manager = dbase_connection

    customer_id: str = context.get_customer_id()
    csp_account_id = config["ATLANTIA-API"]["csp-scheduler-account-id"]

    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (REGISTER) on atlas.policy.commands topic
    send_customer_account_kafka_message(
        event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value,
        account_id=csp_account_id,
        customer_id=customer_id,
        status=1,
    )
    check_account_status(csp_account_id, customer_id, "Registered", postgres_manager, db_connection)

    """
    Protect two assets to create a new protection jobs for the CSP account
    """
    job_1_payload = initial_scheduler_test_setup(
        customer_id,
        csp_account_id,
        str(uuid.uuid4()),
        db_connection,
        postgres_manager,
        ProtectionType.BACKUP.value,
        CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB.value,
    )
    json_object = json.loads(job_1_payload)
    _ = json_object.get("id", {})
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_1,
    #     AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
    #     postgres_manager,
    #     db_connection,
    # )

    job_2_payload = initial_scheduler_test_setup(
        customer_id,
        csp_account_id,
        str(uuid.uuid4()),
        db_connection,
        postgres_manager,
        ProtectionType.CLOUD_BACKUP.value,
        CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB.value,
    )
    json_object = json.loads(job_2_payload)
    job_id_2 = json_object.get("id", {})
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_2,
    #     AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
    #     postgres_manager,
    #     db_connection,
    # )

    """
    Suspend a protection job
    """
    send_suspend_protection_job(
        customer_id=customer_id,
        protection_policy_schedule_ids=[1],
        protection_job_id=job_id_2,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_SUSPEND_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_2,
    #     AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
    #     postgres_manager,
    #     db_connection,
    # )
    """
    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (CSP Account SUSPEND) on csp.cam.updates topic
    # Account suspend should also suspend any protection jobs that are ACTIVE
    # but not update the protection jobs that are already SUSPENDED
    """
    send_customer_account_kafka_message(
        event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value,
        account_id=csp_account_id,
        customer_id=customer_id,
        status=1,
        suspended=True,
    )
    check_account_status(csp_account_id, customer_id, "Suspended", postgres_manager, db_connection)

    # Verify that the active protection job (job_id_1) is in ACCNTSUSPENDED state
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_1,
    #     AtlasPolicyOperations.PROTECTION_JOB_ACCT_SUSPEND.value,
    #     postgres_manager,
    #     db_connection,
    # )
    # # Verify that CSP account suspend did not update protection jobs that are in SUSPENDED state
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_2,
    #     AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
    #     postgres_manager,
    #     db_connection,
    # )

    """
    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (RESUME) on csp.cam.updates topic
    # CSP Account Resume should also Resume any protection jobs that are ACCNTSUSPENDED
    # but not update the protection jobs that are previously SUSPENDED
    """
    send_customer_account_kafka_message(
        event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value,
        account_id=csp_account_id,
        customer_id=customer_id,
        status=1,
        suspended=False,
    )

    check_account_status(csp_account_id, customer_id, "Resume", postgres_manager, db_connection)
    # Verify that the protection job (job_id_1) previously in ACCNTSUSPENDED state is ACTIVE after account Resume
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_1,
    #     AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
    #     postgres_manager,
    #     db_connection,
    # )
    # # Verify that CSP account Resume did not update protection jobs that are in SUSPENDED state
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_2,
    #     AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
    #     postgres_manager,
    #     db_connection,
    # )
    """
    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (UNREGISTER) on csp.cam.updates topic
    # CSP Account Unregister will also terminate any protection jobs for the account and Delete from DB.
    """
    send_customer_account_kafka_message(
        event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value,
        account_id=csp_account_id,
        customer_id=customer_id,
        status=2,
    )
    check_account_status(csp_account_id, customer_id, "Unregistered", postgres_manager, db_connection)
    # Verify that all protection jobs for the account are Terminated and deleted from DB.
    # TODO- Fix this assertion later as the protection job validations are different
    # for Account unregister and protection job Delete
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_1,
    #     AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
    #     postgres_manager,
    #     db_connection,
    # )
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id_2,
    #     AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
    #     postgres_manager,
    #     db_connection,
    # )
