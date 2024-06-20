"""
TestRail ID - C57567583 - On Prem Asset - Volume Protection Group Workflow for protection job operations
TestRail ID - C57583458 - On Prem Asset - Volume Protection Group Workflow for protection job operations with Pre-post Scripts
TestRail ID - C57583456 - On Prem Asset - MSSQL Database Protection Group Workflow for protection job operations
"""

import logging
import uuid
import json
from lib.platform.kafka.kafka_manager import KafkaManager
from lib.common.enums.asset_info_types import AssetType
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
from lib.common.enums.onprem_protection_job_type import OnPremProtectionJobType
from tests.steps.aws_protection.protection_job_steps import (
    send_suspend_protection_job,
    send_resume_protection_job,
    send_protection_job_kafka_message,
    get_update_protection_policy_kafka_response_object,
    send_delete_protection_job,
    initial_onprem_scheduler_test_setup,
    initial_onprem_scheduler_test_setup_with_prepost_scripts,
    wait_and_validate_protection_job,
    assert_updated_repeat_interval_with_retry,
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


@mark.xfail
@mark.csp_scheduler_localstack
@pytestrail.case("C57567583")
def test_protection_jobs_onprem_vpg(context: Context, dbase_connection: tuple[any, PostgresManager]):
    """
    This method will check the Protection Job Create functionality of Volume Protection Group
    Create -> Suspend -> Resume -> Update -> Delete
    """
    db_connection, postgres_manager = dbase_connection
    customer_id: str = context.get_customer_id()

    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (CREATE) on atlas.policy.commands topic
    job_payload = initial_onprem_scheduler_test_setup(
        str(uuid.uuid4()),
        OnPremProtectionJobType.VOLUME_PROTECTION_GROUP_PROT_JOB.value,
        ProtectionType.SNAPSHOT.value,
    )
    json_object = json.loads(job_payload)
    job_id = json_object.get("id", {})
    protection_job = wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
        postgres_manager,
        db_connection,
        AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE,
    )
    customer_id: str = protection_job[0].customer_id
    protection_policy_id: str = protection_job[0].policy_id

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
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
        postgres_manager,
        db_connection,
    )

    # Resume the suspended protection job schedule
    send_resume_protection_job(
        customer_id=customer_id,
        protection_policy_schedule_ids=[1],
        protection_job_id=job_id,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_ONPREM_RESUME_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
        postgres_manager,
        db_connection,
    )

    # Protection Policy Update - update schedule's repeat interval field
    repeat_interval = {"every": 5, "on": None}
    json_payload_update = get_update_protection_policy_kafka_response_object(
        protection_policy_id=protection_policy_id,
        protection_policy_name="Test",
        protection_policy_schedule_id=1,
        protection_type=ProtectionType.SNAPSHOT.value,
        recurrence="Hourly",
        repeat_interval=repeat_interval,
    )
    kafka_topic = AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value
    kafka_manager = KafkaManager(topic=kafka_topic, host=config["KAFKA"]["host"])
    send_protection_job_kafka_message(
        kafka_manager=kafka_manager,
        json_payload=json_payload_update,
        event_operation=AtlasPolicyOperations.PROTECTION_POLICY_UPDATE.value,
        event_type=AtlantiaKafkaEvents.ATLAS_POLICY_ONPREM_UPDATE_EVENT_TYPE.value,
        customer_id=customer_id,
    )
    # Get Protection Job data from db and assert with updated repeat_interval
    assert_updated_repeat_interval_with_retry(
        job_id, postgres_manager, db_connection, repeat_interval, max_retries=2, delay=5
    )

    # Delete VPG Protection Job
    send_delete_protection_job(
        context=context,
        customer_id=customer_id,
        csp_asset_id="",
        asset_type=OnPremProtectionJobType.VOLUME_PROTECTION_GROUP_PROT_JOB.value,
        protection_job_id=job_id,
        protection_policy_id=protection_policy_id,
        wait_for_complete=False,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_DELETE_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
        postgres_manager,
        db_connection,
    )


