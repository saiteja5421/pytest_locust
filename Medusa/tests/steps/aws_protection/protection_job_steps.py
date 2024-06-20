from xmlrpc.client import Boolean
import uuid
import time
import logging
import base64
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.common.enums.atlas_policy_operations import AtlasPolicyOperations
from lib.common.config.config_manager import ConfigManager
from lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_jobs import (
    ProtectionJobList,
)
import lib.platform.kafka.protobuf.atlas_policy_manager.atlas_policy_command_request_pb2 as atlas_policy_cmd_req_pb2
import lib.platform.kafka.protobuf.cloud_account_manager.account_pb2 as account_pb2
from lib.platform.kafka.kafka_manager import KafkaManager
import lib.platform.kafka.protobuf.inventory_manager.asset_pb2 as asset_pb2
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ActiveTime,
    NamePattern,
    ObjectUnitValue,
    Schedule,
    RepeatInterval,
    AssetInfo,
    PreScriptInfo,
    PostScriptInfo,
)
from lib.dscc.backup_recovery.protection_policies.models.protection_job_kafka_response import (
    ProtectionJobKafkaResponse,
    ProtectionKafkaResponse,
    ProtectionPolicyKafkaResponse,
)

# Kafka uses the v1 REST encodings for PolicySchedule. Used in function "create_protection_job_kafka_response_object()"
from lib.dscc.backup_recovery.protection_policies.models.protection_policies import (
    PolicySchedule,
)
import json
from lib.common.enums.protection_types import ProtectionType
from lib.common.enums.csp_protection_job_type import CSPProtectionJobType
from lib.common.enums.object_unit_type import ObjectUnitType
from datetime import timedelta, date

from typing import Union
from waiting import wait, TimeoutExpired

from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.common_steps import get_kafka_headers
from lib.platform.postgres.postgres_manager import PostgresManager

from tests.steps.aws_protection.inventory_manager_steps import (
    get_csp_instance_by_id,
    get_csp_volume_by_id,
    get_protection_group_protection_jobs,
)
from lib.dscc.backup_recovery.aws_protection.scheduler.scheduler_models import (
    InitiateBackupRequest,
)
from tests.steps.aws_protection.inventory_manager.kafka_steps import (
    wait_for_event,
)


config = ConfigManager.get_config()
logger = logging.getLogger()


class KafkaProtectionJob:
    """This class is to hold Kafka protection job notification data and exposes methods to send Kafka updates.
    This class can be in functional test cases where actual backup services are not available.
    """

    def __init__(
        self,
        context: Context,
        customer_id: str,
        csp_asset_id: str,
        asset_type: CSPProtectionJobType,
        protection_type: ProtectionType,
        policy_schedule_id: Union[int, list[int]] = 1,
    ):
        self._context = context
        self._customer_id = customer_id
        self._csp_asset_id = csp_asset_id
        self._asset_type = asset_type
        self._protection_type = protection_type
        self._protection_job_id = str(uuid.uuid4())
        self._protection_policy_id = str(uuid.uuid4())
        self._protection_policy_schedule_ids = policy_schedule_id
        if type(policy_schedule_id) == int:
            self._protection_policy_schedule_ids = [policy_schedule_id]

    def get_schedule_id(self) -> int:
        """Returns only the ID of the first schedule in the protection job

        Returns:
            int: first schedule id
        """
        return self._protection_policy_schedule_ids[0]

    def get_protection_job_id(self) -> str:
        """Returns protection job id

        Returns:
            str: protection job id
        """
        return self._protection_job_id

    def get_protection_policy_id(self):
        """Returns Protection Policy id

        Returns:
            str: Protection Policy id
        """
        return self._protection_policy_id

    def create(self, wait_for_complete: bool = True, number_of_expected_jobs: int = 1):
        """Create Protection job

        Args:
            wait_for_complete (bool, optional): Waits for job to be created. Defaults to True.
            number_of_expected_jobs (int, optional): Number of jobs to be created. Defaults to 1.
        """
        send_create_protection_job(
            context=self._context,
            customer_id=self._customer_id,
            csp_asset_id=self._csp_asset_id,
            asset_type=self._asset_type.value,
            protection_type=self._protection_type.value,
            protection_policy_schedule_id=self._protection_policy_schedule_ids,
            protection_job_id=self._protection_job_id,
            protection_policy_id=self._protection_policy_id,
            number_of_expected_jobs=number_of_expected_jobs,
            wait_for_complete=wait_for_complete,
        )

    def delete(self, wait_for_complete: bool = True, number_of_expected_jobs: int = 0):
        """Delete Protection job

        Args:
            wait_for_complete (bool, optional): Wait for job to be deleted. Defaults to True.
            number_of_expected_jobs (int, optional): Number of jobs to be deleted. Defaults to 0.
        """
        send_delete_protection_job(
            context=self._context,
            customer_id=self._customer_id,
            csp_asset_id=self._csp_asset_id,
            asset_type=self._asset_type.value,
            protection_job_id=self._protection_job_id,
            protection_policy_id=self._protection_policy_id,
            number_of_expected_jobs=number_of_expected_jobs,
            wait_for_complete=wait_for_complete,
        )

    def suspend(self):
        """Suspend the Protection job"""
        send_suspend_protection_job(
            customer_id=self._customer_id,
            protection_policy_schedule_ids=self._protection_policy_schedule_ids,
            protection_job_id=self._protection_job_id,
        )

    def resume(self):
        """Resume the Protection job"""
        send_resume_protection_job(
            customer_id=self._customer_id,
            protection_policy_schedule_ids=self._protection_policy_schedule_ids,
            protection_job_id=self._protection_job_id,
        )

    def wait_for_jobs_count(self, job_count: int):
        """Wait for the Protection job count for an asset

        Args:
            job_count (int): number of jobs
        """

        def _wait_for_protection_job_count():
            count = get_asset_protection_job_count(
                context=self._context,
                csp_asset_id=self._csp_asset_id,
                asset_type=self._asset_type.value,
            )
            return job_count == count

        # wait for PG job creation
        wait(_wait_for_protection_job_count, timeout_seconds=180, sleep_seconds=0.5)


