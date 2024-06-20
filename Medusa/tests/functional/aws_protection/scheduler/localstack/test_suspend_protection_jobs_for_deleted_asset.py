"""
TestRail ID - C57483873 - Validate suspend protection jobs for deleted asset 
"""

import logging
import json
import uuid
from lib.common.enums.csp_protection_job_type import CSPProtectionJobType
from lib.common.enums.kafka_inventory_asset_type import KafkaInventoryAssetType
from pytest import fixture, mark
from pytest_testrail.plugin import pytestrail
from lib.common.enums.postgres_config import PostgresConfig
from lib.platform.postgres.postgres_manager import PostgresManager
from lib.common.enums.protection_types import ProtectionType
from lib.common.enums.atlas_policy_operations import AtlasPolicyOperations
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.provided_users import ProvidedUser
from tests.e2e.aws_protection.context import Context
from lib.common.config.config_manager import ConfigManager

from tests.steps.aws_protection.protection_job_steps import (
    send_delete_protection_job,
    initial_scheduler_test_setup,
    wait_and_validate_protection_job,
    wait_and_validate_protection_jobs_for_asset_deletion,
    send_asset_state_info,
    send_customer_account_kafka_message,
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
@pytestrail.case("C57483873")
def test_validate_suspend_protection_jobs_for_deleted_asset(
    context: Context, dbase_connection: tuple[any, PostgresManager]
):
    """
    Validates that protection jobs are suspended for assets deleted by inventory manager.
    """
    db_connection, postgres_manager = dbase_connection
    customer_id: str = context.get_customer_id()
    account_id = config["ATLANTIA-API"]["csp-scheduler-account-id"]
    asset_id = str(uuid.uuid4())
    job_payload = initial_scheduler_test_setup(
        customer_id,
        account_id,
        asset_id,
        db_connection,
        postgres_manager,
        ProtectionType.BACKUP.value,
        CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB.value,
    )
    json_object = json.loads(job_payload)
    job_id = json_object.get("id", {})
    # protection_policy_id = json_object["protectionPolicy"]["id"]
    # wait_and_validate_protection_job(
    #     customer_id,
    #     job_id,
    #     AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
    #     postgres_manager,
    #     db_connection,
    # )

    send_asset_state_info(customer_id, 1, asset_id, 2)

    wait_and_validate_protection_jobs_for_asset_deletion(
        asset_id,
        job_id,
        postgres_manager,
        db_connection,
    )

    # TODO: If the protection job is not in ACTIVE state, Scheduler will not perform protection job
    # delete operation. Since this test suspends the workflows for deleted asset, Scheduler skips
    # below clean up. This will be fixed soon.

    # Clean up protection job
    # send_delete_protection_job(
    #     context=context,
    #     customer_id=customer_id,
    #     csp_asset_id="",
    #     asset_type=KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE.value,
    #     protection_job_id=job_id,
    #     protection_policy_id=protection_policy_id,
    #     wait_for_complete=False,
    #     event_operation=AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
    #     ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_DELETE_EVENT_TYPE.value,
    #     kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    # )
    # wait_and_validate_protection_job(
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