@mark.xfail
@mark.csp_scheduler_localstack
@pytestrail.case("C57583458")
def test_protection_jobs_onprem_vpg_with_prepost_scripts(
    context: Context, dbase_connection: tuple[any, PostgresManager]
):
    """
    This method will check the Protection Job Create functionality of Volume Protection Group with Pre-Post Scripts
    Create -> Suspend -> Resume -> Update -> Delete
    """
    db_connection, postgres_manager = dbase_connection
    customer_id: str = context.get_customer_id()

    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (CREATE) on atlas.policy.commands topic
    job_payload = initial_onprem_scheduler_test_setup_with_prepost_scripts(
        str(uuid.uuid4()),
        OnPremProtectionJobType.VOLUME_PROTECTION_GROUP_PROT_JOB.value,
        ProtectionType.SNAPSHOT.value,
    )
    json_object = json.loads(job_payload)
    job_id = json_object.get("id", {})
    protection_job = wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
        postgres_manager,
        db_connection,
        AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE,
    )
    customer_id: str = protection_job[0].customer_id
    protection_policy_id: str = protection_job[0].policy_id

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
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
        postgres_manager,
        db_connection,
    )

    # Resume the suspended protection job schedule
    send_resume_protection_job(
        customer_id=customer_id,
        protection_policy_schedule_ids=[1],
        protection_job_id=job_id,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_ONPREM_RESUME_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
        postgres_manager,
        db_connection,
    )

    # Protection Policy Update - update schedule's repeat interval field
    repeat_interval = {"every": 5, "on": None}
    json_payload_update = get_update_protection_policy_kafka_response_object(
        protection_policy_id=protection_policy_id,
        protection_policy_name="Test",
        protection_policy_schedule_id=1,
        protection_type=ProtectionType.SNAPSHOT.value,
        recurrence="Hourly",
        repeat_interval=repeat_interval,
    )
    kafka_topic = AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value
    kafka_manager = KafkaManager(topic=kafka_topic, host=config["KAFKA"]["host"])
    send_protection_job_kafka_message(
        kafka_manager=kafka_manager,
        json_payload=json_payload_update,
        event_operation=AtlasPolicyOperations.PROTECTION_POLICY_UPDATE.value,
        event_type=AtlantiaKafkaEvents.ATLAS_POLICY_ONPREM_UPDATE_EVENT_TYPE.value,
        customer_id=customer_id,
    )
    # Get Protection Job data from db and assert with updated repeat_interval
    assert_updated_repeat_interval_with_retry(
        job_id, postgres_manager, db_connection, repeat_interval, max_retries=2, delay=5
    )

    # Delete VPG Protection Job
    send_delete_protection_job(
        context=context,
        customer_id=customer_id,
        csp_asset_id="",
        asset_type=OnPremProtectionJobType.VOLUME_PROTECTION_GROUP_PROT_JOB.value,
        protection_job_id=job_id,
        protection_policy_id=protection_policy_id,
        wait_for_complete=False,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_DELETE_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
        postgres_manager,
        db_connection,
    )


@mark.xfail
@mark.csp_scheduler_localstack
@pytestrail.case("C57583456")
def test_protection_jobs_onprem_mssql(context: Context, dbase_connection: tuple[any, PostgresManager]):
    """
    This method will check the MSSQL Protection Job Create functionality of Volume Protection Group
    Create -> Suspend -> Resume -> Update
    """
    db_connection, postgres_manager = dbase_connection
    customer_id: str = context.get_customer_id()

    # Creating JSON Payload for Kafka and
    # Producing Kafka Message (CREATE) on atlas.policy.commands topic
    job_payload = initial_onprem_scheduler_test_setup(
        str(uuid.uuid4()),
        OnPremProtectionJobType.MSSQL_DATABASE_PROTECTION_GROUP.value,
        ProtectionType.SNAPSHOT.value,
    )
    json_object = json.loads(job_payload)
    job_id = json_object.get("id", {})
    protection_job = wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
        postgres_manager,
        db_connection,
        AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE,
    )
    customer_id: str = protection_job[0].customer_id
    protection_policy_id: str = protection_job[0].policy_id

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
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
        postgres_manager,
        db_connection,
    )

    # Resume the suspended protection job schedule
    send_resume_protection_job(
        customer_id=customer_id,
        protection_policy_schedule_ids=[1],
        protection_job_id=job_id,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_ONPREM_RESUME_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
        postgres_manager,
        db_connection,
    )

    # Protection Policy Update - update schedule's repeat interval field
    repeat_interval = {"every": 5, "on": None}
    json_payload_update = get_update_protection_policy_kafka_response_object(
        protection_policy_id=protection_policy_id,
        protection_policy_name="Test",
        protection_policy_schedule_id=1,
        protection_type=ProtectionType.SNAPSHOT.value,
        recurrence="Hourly",
        repeat_interval=repeat_interval,
    )
    kafka_topic = AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value
    kafka_manager = KafkaManager(topic=kafka_topic, host=config["KAFKA"]["host"])
    send_protection_job_kafka_message(
        kafka_manager=kafka_manager,
        json_payload=json_payload_update,
        event_operation=AtlasPolicyOperations.PROTECTION_POLICY_UPDATE.value,
        event_type=AtlantiaKafkaEvents.ATLAS_POLICY_ONPREM_UPDATE_EVENT_TYPE.value,
        customer_id=customer_id,
    )
    # Get Protection Job data from db and assert with updated repeat_interval
    assert_updated_repeat_interval_with_retry(
        job_id, postgres_manager, db_connection, repeat_interval, max_retries=2, delay=5
    )

    # Delete MSSQL Database Protection Job
    send_delete_protection_job(
        context=context,
        customer_id=customer_id,
        csp_asset_id="",
        asset_type=OnPremProtectionJobType.MSSQL_DATABASE_PROTECTION_GROUP.value,
        protection_job_id=job_id,
        protection_policy_id=protection_policy_id,
        wait_for_complete=False,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
        ce_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_DELETE_EVENT_TYPE.value,
        kafka_topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
    )
    wait_and_validate_protection_job(
        customer_id,
        job_id,
        AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
        postgres_manager,
        db_connection,
    )