def send_create_protection_job(
    context: Context,
    csp_asset_id: str,
    asset_type: str,
    customer_id: str,
    protection_job_id: str,
    protection_policy_id: str,
    protection_type: str = ProtectionType.CLOUD_BACKUP.value,
    protection_policy_schedule_id: Union[int, list[int]] = 1,
    wait_for_complete: Boolean = True,
    topic: str = AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value,
    number_of_expected_jobs: int = 1,
):
    """
    This method will send a kafka message in regards to protection jobs. The method currently caters to
    Inventory Manager requirements and defaults to CSP_SCHEDULER_UPDATES topic. If this method needs to be extended
    for Scheduler microservice the topic parameter needs to be overridden to ATLAS_POLICY_COMMANDS along with ce_type.
    This method will wait for the job to complete.

    Args:
        context (Context): test Context
        csp_asset_id (str):
            For ec2/volume assets, CSP maintained asset id must be passed
            For CSP Protection Group, Protection group job id must be passed
        asset_type (str): csp asset type
        customer_id (str): customer id
        protection_job_id (str): protection job id
        protection_policy_id (str): protection policy id
        protection_type (str, optional): protection type. Defaults to ProtectionType.CLOUD_BACKUP.value.
        protection_policy_schedule_id (Union[int, list[int]], optional): protection policy schedule id. Defaults to 1.
        wait_for_complete (Boolean, optional): wait for job to be created. Defaults to True.
        topic (str, optional): Policy commands topic. Defaults to AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value.
        number_of_expected_jobs (int, optional): number of jobs to be created. Defaults to 1.
    """

    # Initialize Kafka Manager for policy commands topic
    kafka_manager = KafkaManager(topic=topic, host=config["KAFKA"]["host"])
    json_payload = create_protection_job_kafka_response_object(
        asset_id=csp_asset_id,
        asset_type=asset_type,
        protection_type=protection_type,
        protection_job_id=protection_job_id,
        protection_policy_id=protection_policy_id,
        protection_policy_schedule_id=protection_policy_schedule_id,
    )
    _submit_asset_state_payload(
        kafka_manager=kafka_manager,
        customer_id=customer_id,
        json_payload=json_payload,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
        ce_type=AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE.value,
    )

    if wait_for_complete:
        _wait_for_protection_job(
            context=context,
            kafka_manager=kafka_manager,
            csp_asset_id=csp_asset_id,
            asset_type=asset_type,
            expected_job_count=number_of_expected_jobs,
        )


def send_delete_protection_job(
    context: Context,
    customer_id: str,
    csp_asset_id: str,
    asset_type: str,
    protection_job_id: str,
    protection_policy_id: str,
    number_of_expected_jobs: int = 0,
    wait_for_complete: Boolean = True,
    event_operation: str = AtlasPolicyOperations.PROTECTION_JOB_DELETE.value,
    ce_type: str = AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_DELETE_EVENT_TYPE.value,
    kafka_topic: str = AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value,
):
    """
    This method will send a kafka message in regards to delete protection jobs.
    This method will wait for the job to complete.

    Args:
        context (Context): test context
        customer_id (str): customer id
        csp_asset_id (str):
            For ec2/volume assets, CSP maintained asset id must be passed
            For CSP protection group, Protection group job id must be passed
        asset_type (str): asset type
        protection_job_id (str): protection job id
        protection_policy_id (str): protection policy id
        number_of_expected_jobs (int, optional): Number of jobs to delete. Defaults to 0.
        wait_for_complete (Boolean, optional): Waits for jobs to be deleted. Defaults to True.
        event_operation (str, optional): Event Operation. Defaults to AtlasPolicyOperations.PROTECTION_JOB_DELETE.value.
        ce_type (str, optional): Event Type. Defaults to AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_DELETE_EVENT_TYPE.value.
        kafka_topic (str, optional): Policy commands topic. Defaults to AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value.
    """
    # Initialize Kafka Manager for policy commands topic
    kafka_manager = KafkaManager(topic=kafka_topic, host=config["KAFKA"]["host"])
    json_payload = create_protection_job_delete_kafka_response_object(
        protection_job_id=protection_job_id,
        protection_policy_id=protection_policy_id,
    )
    _submit_asset_state_payload(
        kafka_manager=kafka_manager,
        customer_id=customer_id,
        json_payload=json_payload,
        event_operation=event_operation,
        ce_type=ce_type,
    )

    if wait_for_complete:
        _wait_for_protection_job(
            context=context,
            kafka_manager=kafka_manager,
            csp_asset_id=csp_asset_id,
            asset_type=asset_type,
            expected_job_count=number_of_expected_jobs,
        )


def _submit_asset_state_payload(
    kafka_manager: KafkaManager,
    customer_id: str,
    json_payload: str,
    event_operation: str,
    ce_type: str,
):
    """Creates event and send Kafka message

    Args:
        kafka_manager (KafkaManager): Kafka Manager object
        customer_id (str): Customer id
        json_payload (str): Event payload
        event_operation (str): Event Operation
        ce_type (str): Event type
    """
    requested_event = atlas_policy_cmd_req_pb2.AtlasPolicyCommandRequest()
    requested_event.operation = atlas_policy_cmd_req_pb2._ATLASPOLICYCOMMANDREQUEST_OPERATION.values_by_name[
        event_operation
    ].number
    requested_event.mime_type = "application/json"
    requested_event.payload = json_payload.encode("utf-8")

    kafka_headers = get_kafka_headers(
        kafka_manager=kafka_manager,
        ce_type=ce_type,
        customer_id=customer_id,
    )
    kafka_manager.send_message(event=requested_event, user_headers=kafka_headers, partition=0)


def get_asset_protection_job_count(context: Context, csp_asset_id: str, asset_type: str) -> int:
    """Returns number of protection jobs for an asset

    Args:
        context (Context): test Context
        csp_asset_id (str): CSP asset id
        asset_type (str): Asset type. Can be protection group, csp instance, or csp volume

    Returns:
        int: Number of protection jobs for given asset. If -1, no protection jobs were found.
    """
    if asset_type == CSPProtectionJobType.CSP_PROTECTION_GROUP_PROT_JOB.value:
        asset_jobs = get_protection_group_protection_jobs(context=context, protection_group_id=csp_asset_id)
        return -1 if asset_jobs is None else len(asset_jobs)
    elif asset_type == CSPProtectionJobType.CSP_VOLUME_PROT_JOB.value:
        csp_volume = get_csp_volume_by_id(context=context, csp_volume_id=csp_asset_id)
        return -1 if csp_volume is None else len(csp_volume.protectionJobInfo)
    elif asset_type == CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB.value:
        ec2_instance = get_csp_instance_by_id(context=context, csp_machine_id=csp_asset_id)
        return -1 if ec2_instance is None else len(ec2_instance.protectionJobInfo)


