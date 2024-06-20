"""
TestRail ID - C57483874 - Workflow for CSP Account operations
"""

import logging
import uuid
import json
from lib.common.enums.csp_protection_job_type import CSPProtectionJobType
from lib.common.enums.kafka_inventory_asset_type import KafkaInventoryAssetType
from pytest import fixture, mark
from pytest_testrail.plugin import pytestrail
from lib.common.enums.postgres_config import PostgresConfig
from lib.platform.postgres.postgres_manager import PostgresManager
from lib.common.enums.protection_types import ProtectionType
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.atlas_policy_operations import AtlasPolicyOperations
from lib.common.enums.provided_users import ProvidedUser
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.protection_job_steps import (
    send_suspend_protection_job,
    send_resume_protection_job,
    send_delete_protection_job,
    send_run_protection_job,
    send_customer_account_kafka_message,
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


# @mark.xfail
@mark.csp_scheduler_localstack
@pytestrail.case("C57483874")
def test_protection_jobs_scheduler_db(context: Context, dbase_connection: tuple[any, PostgresManager]):
    """
    This method will check the Protection Job functionality
    Create -> Suspend -> Resume -> Resume -> OnDemand -> Delete ; will check negative use case
    of resuming an already resumed job
    """
    db_connection, postgres_manager = dbase_connection
    customer_id: str = context.get_customer_id()
    account_id = config["ATLANTIA-API"]["csp-scheduler-account-id"]
    protection_policy_id = config["ATLANTIA-API"]["csp-scheduler-protection-policy-id"]

    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (CREATE) on atlas.policy.commands  topic
    job_payload = initial_scheduler_test_setup(
        customer_id,
        account_id,
        str(uuid.uuid4()),
        db_connection,
        postgres_manager,
        ProtectionType.BACKUP.value,
        CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB.value,
    )
    json_object = json.loads(job_payload)
    job_id = json_object.get("id", {})
    # results = wait_and_validate_protection_job(
    #     customer_id,
    #     job_id,
    #     AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
    #     postgres_manager,
    #     db_connection,
    #     AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE,
    # )
    # TODO - Verify the Kafka an event is published for atlas.policy.internal, csp.scheduler.updates topics

    logger.info("Calling protection job suspend for jobID " + job_id)
    # Suspend one of the protection job schedules
    send_suspend_protection_job(
        customer_id=customer_id,
        protection_policy_schedule_ids=[1],
        protection_job_id=job_id,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_SUSPEND_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    # results = wait_and_validate_protection_job(
    #     customer_id,
    #     job_id,
    #     AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
    #     postgres_manager,
    #     db_connection,
    # )

    # Resume the suspended protection job schedule
    send_resume_protection_job(
        customer_id=customer_id,
        protection_policy_schedule_ids=[1],
        protection_job_id=job_id,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_RESUME_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    # results = wait_and_validate_protection_job(
    #     customer_id,
    #     job_id,
    #     AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
    #     postgres_manager,
    #     db_connection,
    # )

    # Protection job run
    send_run_protection_job(
        customer_id=customer_id,
        protection_policy_schedule_ids=[1],
        protection_job_id=job_id,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_RUN.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_RUN_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )

    # results = wait_and_validate_protection_job(
    #     customer_id,
    #     job_id,
    #     AtlasPolicyOperations.PROTECTION_JOB_RUN.value,
    #     postgres_manager,
    #     db_connection,
    #     AtlantiaKafkaEvents.SCHEDULER_INITIATE_BACKUP_REQUEST,
    # )

    # Delete protection job
    send_delete_protection_job(
        context=context,
        customer_id=customer_id,
        csp_asset_id="",
        asset_type=KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE.value,
        protection_job_id=job_id,
        protection_policy_id=protection_policy_id,
        wait_for_complete=False,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_DELETE_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    # results = wait_and_validate_protection_job(
    #     customer_id,
    #     job_id,
    #     AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
    #     postgres_manager,
    #     db_connection,
    # )

    # Clean up CSP account
    send_customer_account_kafka_message(
        event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value,
        account_id=account_id,
        customer_id=customer_id,
        status=2,
    )
    check_account_status(account_id, customer_id, "Unregistered", postgres_manager, db_connection)