def _wait_for_protection_job(
    context: Context,
    kafka_manager: KafkaManager,
    csp_asset_id: str,
    asset_type: str,
    expected_job_count: int,
):
    """Waits for protection job

    Args:
        context (Context): the test context
        kafka_manager (KafkaManager): Kafka Manager object
        csp_asset_id (str): Asset id
        asset_type (str): Asset type. Can be protection group, csp instance, or csp volume
        expected_job_count (int): Number of expected jobs
    """
    end_offset = -1

    def _wait_for_message_consume():
        current_offset, current_offset_end = kafka_manager.consumer_group_offset("csp_inventory", 0)
        return current_offset >= end_offset

    def _wait_for_protection_job_count():
        job_count = get_asset_protection_job_count(context=context, csp_asset_id=csp_asset_id, asset_type=asset_type)
        return expected_job_count == job_count

    offset, end_offset = kafka_manager.consumer_group_offset("csp_inventory", 0)

    # wait for Kafka message processing
    wait(_wait_for_message_consume, timeout_seconds=120, sleep_seconds=1)

    # wait for PG job creation
    wait(_wait_for_protection_job_count, timeout_seconds=180, sleep_seconds=0.5)


def send_protection_job_kafka_message(
    kafka_manager: KafkaManager,
    json_payload: str,
    event_operation: str = AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
    event_type: str = AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE.value,
    customer_id: str = "8922afa6723011ebbe01ca32d32b6b77",
):
    """
    This method will send a kafka message in regards to protection jobs.
    Most of the values for now are hardcoded as they don't need to be modified for our testing.
    We will modify this method in the future to accept more parameters if needed.

    Args:
        kafka_manager (KafkaManager): Kafka manager object
        json_payload (str): Event payload
        event_operation (str, optional): Event Operation. Defaults to AtlasPolicyOperations.PROTECTION_JOB_CREATE.value.
        event_type (str, optional): Event Type. Defaults to AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE.value.
        customer_id (str, optional): Customer ID. Defaults to "8922afa6723011ebbe01ca32d32b6b77".
    """
    requested_event = atlas_policy_cmd_req_pb2.AtlasPolicyCommandRequest()
    requested_event.operation = atlas_policy_cmd_req_pb2._ATLASPOLICYCOMMANDREQUEST_OPERATION.values_by_name[
        event_operation
    ].number
    requested_event.mime_type = "application/json"
    requested_event.payload = json_payload.encode("utf-8")

    kafka_headers = get_kafka_headers(kafka_manager=kafka_manager, ce_type=event_type, customer_id=customer_id)

    kafka_manager.send_message(event=requested_event, user_headers=kafka_headers)

    def _wait_for_message_consume():
        current_offset, current_offset_end = kafka_manager.consumer_group_offset("csp_inventory", 0)
        return current_offset >= end_offset

    offset, end_offset = kafka_manager.consumer_group_offset("csp_inventory", 0)
    # wait for Kafka message processing
    wait(_wait_for_message_consume, timeout_seconds=120, sleep_seconds=1)


def create_protection_job_delete_kafka_response_object(protection_job_id: str, protection_policy_id: str) -> str:
    """
    This method will return a ProtectionJobKafkaResponse json object to delete a protection job.
    Most of the values for now are hardcoded as they don't need to be modified for our testing.
    We will modify this method in the future to accept more parameters if needed.

    Args:
        protection_job_id (str): Protection job id
        protection_policy_id (str): Protection policy id

    Returns:
        str: json object for deleting the protection job
    """
    protection_job_dict = {
        "id": protection_job_id,
        "protectionPolicyId": protection_policy_id,
    }
    json_data = json.dumps(protection_job_dict)
    return json_data


def create_protection_job_run_kafka_response_object(
    protection_policy_schedule_ids: list[str], protection_job_id: str
) -> str:
    """
    This method will return a ProtectionJobKafkaResponse json object to run protection jobs.
    Most of the values for now are hardcoded as they don't need to be modified for our testing.
    We will modify this method in the future to accept more parameters if needed.

    Args:
        protection_policy_schedule_ids (list[str]): Schedule id
        protection_job_id (str): Protection job id

    Returns:
        str: json object to run the protection job
    """
    protection_job_dict = {
        "scheduleIds": protection_policy_schedule_ids,
        "id": protection_job_id,
    }
    json_data = json.dumps(protection_job_dict)
    return json_data


def create_asset_state_object(protection_policy_schedule_ids: list[int], protection_job_id: str) -> str:
    """
    This method will return a ProtectionJobKafkaResponse json object to suspend/resume protection jobs.
    Most of the values for now are hardcoded as they don't need to be modified for our testing.
    We will modify this method in the future to accept more parameters if needed.

    Args:
        protection_policy_schedule_ids (list[int]): Schedule id
        protection_job_id (str): Protection job id

    Returns:
        str: json object to suspend/resume the protection job
    """
    protection_job_dict = {
        "scheduleIds": protection_policy_schedule_ids,
        "id": protection_job_id,
    }
    json_data = json.dumps(protection_job_dict)
    return json_data


def update_protection_policy_kafka_response_object(
    protection_policy_id: str = "60000000-0000-0000-0000-000000000001",
    protection_policy_name: str = "Test",
) -> str:
    """This method will return a ProtectionPolicyKafkaResponse json object.

    Args:
        protection_policy_id (str, optional): Protection policy id. Defaults to "60000000-0000-0000-0000-000000000001".
        protection_policy_name (str, optional): Protection policy name. Defaults to "Test".

    Returns:
        str: json object for updating protection policy
    """
    protection_policy = ProtectionPolicyKafkaResponse(
        name=protection_policy_name, id=protection_policy_id, protections=None
    )
    json_payload = protection_policy.to_json()
    return json_payload


def create_protection_job_kafka_response_object(
    asset_id: str,
    asset_type: str,
    protection_type: str = ProtectionType.CLOUD_BACKUP.value,
    protection_job_id: str = "50000000-0000-0000-0000-000000000001",
    protection_policy_id: str = "60000000-0000-0000-0000-000000000001",
    protection_policy_name: str = "Test",
    protection_policy_schedule_id: Union[int, list[int]] = 1,
    csp_type: str = "AWS",
) -> str:
    """
    This method will return a ProtectionJobKafkaResponse json object.
    Most of the values for now are hardcoded as they don't need to be modified for our testing.
    We will modify this method in the future to accept more parameters if needed.

    The protection_policy_schedule_id argument can be a simple integer or a list of integers.
    The protection job contains a separate schedule for each integer provided.

    Args:
        asset_id (str): asset id
        asset_type (str): asset type
        protection_type (str, optional): Protection type. Defaults to ProtectionType.CLOUD_BACKUP.value.
        protection_job_id (str, optional): Protection job id. Defaults to "50000000-0000-0000-0000-000000000001".
        protection_policy_id (str, optional): Protection policy id. Defaults to "60000000-0000-0000-0000-000000000001".
        protection_policy_name (str, optional): Protection policy name. Defaults to "Test".
        protection_policy_schedule_id (Union[int, list[int]], optional): Schedule id. Defaults to 1.

    Returns:
        str: json object for creating protection job
    """
    expire_after = ObjectUnitValue(unit=ObjectUnitType.HOURS.value, value=1)
    lock_for = ObjectUnitValue(unit=ObjectUnitType.HOURS.value, value=1)
    name_pattern = NamePattern(format="Backup_Name")
    active_time = ActiveTime(active_from_time="08:00", active_until_time="23:30")
    repeat_interval = RepeatInterval(every=1, on=[2, 3])
    schedule = Schedule(
        activeTime=active_time,
        recurrence="Hourly",
        repeatInterval=repeat_interval,
        startTime="00:00",
    )

    if type(protection_policy_schedule_id) == int:
        protection_policy_schedule_id = [protection_policy_schedule_id]
    policy_schedules = []
    for schedule_id in protection_policy_schedule_id:
        policy_schedules.append(
            PolicySchedule(
                id=schedule_id,
                name=protection_type,
                schedule=schedule,
                expire_after=expire_after,
                name_pattern=name_pattern,
                source_protection_schedule_id=1,
                lock_for=lock_for,
            )
        )
    protections = ProtectionKafkaResponse(
        id="740b1aa0-b57a-4500-aa77-600e28a7db0d",
        type=protection_type,
        schedules=policy_schedules,
    )

    protection_policy = ProtectionPolicyKafkaResponse(
        name=protection_policy_name, id=protection_policy_id, protections=[protections]
    )

    asset_info = AssetInfo(id=asset_id, name=protection_policy_name, type=asset_type, cspType=csp_type)
    effectiveDate = date.today() + timedelta(days=1)
    effectiveDate.isoformat()

    protection_job = ProtectionJobKafkaResponse(
        id=protection_job_id,
        asset_info=asset_info,
        protection_policy=protection_policy,
    )
    json_payload = protection_job.to_json()
    return json_payload


def create_onprem_protection_job_kafka_response_object(
    asset_id: str,
    asset_type: str,
    protection_type: str,
    protection_job_id: str = "50000000-0000-0000-0000-000000000001",
    protection_policy_id: str = "60000000-0000-0000-0000-000000000001",
    protection_policy_name: str = "Test",
    protection_policy_schedule_id: Union[int, list[int]] = 1,
) -> str:
    """
    This method will return a ProtectionJobKafkaResponse json object.
    Most of the values for now are hardcoded as they don't need to be modified for our testing.
    We will modify this method in the future to accept more parameters if needed.

    The protection_policy_schedule_id argument can be a simple integer or a list of integers.
    The protection job contains a separate schedule for each integer provided.

    Args:
        asset_id (str): asset id
        asset_type (str): asset type
        protection_type (str, optional): Protection type. Defaults to ProtectionType.CLOUD_BACKUP.value.
        protection_job_id (str, optional): Protection job id. Defaults to "50000000-0000-0000-0000-000000000001".
        protection_policy_id (str, optional): Protection policy id. Defaults to "60000000-0000-0000-0000-000000000001".
        protection_policy_name (str, optional): Protection policy name. Defaults to "Test".
        protection_policy_schedule_id (Union[int, list[int]], optional): Schedule id. Defaults to 1.

    Returns:
        str: json object for creating protection job
    """
    expire_after = ObjectUnitValue(unit=ObjectUnitType.HOURS.value, value=1)
    lock_for = ObjectUnitValue(unit=ObjectUnitType.HOURS.value, value=1)
    name_pattern = NamePattern(format="Backup_Name")
    active_time = ActiveTime(active_from_time="08:00", active_until_time="23:30")
    repeat_interval = RepeatInterval(every=1, on=[2, 3])
    schedule = Schedule(
        activeTime=active_time,
        recurrence="Hourly",
        repeatInterval=repeat_interval,
        startTime="00:00",
    )
    prescript_info = PreScriptInfo(
        hostId="123",
        params="params",
        path="/local",
        timeout_in_seconds=2,
    )
    postscript_info = PostScriptInfo(
        hostId="123",
        params="params",
        path="/local",
        timeout_in_seconds=2,
    )

    if type(protection_policy_schedule_id) == int:
        protection_policy_schedule_id = [protection_policy_schedule_id]
    policy_schedules = []
    for schedule_id in protection_policy_schedule_id:
        policy_schedules.append(
            PolicySchedule(
                id=schedule_id,
                name=protection_type,
                schedule=schedule,
                expire_after=expire_after,
                name_pattern=name_pattern,
                source_protection_schedule_id=1,
                lock_for=lock_for,
                pre_script_info=prescript_info,
                post_script_info=postscript_info,
            )
        )
    protections = ProtectionKafkaResponse(
        id="740b1aa0-b57a-4500-aa77-600e28a7db0d",
        type=protection_type,
        schedules=policy_schedules,
    )

    protection_policy = ProtectionPolicyKafkaResponse(
        name=protection_policy_name, id=protection_policy_id, protections=[protections]
    )

    asset_info = AssetInfo(id=asset_id, name=protection_policy_name, type=asset_type)
    effectiveDate = date.today() + timedelta(days=1)
    effectiveDate.isoformat()

    protection_job = ProtectionJobKafkaResponse(
        id=protection_job_id,
        asset_info=asset_info,
        protection_policy=protection_policy,
    )
    json_payload = protection_job.to_json()
    return json_payload


def create_test_csp_account(
    account_id: str = "00000000-0000-0000-0000-000000000001",
    status=1,
    suspended: bool = False,
) -> account_pb2.CspAccountInfo:
    """Creates a test CSP account

    Args:
        account_id (str, optional): CSP Account id. Defaults to "00000000-0000-0000-0000-000000000001".
        status (int, optional): CSP Account Status. Defaults to 1.
        suspended (bool, optional): True if the account is suspended. Defaults to False.

    Returns:
        account_pb2.CspAccountInfo: CSP Account
    """
    csp_account = account_pb2.CspAccountInfo()
    csp_account.id = account_id
    csp_account.name = "test-account"
    csp_account.service_provider_id = "arn:aws:iam::681961981209"
    csp_account.status = status
    csp_account.type = 1
    csp_account.validation_status = 2
    csp_account.paused = suspended

    return csp_account


def send_customer_account_kafka_message(
    event_type: str = AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value,
    account_id: str = "00000000-0000-0000-0000-000000000001",
    customer_id: str = "8922afa6723011ebbe01ca32d32b6b77",
    status=1,
    suspended: bool = False,
):
    """This method will send a kafka message in regards to customer account register/suspend/resume/unregister.

    Args:
        event_type (str, optional): Event type. Defaults to AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value.
        account_id (str, optional): Account id. Defaults to "00000000-0000-0000-0000-000000000001".
        customer_id (str, optional): Customer id. Defaults to "8922afa6723011ebbe01ca32d32b6b77".
        status (int, optional): Account status. Defaults to 1.
        suspended (bool, optional): True if the account is suspended. Defaults to False.
    """
    requested_event = create_test_csp_account(account_id, status, suspended)
    kafka_manager = KafkaManager(topic=AtlantiaKafkaTopics.CSP_CAM_UPDATES.value, host=config["KAFKA"]["host"])
    kafka_headers = get_kafka_headers(kafka_manager=kafka_manager, ce_type=event_type, customer_id=customer_id)
    # Temporary fix for setting the customer id parameter as the key, the key is being auto generated in kafka_manager
    s = customer_id
    b = bytearray()
    b.extend(map(ord, s))
    kafka_manager.account_id = b
    kafka_manager.send_message(event=requested_event, user_headers=kafka_headers)


def run_all_protection_policy_protection_jobs_schedules_and_return_task_id_list(
    context: Context, protection_policy_id: str
) -> list[str]:
    """Retrieves all the associated protections jobs using protection_policy_id and runs all the schedules

    Args:
        context (Context): context object
        protection_policy_id (str): Protection Policy ID for which all the schedules need to be run

    Returns:
        list[str]: List of tasks which got generated by running the Protection Job Schedules
    """
    protection_jobs: ProtectionJobList = context.policy_manager.get_protection_jobs_by_protection_policy_id(
        protection_policy_id=protection_policy_id
    )

    # Run jobs, save task_id to list, and then loop through waiting for tasks to complete
    task_ids: list[str] = []

    for protection_job in protection_jobs.items:
        job_id = protection_job.id
        schedule_ids: list[int] = []
        for protection in protection_job.protections:
            for schedule in protection.schedules:
                schedule_ids.append(schedule.id)
        task_ids.append(
            context.policy_manager.run_protection_job(protection_job_id=job_id, protection_schedule_ids=schedule_ids)
        )

    return task_ids


def send_suspend_protection_job(
    customer_id: str,
    protection_policy_schedule_ids: list[int],
    protection_job_id: str,
    event_operation: str = AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value,
    ce_type: str = AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_SUSPEND_EVENT_TYPE.value,
    kafka_topic: str = AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value,
):
    """Publish a Kafka event to suspend one or more schedules of a protection job.

    Args:
        customer_id (str): ID of the customer
        protection_policy_schedule_ids (list[int]): List of schedule IDs to suspend
        protection_job_id (str): Protection job ID the schedule/s belong to
        event_operation (str, optional): Event operation. Defaults to AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value.
        ce_type (str, optional): Event type. Defaults to AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_SUSPEND_EVENT_TYPE.value.
        kafka_topic (str, optional): Policy commands topic. Defaults to AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value.
    """
    # Initialize Kafka Manager for policy commands topic
    kafka_manager = KafkaManager(topic=kafka_topic, host=config["KAFKA"]["host"])
    protection_job_suspend_data = create_asset_state_object(
        protection_policy_schedule_ids,
        protection_job_id,
    )
    _submit_asset_state_payload(
        kafka_manager=kafka_manager,
        customer_id=customer_id,
        json_payload=protection_job_suspend_data,
        event_operation=event_operation,
        ce_type=ce_type,
    )


def send_resume_protection_job(
    customer_id: str,
    protection_policy_schedule_ids: list[int],
    protection_job_id: str,
    event_operation: str = AtlasPolicyOperations.PROTECTION_JOB_RESUME.value,
    ce_type: str = AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_RESUME_EVENT_TYPE.value,
    kafka_topic: str = AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value,
):
    """Publish a Kafka event to resume one or more schedules of a protection job.

    Args:
        customer_id (str): ID of the customer
        protection_policy_schedule_ids (list[int]): List of schedule IDs to resume
        protection_job_id (str): Protection job ID the schedule/s belong to
        event_operation (str, optional): Event Operation. Defaults to AtlasPolicyOperations.PROTECTION_JOB_RESUME.value.
        ce_type (str, optional): Event type. Defaults to AtlantiaKafkaEvents.SCHEDULER_PROTECTION_JOB_RESUME_EVENT_TYPE.value.
        kafka_topic (str, optional): Policy commands topic. Defaults to AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value.
    """
    # Initialize Kafka Manager for policy commands topic
    kafka_manager = KafkaManager(topic=kafka_topic, host=config["KAFKA"]["host"])
    protection_job_resume_data = create_asset_state_object(
        protection_policy_schedule_ids,
        protection_job_id,
    )
    _submit_asset_state_payload(
        kafka_manager=kafka_manager,
        customer_id=customer_id,
        json_payload=protection_job_resume_data,
        event_operation=event_operation,
        ce_type=ce_type,
    )


def send_run_protection_job(
    customer_id: str,
    protection_policy_schedule_ids: list[int],
    protection_job_id: str,
    event_operation: str = AtlasPolicyOperations.PROTECTION_JOB_RUN.value,
    ce_type: str = AtlantiaKafkaEvents.ATLAS_POLICY_JOB_RUN_EVENT_TYPE.value,
    kafka_topic: str = AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value,
) -> str:
    """Publish a Kafka event to resume one or more schedules of a protection job.

    Args:
        customer_id (str): ID of the customer
        protection_policy_schedule_ids (list[int]): List of schedule IDs to resume
        protection_job_id (str): Protection job ID the schedule/s belong to
        event_operation (str, optional): Event Operation. Defaults to AtlasPolicyOperations.PROTECTION_JOB_RUN.value.
        ce_type (str, optional): Event type. Defaults to AtlantiaKafkaEvents.ATLAS_POLICY_JOB_RUN_EVENT_TYPE.value.
        kafka_topic (str, optional): Policy commands topic. Defaults to AtlantiaKafkaTopics.CSP_SCHEDULER_UPDATES.value.

    Returns:
        str: Event to resume schedule(s) for a protection job
    """
    # Initialize Kafka Manager for policy commands topic
    kafka_manager = KafkaManager(topic=kafka_topic, host=config["KAFKA"]["host"])
    protection_job_run_data = create_asset_state_object(
        protection_policy_schedule_ids,
        protection_job_id,
    )
    _submit_asset_state_payload(
        kafka_manager=kafka_manager,
        customer_id=customer_id,
        json_payload=protection_job_run_data,
        event_operation=event_operation,
        ce_type=ce_type,
    )
    return protection_job_run_data


def get_update_protection_policy_kafka_response_object(
    protection_policy_id: str,
    protection_policy_name: str,
    protection_policy_schedule_id: int,
    protection_type: str,
    recurrence: str,
    repeat_interval: dict,
):
    """
    This method will return a ProtectionPolicyKafkaResponse json object.
    """

    expire_after = {"unit": ObjectUnitType.HOURS.value, "value": 10}
    lock_for = {"unit": "Hours", "value": 10}
    active_time = {"activeFromTime": "08:00", "activeUntilTime": "23:30"}
    schedule = {
        "activeTime": active_time,
        "recurrence": recurrence,
        "repeatInterval": repeat_interval,
        "startTime": "00:10",
    }
    if type(protection_policy_schedule_id) == int:
        protection_policy_schedule_id = [protection_policy_schedule_id]
    for schedule_id in protection_policy_schedule_id:
        policy_schedules = {
            "id": schedule_id,
            "schedule": schedule,
            "expire_after": expire_after,
            "name_pattern": None,
            "lock_for": lock_for,
        }
    protections = {
        "id": "740b1aa0-b57a-4500-aa77-600e28a7db0d",
        "type": protection_type,
        "modifiedSchedules": [policy_schedules],
    }
    protection_policy = {
        "name": protection_policy_name,
        "id": protection_policy_id,
        "modifiedProtections": [protections],
    }
    json_payload = json.dumps(protection_policy)
    return json_payload


def initial_scheduler_test_setup(
    customer_id: str,
    account_id: str,
    asset_id: str,
    db_connection,
    postgres_manager: PostgresManager,
    protection_type: str = ProtectionType.BACKUP.value,
    asset_type: str = CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB.value,
) -> str:
    """
    Args:
        customer_id (str): Customer id
        account_id (str): Account id
        asset_id (str): Asset id
        db_connection (_type_): DB connection object
        postgres_manager (PostgresManager): Postgres Manager object
        protection_type (str, optional): Protection type. Defaults to ProtectionType.BACKUP.value.
        asset_type (str, optional): Asset type. Defaults to CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB.value.

    Returns:
        str: protection job payload
    """
    # Check if there is an active CSP account exists before running any protection job operations.
    # Create a new CSP account if there is none exists.
    is_account_exists = check_csp_account_active(account_id, customer_id, db_connection, postgres_manager)

    if not is_account_exists:
        send_customer_account_kafka_message(
            event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_INFO_EVENT_TYPE.value,
            account_id=account_id,
            customer_id=customer_id,
            status=1,
        )

    check_account_status(account_id, customer_id, "Registered", postgres_manager, db_connection)

    # Send a new Kafka message to Schedule a new Protection job
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
        host=config["KAFKA"]["host"],
    )
    job_id = str(uuid.uuid4())
    json_payload_ec2_1 = create_protection_job_kafka_response_object(
        asset_id=asset_id,
        asset_type=asset_type,
        protection_type=protection_type,
        protection_job_id=job_id,
    )
    send_protection_job_kafka_message(
        kafka_manager=kafka_manager,
        json_payload=json_payload_ec2_1,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
        event_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_CREATE_EVENT_TYPE.value,
    )
    return json_payload_ec2_1


def wait_and_validate_protection_job(
    customer_id: str,
    job_id: str,
    event_operation: str,
    postgres_manager: PostgresManager,
    db_connection,
    event_type: AtlantiaKafkaEvents = None,
):
    """This function validates the protection job state in Scheduler DB based on the event operation

    Args:
        customer_id (str): Customer id
        job_id (str): Protection job id
        event_operation (AtlasPolicyOperations): Protection job event
        postgres_manager (PostgresManager): Postgres Manager object
        db_connection (_type_): DB connection object
        event_type (AtlantiaKafkaEvents, optional): Event type. Defaults to None.

    Returns:
        jobs
    """

    def _wait_for_db(job_id, state):
        query: str = "SELECT * FROM protection_job_workflow WHERE job_id ='" + job_id + "'"
        results = postgres_manager.execute_query(connection=db_connection, query=query)
        if len(results) > 0:
            return results[0].orchestrator_state == state
        else:
            return False

    if (event_operation == AtlasPolicyOperations.PROTECTION_JOB_CREATE.value) or (
        event_operation == AtlasPolicyOperations.PROTECTION_JOB_RESUME.value
    ):
        try:
            wait(
                lambda: _wait_for_db(job_id, "ACTIVE"),
                timeout_seconds=180,
                sleep_seconds=(0.1, 10),
            )
            jobs = get_protection_job(job_id, postgres_manager, db_connection)
            assert len(jobs) > 0
            assert jobs[0].orchestrator_id != ""
            assert jobs[0].orchestrator_state == "ACTIVE"
        except TimeoutExpired:
            raise TimeoutError("Timeout occurred")
        # TODO - Validate a Kafka event published to csp.scheduler.updates topic to be able to consume by IM.

    elif event_operation == AtlasPolicyOperations.PROTECTION_JOB_DELETE.value:
        wait(
            lambda: _wait_for_db(job_id, "TERMINATED"),
            timeout_seconds=180,
            sleep_seconds=(0.1, 10),
        )
        jobs = get_protection_job(job_id, postgres_manager, db_connection)
        assert len(jobs) > 0
    elif event_operation == AtlasPolicyOperations.PROTECTION_JOB_SUSPEND.value:
        try:
            wait(
                lambda: _wait_for_db(job_id, "SUSPENDED"),
                timeout_seconds=180,
                sleep_seconds=(0.1, 10),
            )
            jobs = get_protection_job(job_id, postgres_manager, db_connection)
            assert len(jobs) > 0
            assert jobs[0].orchestrator_id == ""
            assert jobs[0].orchestrator_state == "SUSPENDED"
        except TimeoutExpired:
            raise TimeoutError("Timeout occurred")

    elif event_operation == AtlasPolicyOperations.PROTECTION_JOB_ACCT_SUSPEND.value:
        try:
            wait(
                lambda: _wait_for_db(job_id, "ACCNTSUSPENDED"),
                timeout_seconds=180,
                sleep_seconds=(0.1, 10),
            )
            jobs = get_protection_job(job_id, postgres_manager, db_connection)
            assert len(jobs) > 0
            assert jobs[0].orchestrator_id == ""
            assert jobs[0].orchestrator_state == "ACCNTSUSPENDED"
        except TimeoutExpired:
            raise TimeoutError("Timeout occurred")
    elif event_operation == AtlasPolicyOperations.PROTECTION_JOB_RUN.value:
        # Validate message on CSP Dataprotection Actions topic
        kafka_monitor = KafkaManager(
            topic=AtlantiaKafkaTopics.CSP_DATAPROTECTION_BACKUP_ACTIONS.value,
            host=config["KAFKA"]["host"],
            account_id=bytes(customer_id, "utf-8"),
        )
        jobs = get_protection_job(job_id, postgres_manager, db_connection)
        consumer = kafka_monitor.consumer
        for message in consumer:
            logger.debug(f"message from kafka consumer: {message}")
            # payload field from Kafka topic is in marshaled JSON string, un-marshal it before performing any assertions
            decoded = base64.b64decode(message.value["payload"], validate=False)
            # Convert decoded bytes[] to JSON String
            to_dict = json.loads(decoded)
            logger.debug(f"converted incoming message:{to_dict}")
            # Convert the JSON String to dictionary
            response: InitiateBackupRequest = InitiateBackupRequest.from_dict(to_dict)
            logger.info(f"converted response value from the Kafka message:{response}")
            scheduleID = response.protectionPolicy.protection.schedule.id
            assert response.id == job_id, "Job ID " + job_id + " do not match with the response"
            assert scheduleID == jobs[0].schedule_id, (
                "scheduleID:" + scheduleID + " do not match with the protection job value in DB"
            )

    return jobs


def get_protection_job(job_id: str, postgres_manager: PostgresManager, db_connection):
    """This function retrieves the protection job data from DB by the job ID

    Args:
        job_id (str): Protection job id
        postgres_manager (PostgresManager): Postgres manager object
        db_connection (_type_): DB connection object

    Returns:
        _type_: Query Results
    """
    query: str = "SELECT * FROM protection_job_workflow WHERE job_id ='" + job_id + "'"
    return postgres_manager.execute_query(connection=db_connection, query=query)


def check_account_status(
    csp_account_id: str, customer_id: str, event_operation: str, postgres_manager: PostgresManager, db_connection
):
    """This function validates the CSP account status in Scheduler DB based on the event operation

    Args:
        csp_account_id (str): CSP account id
        customer_id (str): Customer id
        event_operation (str): Protection job event operation
        postgres_manager (PostgresManager): Postgres Manager object
        db_connection (_type_): DB connection object
    """

    def _wait_for_db(csp_account_id, customer_id, state):
        query: str = (
            "SELECT * FROM csp_account WHERE account_id = '"
            + csp_account_id
            + "' AND customer_id = '"
            + customer_id
            + "'"
        )
        results = postgres_manager.execute_query(connection=db_connection, query=query)
        if state == "Unregistered":
            return len(results) == 0
        elif len(results) > 0:
            return results[0].account_state == state
        else:
            return False

    if event_operation == "Registered" or event_operation == "Resume":
        try:
            wait(
                lambda: _wait_for_db(csp_account_id, customer_id, "ACTIVE"),
                timeout_seconds=60,
                sleep_seconds=(0.1, 10),
            )
            accounts = get_csp_account(csp_account_id, customer_id, postgres_manager, db_connection)
            assert len(accounts) > 0
            assert accounts[0].account_state == "ACTIVE"
        except TimeoutExpired:
            raise TimeoutError("Timeout occurred")

    elif event_operation == "Suspended":
        try:
            wait(
                lambda: _wait_for_db(csp_account_id, customer_id, "SUSPENDED"),
                timeout_seconds=60,
                sleep_seconds=(0.1, 10),
            )
            accounts = get_csp_account(csp_account_id, customer_id, postgres_manager, db_connection)
            assert len(accounts) > 0
            assert accounts[0].account_state == "SUSPENDED"
        except TimeoutExpired:
            raise TimeoutError("Timeout occurred")

    elif event_operation == "Unregistered":
        try:
            wait(
                lambda: _wait_for_db(csp_account_id, customer_id, "Unregistered"),
                timeout_seconds=60,
                sleep_seconds=(0.1, 10),
            )
            accounts = get_csp_account(csp_account_id, customer_id, postgres_manager, db_connection)
            assert len(accounts) == 0
        except TimeoutExpired:
            raise TimeoutError("Timeout occurred")


def get_csp_account(csp_account_id: str, customer_id: str, postgres_manager: PostgresManager, db_connection):
    """This function returns the CSP Account from Scheduler DB

    Args:
        csp_account_id (str): CSP account id
        customer_id (str): Customer id
        postgres_manager (PostgresManager): Postgres Manager object
        db_connection (_type_): DB connection object

    Returns:
        _type_: Query results
    """
    query: str = (
        "SELECT * FROM csp_account WHERE account_id = '" + csp_account_id + "' AND customer_id = '" + customer_id + "'"
    )
    return postgres_manager.execute_query(connection=db_connection, query=query)


def wait_and_validate_protection_jobs_for_asset_deletion(
    asset_id: str, job_id: str, postgres_manager: PostgresManager, db_connection
):
    """This Function will wait and validate if the protection job is in Suspended state

    Args:
        asset_id (str): Asset id
        job_id (str): Protection job id
        postgres_manager (PostgresManager): Postgres manager object
        db_connection (_type_): DB connection object
    """

    def _wait_for_db(asset_id):
        query: str = (
            "SELECT * FROM protection_job_workflow WHERE orchestrator_state = 'SUSPENDED' AND"
            + " payload -> 'assetInfo' ->> 'id' = '"
            + asset_id
            + "' AND job_id = '"
            + job_id
            + "'"
        )
        results = postgres_manager.execute_query(connection=db_connection, query=query)
        if len(results) > 0:
            return True
        else:
            return False

    wait(
        lambda: _wait_for_db(asset_id),
        timeout_seconds=60,
        sleep_seconds=(0.1, 5),
    )

    jobs = get_protection_job(job_id, postgres_manager, db_connection)
    assert len(jobs) > 0
    assert jobs[0].orchestrator_id == "", jobs[0].orchestrator_id
    assert jobs[0].orchestrator_state == "SUSPENDED", jobs[0].orchestrator_state


def check_csp_account_active(account_id: str, customer_id: str, db_connection, postgres_manager: PostgresManager):
    """This function returns true if there is an active CSP account in Scheduler DB by Customer Id and Account ID

    Args:
        account_id (str): CSP account id
        customer_id (str): Customer id
        db_connection (_type_): DB connection object
        postgres_manager (PostgresManager): Postgres Manager object

    Returns:
        bool: True if CSP account active
    """
    query: str = (
        "SELECT * FROM csp_account WHERE account_id='"
        + account_id
        + "' AND customer_id='"
        + customer_id
        + "' AND account_state = 'ACTIVE'"
    )
    results = postgres_manager.execute_query(connection=db_connection, query=query)

    if len(results) > 0:
        return True
    else:
        return False


def create_asset_state_payload(asset_type: str, asset_id: str, state: str) -> str:
    """This method will return a Asset State json object.

    Args:
        asset_type (str): Asset type
        asset_id (str): Asset id
        state (str): Asset state

    Returns:
        str: Asset state json object
    """
    asset_dict = {"type": asset_type, "id": asset_id, "state": state}
    json_data = json.dumps(asset_dict)
    return json_data


def send_asset_state_info(
    customer_id: str,
    asset_type: str,
    asset_id: str,
    state: str,
):
    """This publishes Kafka message to csp.inventory.updates topic.
    This is used to validate the protection jobs for Deleted assets

    Args:
        customer_id (str): Customer id
        asset_type (str): Asset type
        asset_id (str): Asset id
        state (str): Asset state
    """
    # Initialize Kafka Manager for policy commands topic
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.CSP_INVENTORY_UPDATES.value,
        host=config["KAFKA"]["host"],
    )

    _submit_asset_state_event(
        asset_type,
        asset_id,
        state,
        kafka_manager=kafka_manager,
        customer_id=customer_id,
    )


def _submit_asset_state_event(
    asset_type: str,
    asset_id: str,
    state: str,
    kafka_manager: KafkaManager,
    customer_id: str,
    event_type: str = AtlantiaKafkaEvents.ASSET_STATE_INFO_EVENT_TYPE.value,
):
    """This publishes Kafka message to csp.inventory.updates topic.
    This is used to validate the protection jobs for Deleted assets

    Args:
        asset_type (str): Asset Type
        asset_id (str): Asset id
        state (str): Asset state
        kafka_manager (KafkaManager): Kafka Manager object
        customer_id (str): Customer id
        event_type (str, optional): Event type. Defaults to AtlantiaKafkaEvents.ASSET_STATE_INFO_EVENT_TYPE.value.
    """
    requested_event = asset_pb2.AssetStateInfo()
    requested_event.type = asset_type
    requested_event.id = asset_id
    requested_event.state = state

    kafka_headers = get_kafka_headers(
        kafka_manager=kafka_manager,
        ce_type=event_type,
        customer_id=customer_id,
    )
    kafka_manager.send_message(event=requested_event, user_headers=kafka_headers, partition=0)


def initial_onprem_scheduler_test_setup(
    asset_id: str,
    asset_type: str,
    protection_type: str = ProtectionType.SNAPSHOT.value,
) -> str:
    """This function will publish a Create OnPrem protection job Kafka message to atlas.policy.commands topics

    Args:
        asset_id (str): Asset id
        asset_type (str): Asset type.
        protection_type (str, optional): Protection Type. Defaults to ProtectionType.SNAPSHOT.value.


    Returns:
        str: protection job payload
    """

    # Send a new Kafka message to Schedule a new Protection job
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
        host=config["KAFKA"]["host"],
    )
    job_id = str(uuid.uuid4())
    json_payload = create_protection_job_kafka_response_object(
        asset_id=asset_id,
        asset_type=asset_type,
        protection_type=protection_type,
        protection_job_id=job_id,
    )
    send_protection_job_kafka_message(
        kafka_manager=kafka_manager,
        json_payload=json_payload,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
        event_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_ONPREM_CREATE_EVENT_TYPE.value,
    )
    return json_payload


def initial_onprem_scheduler_test_setup_with_prepost_scripts(
    asset_id: str,
    asset_type: str,
    protection_type: str = ProtectionType.SNAPSHOT.value,
) -> str:
    """This function will publish a Create VPG protection job with Pre-Post script Data Kafka message to atlas.policy.commands topics

    Args:
        asset_id (str): Asset id
        asset_type (str): Asset type.
        protection_type (str, optional): Protection Type. Defaults to ProtectionType.SNAPSHOT.value.


    Returns:
        str: protection job payload
    """

    # Send a new Kafka message to Schedule a new Protection job
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.ATLAS_POLICY_COMMANDS.value,
        host=config["KAFKA"]["host"],
    )
    job_id = str(uuid.uuid4())
    json_payload = create_onprem_protection_job_kafka_response_object(
        asset_id=asset_id,
        asset_type=asset_type,
        protection_type=protection_type,
        protection_job_id=job_id,
    )
    send_protection_job_kafka_message(
        kafka_manager=kafka_manager,
        json_payload=json_payload,
        event_operation=AtlasPolicyOperations.PROTECTION_JOB_CREATE.value,
        event_type=AtlantiaKafkaEvents.ATLAS_POLICY_JOB_ONPREM_CREATE_EVENT_TYPE.value,
    )
    return json_payload


def assert_updated_repeat_interval_with_retry(
    job_id: str, postgres_manager: PostgresManager, db_connection, repeat_interval: dict, max_retries: int, delay: int
):
    """This function will get protection_job data from DB and
    assert the updated data with retries

    Args:
        job_id (str): Protection job id
        postgres_manager (PostgresManager): Postgres Manager Object
        db_connection (_type_): DB connection object
        repeat_interval (dict): Repeat interval for schedule
        max_retries (int): Max retries to try to update
        delay (int): Delay between tries
    """
    retries = 0
    while retries < max_retries:
        try:
            jobs = get_protection_job(job_id, postgres_manager, db_connection)
            assert len(jobs) > 0
            schedule = jobs[0].schedule
            repeat_interval_every = schedule["repeatInterval"]["every"]
            assert repeat_interval_every == repeat_interval["every"]
            break
        except AssertionError:
            retries += 1
            logger.info("Assertion failed! Retrying... (Attempt {retries})")
            time.sleep(delay)

    if retries == max_retries:
        logger.info("Maximum number of retries reached.")
