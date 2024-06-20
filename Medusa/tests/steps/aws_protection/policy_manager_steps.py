import logging
from datetime import datetime
import copy
from typing import Union
from requests import codes
from lib.common.enums.csp_type import CspType
from lib.common.enums.protection_summary import ProtectionStatus
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSProtectionJobInfo
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import CSPVolumeModel
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import CSPMachineInstanceModel
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.protection_group_model import (
    ProtectionGroupModel,
)
from tests.e2e.azure_protection.azure_context import AzureContext
from utils.dates import compare_dates
from utils.timeout_manager import TimeoutManager
from waiting import wait
from uuid import UUID

from lib.common.enums.suspend_operational import SuspendOperational
from lib.common.enums.app_type import AppType
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.backup_type import BackupType

# to avoid name collision with 'models.protection_jobs.ExecutionStatus' imported below
from lib.common.enums.execution_status import ExecutionStatus as ProtJobExecutionStatus
from lib.common.enums.protection_types import ProtectionType
from lib.common.enums.schedule_type import ScheduleType
from lib.common.enums.object_unit_type import ObjectUnitType
from lib.common.enums.task_status import TaskStatus
from lib.common.error_messages import (
    ERROR_MESSAGE_PROTECTION_POLICY_NOT_FOUND,
)
from lib.dscc.backup_recovery.aws_protection.common.models.asset_set import AssetSet
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ActiveTime,
    CspProtectionJobInfo,
    ObjectUnitValue,
    NamePattern,
    RepeatInterval,
)
import lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_jobs as ProtectionJobs
from lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_policies import (
    ProtectionPolicy,
)
import lib.dscc.backup_recovery.protection_policies.payload.post_put_patch_protection_policies as PostPutPatchProtectionPolicies

from tests.e2e.aws_protection.context import Context
import tests.steps.aws_protection.inventory_manager_steps as IMS
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps
import tests.steps.aws_protection.common_steps as CommonSteps
from tests.steps.tasks import tasks

logger = logging.getLogger()

# NOTE: "start_time"
# Applicable for 'DAILY', 'WEEKLY' and 'MONTHLY' schedules only.
START_TIME_RECURRENCES = [ScheduleType.DAILY, ScheduleType.WEEKLY, ScheduleType.MONTHLY]
# NOTE: "active_time"
# Applicable only for 'BY_MINUTES' and 'HOURLY'
ACTIVE_TIME_RECURRENCES = [ScheduleType.MINUTES, ScheduleType.HOURLY]


def build_backup_policy_schedule(
    expire_after: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.DAYS.value, 3),
    recurrence: ScheduleType = ScheduleType.DAILY,
    repeat_interval: RepeatInterval = RepeatInterval(every=2),
    active_time: ActiveTime = ActiveTime(active_from_time="01:00", active_until_time="23:00"),
    start_time: str = "00:00",
) -> PostPutPatchProtectionPolicies.Schedules:
    """Build a Backup Policy Schedule

    Args:
        expire_after (ObjectUnitValue, optional): Expiration of Backup. Defaults to ObjectUnitValue(ObjectUnitType.DAYS.value, 3).
        recurrence (ScheduleType, optional): Recurrence of Backup. Defaults to ScheduleType.DAILY.
        repeat_interval (RepeatInterval, optional): Repeat Interval of Backup. Defaults to RepeatInterval(every=2).
        active_time (ActiveTime, optional): Active time of Backup. Defaults to ActiveTime(active_from_time="01:00", active_until_time="23:00").
        start_time (str, optional): Start time of backup. Defaults to "00:00".

    Returns:
        Schedules: Backup Policy Schedule object
    """
    schedule_name = "Native_Snapshot_1"
    name_pattern = NamePattern("Native_Snapshot_{DateFormat}")

    start_time_backup = None
    if recurrence in START_TIME_RECURRENCES:
        start_time_backup = start_time

    active_time_backup = None
    if recurrence in ACTIVE_TIME_RECURRENCES:
        active_time_backup = active_time

    backup_schedule = PostPutPatchProtectionPolicies.Schedule(
        repeatInterval=repeat_interval,
        recurrence=recurrence.value,
        startTime=start_time_backup,
        activeTime=active_time_backup,
    )
    # NOTE: Immutability setting (lock_for) is not allowed for protection type 'Backup'
    backup_schedules = PostPutPatchProtectionPolicies.Schedules(
        scheduleId=1,
        schedule=backup_schedule,
        expire_after=expire_after,
        lock_for=None,
        name_pattern=name_pattern,
        name=schedule_name,
    )
    return backup_schedules


def build_cloud_backup_policy_schedule(
    expire_after: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.YEARS.value, 1),
    recurrence: ScheduleType = ScheduleType.MONTHLY,
    repeat_interval: RepeatInterval = RepeatInterval(every=7, on=[1]),
    lock_for: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.YEARS.value, 0),
    active_time: ActiveTime = ActiveTime(active_from_time="01:00", active_until_time="23:00"),
    start_time: str = "00:00",
) -> PostPutPatchProtectionPolicies.Schedules:
    """Build Cloud Backup Policy Schedule

    Args:
        expire_after (ObjectUnitValue, optional): Expiration of Backup. Defaults to ObjectUnitValue(ObjectUnitType.YEARS.value, 1).
        recurrence (ScheduleType, optional): Recurrence of Backup. Defaults to ScheduleType.MONTHLY.
        repeat_interval (RepeatInterval, optional): Repeat Interval of Backup. Defaults to RepeatInterval(every=7, on=[1]).
        lock_for (ObjectUnitValue, optional): Locked Backup duration. Defaults to ObjectUnitValue(ObjectUnitType.YEARS.value, 0).
        active_time (ActiveTime, optional): Active time for Backup. Defaults to ActiveTime(active_from_time="01:00", active_until_time="23:00").
        start_time (str, optional): Start time for Backup. Defaults to "00:00".

    Returns:
        cloud_schedules (Schedules): Cloud Backup Policy Schedule object
    """
    cloud_schedule_name = "Cloud_Backup_2"
    cloud_name_pattern = NamePattern("Cloud_Backup_{DateFormat}")

    start_time_cloud = None
    if recurrence in START_TIME_RECURRENCES:
        start_time_cloud = start_time

    active_time_cloud = None
    if recurrence in ACTIVE_TIME_RECURRENCES:
        active_time_cloud = active_time

    cloud_schedule = PostPutPatchProtectionPolicies.Schedule(
        repeatInterval=repeat_interval,
        recurrence=recurrence.value,
        startTime=start_time_cloud,
        activeTime=active_time_cloud,
    )

    cloud_schedules = PostPutPatchProtectionPolicies.Schedules(
        scheduleId=2,
        schedule=cloud_schedule,
        expire_after=expire_after,
        lock_for=lock_for,
        name_pattern=cloud_name_pattern,
        name=cloud_schedule_name,
    )
    return cloud_schedules


def create_protection_policy(
    context: Context,
    name: str,
    backup_only: bool = False,
    cloud_only: bool = False,
    vmware_schedule: bool = False,
    backup_expire_after: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.DAYS.value, 3),
    backup_recurrence: ScheduleType = ScheduleType.DAILY,
    backup_repeat_interval: RepeatInterval = RepeatInterval(every=2),
    backup_active_time: ActiveTime = ActiveTime(active_from_time="01:00", active_until_time="23:00"),
    backup_start_time: str = "00:00",
    cloud_expire_after: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.YEARS.value, 1),
    cloud_recurrence: ScheduleType = ScheduleType.MONTHLY,
    cloud_repeat_interval: RepeatInterval = RepeatInterval(every=7, on=[1]),
    cloud_lock_for: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.YEARS.value, 0),
    cloud_active_time: ActiveTime = ActiveTime(active_from_time="01:00", active_until_time="23:00"),
    cloud_start_time: str = "00:00",
    immutable: bool = False,
    ms365_schedule: bool = False,
    azure_schedule: bool = False,
) -> str:
    """Create a Protection Policy
    Args:
        context (Context): Test Context
        name (str): The name for the protection policy
        backup_only (bool, optional): If True, only a Backup schedule will be created. Defaults to False.
        cloud_only (bool, optional): If True, only a CloudBackup schedule will be created. Defaults to False.
        vmware_schedule (bool, optional): If True, vmware schedule will be created. Defaults to False.
        backup_expire_after (ObjectUnitValue, optional): Specifies the expiration for the Backup artifacts created. Allowed 'units': HOURS, DAYS, WEEKS, MONTHS, YEARS. Allowed 'value' >= 1. Defaults to ObjectUnitValue("DAYS", 3).
        backup_recurrence (ScheduleType, optional): Specifies the recurrence. Allowed: BY_MINUTES, HOURLY, DAILY, WEEKLY, MONTHLY. Defaults to ScheduleType.DAILY.
        backup_repeat_interval (RepeatInterval, optional): Specifies the repeat interval. Defaults to RepeatInterval(every=2).
        backup_active_time (ActiveTime, optional): Active time for the schedule. Applicable for 'BY_MINUTES' and 'HOURLY' schedules only. Defaults to ActiveTime(active_from_time="01:00", active_until_time="23:00").
        backup_start_time (str, optional): Time when schedule is to be executed. Applicable for 'DAILY', 'WEEKLY' and 'MONTHLY' schedules only. Defaults to "00:00".
        cloud_expire_after (ObjectUnitValue, optional): Specifies the expiration for the CloudBackup artifacts created. Allowed 'units': HOURS, DAYS, WEEKS, MONTHS, YEARS. Allowed 'value' >= 1. Defaults to ObjectUnitValue("YEARS", 1).
        cloud_recurrence (ScheduleType, optional): Specifies the recurrence. Allowed: BY_MINUTES, HOURLY, DAILY, WEEKLY, MONTHLY. Defaults to ScheduleType.MONTHLY.
        cloud_repeat_interval (RepeatInterval, optional): Specifies the repeat interval. Defaults to RepeatInterval(every=7, on=[1]).
        cloud_lock_for (ObjectUnitValue, optional): Retention attribute, specifies the retention period for the artifacts created. Artifacts are locked for deletion for the specified period of time. Defaults to ObjectUnitValue("YEARS", 0).
        cloud_active_time (ActiveTime, optional): Active time for the schedule. Applicable for 'BY_MINUTES' and 'HOURLY' schedules only. Defaults to ActiveTime(active_from_time="01:00", active_until_time="23:00").
        cloud_start_time (str, optional): Time when schedule is to be executed. Applicable for 'DAILY', 'WEEKLY' and 'MONTHLY' schedules only. Defaults to "00:00".
        immutable (bool): Determine if Protection Policy is immutable.
        ms365_schedule (bool, optional): If user want to create protection policy only with ms365 schedule then provide True. by default False
        azure_schedule (bool, optional): If user want to create protection policy only with azure schedule then provide True. by default False
    Raises:
        ValueError: Conflicting values provided for backup_only(True) and cloud_only(True)
    Returns:
        str: The ID of the Protection Policy created.
    """
    logger.info(f"Create protection policy {name}")

    if immutable:
        cloud_lock_for = ObjectUnitValue(ObjectUnitType.YEARS.value, 1)

    # "backup_recurrence" -> default = DAILY, every 2 days
    # "cloud_recurrence" -> Default = MONTHLY, every 7 months, on the 1st day

    backup_schedules = build_backup_policy_schedule(
        expire_after=backup_expire_after,
        recurrence=backup_recurrence,
        repeat_interval=backup_repeat_interval,
        active_time=backup_active_time,
        start_time=backup_start_time,
    )

    cloud_schedules = build_cloud_backup_policy_schedule(
        expire_after=cloud_expire_after,
        recurrence=cloud_recurrence,
        repeat_interval=cloud_repeat_interval,
        lock_for=cloud_lock_for,
        active_time=cloud_active_time,
        start_time=cloud_start_time,
    )

    # TODO Copy pool Id should be updated if required to create a policy for AWS assets.
    # Get /copypools
    if ms365_schedule:
        # This condition added here for ms365 app type schedules and it only supports cloud backups.
        cloud_protection = PostPutPatchProtectionPolicies.Protection(
            copyPoolId=None,
            schedules=[cloud_schedules],
            type=ProtectionType.CLOUD_BACKUP.value,
        )
        protections: list[PostPutPatchProtectionPolicies.Protection] = [cloud_protection]
        applicationType = AppType.ms365  # Assigning again as this needs used for filepoc
    elif not cloud_only and not backup_only:
        backup_protection = PostPutPatchProtectionPolicies.Protection(
            copyPoolId=None,
            schedules=[backup_schedules],
            type=ProtectionType.BACKUP.value,
        )
        # cloud_schedules.sourceProtectionScheduleId = 1  # https://nimblejira.nimblestorage.com/browse/AT-22850
        cloud_protection = PostPutPatchProtectionPolicies.Protection(
            copyPoolId=None,
            schedules=[cloud_schedules],
            type=ProtectionType.CLOUD_BACKUP.value,
        )
        protections: list[PostPutPatchProtectionPolicies.Protection] = [backup_protection, cloud_protection]
        if azure_schedule:
            applicationType = AppType.azure
        else:
            applicationType = AppType.aws  # Assigning again as this needs used for filepoc
    elif not cloud_only and backup_only:
        backup_protection = PostPutPatchProtectionPolicies.Protection(
            copyPoolId=None,
            schedules=[backup_schedules],
            type=ProtectionType.BACKUP.value,
        )
        protections: list[PostPutPatchProtectionPolicies.Protection] = [backup_protection]
        if azure_schedule:
            applicationType = AppType.azure
        else:
            applicationType = AppType.aws  # Assigning again as this needs used for filepoc
    elif not backup_only and cloud_only:
        cloud_protection = PostPutPatchProtectionPolicies.Protection(
            copyPoolId=None,
            schedules=[cloud_schedules],
            type=ProtectionType.CLOUD_BACKUP.value,
        )
        protections: list[PostPutPatchProtectionPolicies.Protection] = [cloud_protection]
        if azure_schedule:
            applicationType = AppType.azure
        else:
            applicationType = AppType.aws  # Assigning again as this needs used for filepoc
    else:
        raise ValueError("DEBUG: Conflicting values provided for backup_only(True) and cloud_only(True)")

    # TODO: Get copy pool id and update the values as needed.
    # How do we get the backup copy pool id and cloud copy pool id from cVSA manager?
    # Is it unique per customer?
    # protections = [Protection(snapshot_copy_pool_id, snapshot_schedules, "Snapshot")]

    if vmware_schedule:  # It will create only VMWare Array snapshot schedule
        vmware_backup_schedules = copy.deepcopy(backup_schedules)
        vmware_backup_schedules.scheduleId = 5  # Updating because duplicate IDs are not allowed
        vmware_backup_schedules.name = "Array_Snapshot_{DateFormat}"
        vmware_protection = PostPutPatchProtectionPolicies.Protection(
            copyPoolId=None,
            schedules=[vmware_backup_schedules],
            type=ProtectionType.SNAPSHOT.value,
        )
        protections.append(vmware_protection)
        applicationType = AppType.vmware  # Assigning again as this needs used for filepoc

    protection_policy = context.policy_manager.post_protection_policy(name, protections, applicationType)
    # NOTE: TypeError: argument of type 'ProtectionPolicy' is not iterable.
    # This assertion is handled in policy_manager call
    # assert ERROR_MESSAGE_PROTECTION_NAME_EXISTS not in protection_policy

    # only store in context if it is currently empty
    if not context.protection_policy_id:
        context.protection_policy_id = protection_policy.id

    # Validate policy is listed by the policy manager
    assert context.policy_manager.get_protection_policy_by_name(
        protection_policy_name=name
    ), ERROR_MESSAGE_PROTECTION_POLICY_NOT_FOUND

    logger.info(f"Protection Policy created: {protection_policy.id}")
    return protection_policy.id


def update_protection_policy(
    context: Context,
    policy_id: UUID,
    name: str = None,
    backup_only: bool = False,
    cloud_only: bool = False,
    start_time: str = "00:00",
    backup_expire_after: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.DAYS.value, 4),
    backup_recurrence: str = ScheduleType.DAILY.value,
    backup_lock_for: ObjectUnitValue = None,
    backup_active_time: ActiveTime = ActiveTime(active_from_time="01:00", active_until_time="23:00"),
    backup_repeat_interval_every: int = 1,
    backup_repeat_interval_on: list[int] = [1],
    cloud_expire_after: ObjectUnitValue = ObjectUnitValue(ObjectUnitType.YEARS.value, 2),
    cloud_recurrence: str = ScheduleType.MONTHLY.value,
    cloud_lock_for: ObjectUnitValue = None,
    cloud_active_time: ActiveTime = ActiveTime(active_from_time="01:00", active_until_time="23:00"),
    cloud_repeat_interval_every: int = 1,
    cloud_repeat_interval_on: list[int] = [1],
) -> str:
    """Update Protection Policy

    Args:
        context (Context): Context object
        policy_id (UUID): UUID of Protection Policy
        name (str, optional): Protection Policy Name. Defaults to None.
        backup_only (bool, optional): Parameter to make Backups only update. Defaults to False.
        cloud_only (bool, optional): Parameter to make Cloud Backups only update. Defaults to False.
        start_time (str, optional): Parameter to make start time update. Defaults to "00:00".
        backup_expire_after (ObjectUnitValue, optional): Parameter to make expire time update. Defaults to ObjectUnitValue(ObjectUnitType.DAYS.value, 4).
        backup_recurrence (str, optional): Parameter to make backup recurrence update. Defaults to ScheduleType.DAILY.value.
        backup_lock_for (ObjectUnitValue, optional): Parameter to make backup lock update. Defaults to None.
        backup_active_time (ActiveTime, optional): Parameter to make backup active time update. Defaults to ActiveTime(active_from_time="01:00", active_until_time="23:00").
        backup_repeat_interval_every (int, optional): Parameter to make backup repeat interval recurrence update. Defaults to 1.
        backup_repeat_interval_on (list[int], optional): Parameter to make backup repeat interval starting update. Defaults to [1].
        cloud_expire_after (ObjectUnitValue, optional): Parameter to make cloud expire after date update. Defaults to ObjectUnitValue(ObjectUnitType.YEARS.value, 2).
        cloud_recurrence (str, optional): Parameter to make cloud recurrence update. Defaults to ScheduleType.MONTHLY.value.
        cloud_lock_for (ObjectUnitValue, optional): Parameter to make cloud lock update. Defaults to None.
        cloud_active_time (ActiveTime, optional): Parameter to make cloud active time update. Defaults to ActiveTime(active_from_time="01:00", active_until_time="23:00").
        cloud_repeat_interval_every (int, optional): Parameter to make cloud repeat interval recurrence update. Defaults to 1.
        cloud_repeat_interval_on (list[int], optional): Parameter to make cloud repeat interval starting update. Defaults to [1].

    Returns:
        str: Protection Policy ID
    """

    # The 4 "ObjectUnitValue" fields cannot have a value of 0
    # If a 0 value is provided, set the parameter to None
    def _validate_field(field: ObjectUnitValue) -> ObjectUnitValue:
        if field and not field.value:
            return None
        return field

    backup_expire_after = _validate_field(field=backup_expire_after)
    backup_lock_for = _validate_field(field=backup_lock_for)
    cloud_expire_after = _validate_field(field=cloud_expire_after)
    cloud_lock_for = _validate_field(field=cloud_lock_for)

    protection_policy = context.policy_manager.get_protection_policy(policy_id)
    protections = protection_policy.protections
    protections_updated = []
    for protection in protections:
        if not cloud_only and protection.type == ProtectionType.BACKUP.value:
            for schedule in protection.schedules:
                schedule.expire_after = backup_expire_after
                schedule.schedule.recurrence = backup_recurrence
                if backup_recurrence == ScheduleType.WEEKLY.value or backup_recurrence == ScheduleType.MONTHLY.value:
                    schedule.schedule.repeatInterval.on = backup_repeat_interval_on
                schedule.lock_for = backup_lock_for
                schedule.schedule.repeatInterval.every = backup_repeat_interval_every
                schedule.schedule.startTime = start_time
                schedule.schedule.activeTime = backup_active_time
            protections_updated.append(protection)

        elif not backup_only and protection.type == ProtectionType.CLOUD_BACKUP.value:
            for schedule in protection.schedules:
                schedule.expire_after = cloud_expire_after
                schedule.schedule.recurrence = cloud_recurrence
                if cloud_recurrence == ScheduleType.WEEKLY.value or cloud_recurrence == ScheduleType.MONTHLY.value:
                    schedule.schedule.repeatInterval.on = cloud_repeat_interval_on
                schedule.lock_for = cloud_lock_for
                schedule.schedule.repeatInterval.every = cloud_repeat_interval_every
                schedule.schedule.startTime = start_time
                schedule.schedule.activeTime = cloud_active_time
            protections_updated.append(protection)

    name = name if name else protection_policy.name

    protection_jobs = context.policy_manager.get_protection_jobs_by_protection_policy_id(policy_id)
    if protection_jobs.total == 0:
        updated_policy: ProtectionPolicy = context.policy_manager.put_protection_policy(
            policy_id=policy_id,
            name=name,
            protections=protections_updated,
            application_type=protection_policy.application_type.value,
        )
    else:
        updated_policy: ProtectionPolicy = context.policy_manager.patch_protection_policy(
            name=name,
            protection_policy_id=policy_id,
            protections=protections_updated,
        )
    return updated_policy.id


def assign_protection_policy(context: Context, asset_id: str, asset_type: str, protection_policy_id: str = None):
    """Assign Protection Policy

    Args:
        context (Context): Context object
        asset_id (str): CSP Asset ID
        asset_type (str): CSP Asset type
        protection_policy_id (str, optional): Protection Policy ID. Defaults to None.
    """
    logger.info("Assign protection policy to AWS resource")
    timeout: int = TimeoutManager.standard_task_timeout

    protection_policy_id = protection_policy_id if protection_policy_id else context.protection_policy_id
    protection_policy = context.policy_manager.get_protection_policy(protection_policy_id)

    # Get backup uuid and cloud backup uuid (similar to copy pools from cVSA !!!)
    backup_id: UUID = ""
    cloud_backup_id: UUID = ""

    for protection in protection_policy.protections:
        protection_type = protection.type
        if protection_type == ProtectionType.BACKUP.value:
            backup_id = protection.id
        elif protection_type == ProtectionType.CLOUD_BACKUP.value:
            cloud_backup_id = protection.id

    # Protect an AWS asset or protection group with a protection policy
    task_id = context.policy_manager.post_protection_jobs(
        asset_id, asset_type, protection_policy_id, backup_id, cloud_backup_id
    )
    status = tasks.wait_for_task(task_id, context.user, timeout)
    assert (
        status == TaskStatus.success.value.lower()
    ), f"Protect asset with protection policy failed {task_id} : {status}"
    logger.info(f"{protection_policy.name} policy successfully assigned to the {asset_id}")


def unassign_all_protection_policies(context: Context, asset_id: str, wait_for_task: bool = True):
    """Delete all Protection Jobs from the asset_id provided
    Args:
        context (Context): The test Context
        asset_id (str): Asset ID
        wait_for_task (bool, optional): If False, will not wait for task completion. Defaults to True (bug DCS-3511)
    """
    protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id=asset_id)
    if not protection_jobs.total:
        logger.warning(f"No protection jobs found for asset id: {asset_id}")
        return

    for protection_job in protection_jobs.items:
        logger.info(f"Protection job delete {protection_job.id}")
        task_id = context.policy_manager.delete_protection_job(protection_job_id=protection_job.id)
        if wait_for_task:
            status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.standard_task_timeout)
            # Note: the status is returned lowercase; TaskStatus enum is uppercase
            assert status.upper() == TaskStatus.success.value, f"Unprotect task failed!! debug: {task_id} - {status}"


def delete_protection_policy(context: Context, policy_id: str = None):
    """Delete Protection Policy

    Args:
        context (Context): Context object
        policy_id (str, optional): Protection Policy ID. Defaults to None.
    """
    policy_id = policy_id if policy_id else context.protection_policy_id
    logger.info(f"Deleting protection policy {policy_id}")
    response = context.policy_manager.delete_protection_policy(UUID(policy_id))
    assert response.status_code == codes.no_content, f"Protection policy deletion failed: {response.content}"
    logger.info(f"Protection policy with {context.protection_policy_id} deleted successfully!!!")


def protect_standard_assets_with_protection_policy(
    context: Context, protection_policy_id: str, asset_set: AssetSet = None
):
    """Protect Standard Assets with a Protection Policy

    Args:
        context (Context): Context object
        protection_policy_id (str): Protection Policy ID
        asset_set (AssetSet, optional): Asset Set of Standard Assets. Defaults to None.
    """
    if not asset_set:
        asset_set = context.asset_set_region_one_aws_one
    asset_id_list, asset_type_list = asset_set.get_standard_assets()
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if not asset_id:
            continue
        # create Protection Job for each standard asset
        create_protection_job_for_asset(
            context=context,
            asset_id=asset_id,
            asset_type=asset_type,
            protection_policy_id=protection_policy_id,
        )
        status = IMS.get_asset_protection_status(context, asset_id, asset_type)
        logger.info(f"For testing, immediate ProtectionStatus = {status}")


def assign_protection_policy_and_wait_for_assignment(
    context: Union[Context, AzureContext],
    account_id: str,
    protection_policy_id: str,
    asset: Union[CSPMachineInstanceModel, CSPVolumeModel, ProtectionGroupModel],
    asset_type: AssetType,
    expected_protection_status: ProtectionStatus,
    csp_type: CspType = CspType.AWS,
):
    """Assigns provided protection policy to the target assets and waits for the required protection status of the asset

    Args:
        context (Union[Context, AzureContext]): Context or AzureContext object
        account_id (str): CSP Account ID
        protection_policy_id (str): ID of the protection policy to be assigned to the asset
        asset (Union[CSPMachineInstanceModel, CSPVolumeModel, ProtectionGroupModel]): Asset object to which the protection policy should be assigned
        asset_type (AssetType): Type of the asset. Valid values are: CSP_MACHINE_INSTANCE, CSP_VOLUME, CSP_PROTECTION_GROUP
        expected_protection_status (ProtectionStatus): Protection Status the asset should be in after policy assignment
        csp_type (CspType, optional): Type of the asset -> AWS / Azure. Defaults to AWS
    """

    logger.info(f"Assigning Policy {protection_policy_id}, to {asset_type.value}, {asset.id}")
    create_protection_job_for_asset(
        context=context,
        asset_id=asset.id,
        asset_type=asset_type,
        protection_policy_id=protection_policy_id,
    )

    wait_for_protection_status(context, account_id, asset, asset_type, expected_protection_status, csp_type)


def wait_for_protection_status(
    context: Union[Context, AzureContext],
    account_id: str,
    asset: Union[CSPMachineInstanceModel, CSPVolumeModel, ProtectionGroupModel],
    asset_type: AssetType,
    expected_protection_status: ProtectionStatus,
    csp_type: CspType = CspType.AWS,
):
    """Waits for the required protection status of the asset

    Args:
        context (Union[Context, AzureContext]): Context or AzureContext object
        account_id (str): CSP Account ID
        asset (Union[CSPMachineInstanceModel, CSPVolumeModel, ProtectionGroupModel]): Asset object to which the protection policy should be assigned
        asset_type (AssetType): Type of the asset. Valid values are: CSP_MACHINE_INSTANCE, CSP_VOLUME, CSP_PROTECTION_GROUP
        expected_protection_status (ProtectionStatus): Protection Status the asset should be in after policy assignment
        csp_type (CspType, optional): Type of the asset -> AWS / Azure. Defaults to AWS
    """
    if asset_type == AssetType.CSP_PROTECTION_GROUP:
        logger.info(f"Retrieving assets for PG: {asset.name}")
        filter = (
            f"cspType eq '{csp_type.value}' and accountInfo/id eq {account_id} and {asset.id} in protectionGroupInfo/id"
        )

        if asset.assetType == AssetType.CSP_MACHINE_INSTANCE:
            pg_assets = IMS.get_csp_instances(context=context, filter=filter)
            asset_type = AssetType.CSP_MACHINE_INSTANCE
        else:
            pg_assets = IMS.get_csp_volumes(context=context, filter=filter)
            asset_type = AssetType.CSP_VOLUME

        for pg_asset in pg_assets.items:
            logger.info(
                f"Waiting for {asset_type.value}, {pg_asset.id} to be in Protection Status: {ProtectionStatus.PENDING.value}"
            )
            IMS.wait_for_asset_protection_status(
                context=context,
                asset_id=pg_asset.cspId,
                expected_status=ProtectionStatus.PENDING,
                asset_type=asset_type,
                account_id=account_id,
            )
    else:
        logger.info(
            f"Waiting for {asset_type.value}, {asset.id} to be in Protection Status: {expected_protection_status.value}"
        )
        IMS.wait_for_asset_protection_status(
            context=context,
            asset_id=asset.cspId,
            expected_status=expected_protection_status,
            asset_type=asset_type,
            account_id=account_id,
        )


def unprotect_standard_assets_from_protection_policies(
    context: Context, account_name: str = None, asset_set: AssetSet = None
):
    """Remove all Protection Policies from standard assets.
    Args:
        context (Context): The Context
        asset_set (AssetSet, optional): List of Asset IDs
        Defaults to None.
    """
    if not account_name:
        account_name = context.aws_one_account_name
    if not asset_set:
        asset_set = context.asset_set_region_one_aws_one
    asset_id_list, asset_type_list = asset_set.get_standard_assets()
    for asset_id, _ in zip(asset_id_list, asset_type_list):
        unassign_all_protection_policies(context=context, asset_id=asset_id)
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name=account_name)
    CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account.id)


def protect_protection_groups_with_protection_policy(
    context: Context, protection_policy_id: str, protection_group_ids: list[str]
):
    """Protect Protection Groups with a Protection Policy

    Args:
        context (Context): Context object
        protection_policy_id (str): Protection Policy ID
        protection_group_ids (list[str]): List of Protection Group IDs
    """
    logger.info(f"Assigning protection policy {protection_policy_id} to protection group {protection_group_ids}")
    for protection_group_id in protection_group_ids:
        assign_protection_policy(
            context,
            protection_group_id,
            AssetType.CSP_PROTECTION_GROUP.value,
            protection_policy_id,
        )


def unprotect_protection_groups_from_protection_policy(context: Context, protection_group_ids: list[str]):
    """Unprotect Protection Groups from Protection Policy

    Args:
        context (Context): Context object
        protection_group_ids (list[str]): List of Protection Group IDs
    """
    for protection_group_id in protection_group_ids:
        unassign_all_protection_policies(context, protection_group_id)


def suspend_protection_job_for_assets(context: Context, asset_id_list: list[str]):
    """Suspend Protection Job for Assets

    Args:
        context (Context): Context object
        asset_id_list (list[str]): List of Asset IDs
    """
    for asset_id in asset_id_list:
        protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id)
        for protection_job in protection_jobs.items:
            protection_job_id = protection_job.id
            schedules_ids = []
            for protection in protection_job.protections:
                for schedules in protection.schedules:
                    schedules_ids.append(schedules.schedule_id)
            task_id = context.policy_manager.suspend_protection_job(protection_job_id, schedules_ids)
            status = tasks.wait_for_task(task_id, context.user, TimeoutManager.standard_task_timeout)
            assert (
                status.upper() == TaskStatus.success.value
            ), f"Unable to suspend the protection job!! debug: {task_id} - {status}"
        else:
            logger.warning(f"No protection jobs found for asset id {asset_id}")


def suspend_protection_job_schedule_for_asset(context: Context, asset_id: str, protection_type: BackupType):
    protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id)
    if protection_jobs.items:
        protection_job_id = protection_jobs.items[0].id
        schedule_id = ""
        for protection in protection_jobs.items[0].protections:
            if protection.type == protection_type.value:
                schedule_id = protection.schedules[0].schedule_id
        task_id = context.policy_manager.suspend_protection_job(protection_job_id, [schedule_id])
        status = tasks.wait_for_task(task_id, context.user, TimeoutManager.standard_task_timeout)
        assert (
            status.upper() == TaskStatus.success.value
        ), f"Unable to suspend the protection job!! debug: {task_id} - {status}"
    else:
        logger.warning(f"No protection jobs found for asset id {asset_id}")


def resume_protection_job_schedule_for_asset(context: Context, asset_id: str, protection_type: BackupType):
    """Resume protection schedule of a specified protection type for an asset

    Args:
        context (Context): context object
        asset_id (str): asset id of an associated protection job
        protection_type (BackupType): backup type of the schedule to be resumed.
    """
    protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id)
    if protection_jobs.items:
        protection_job_id = protection_jobs.items[0].id
        schedule_id = []
        for protection in protection_jobs.items[0].protections:
            if protection.type == protection_type.value:
                schedule_id = protection.schedules[0].schedule_id
        logger.info(f"Resuming protection schedule {schedule_id} of protection job ID: {protection_job_id}")
        task_id = context.policy_manager.resume_protection_job(
            protection_job_id=protection_job_id,
            schedules_ids=[schedule_id],
        )
        status = tasks.wait_for_task(task_id, context.user, TimeoutManager.standard_task_timeout)
        assert (
            status.upper() == TaskStatus.success.value
        ), f"Unable to resume the protection job!! debug: {task_id} - {status}"
        logger.info(f"Successfully Resumed protection schedule {schedule_id} of protection job ID: {protection_job_id}")
    else:
        logger.warning(f"No protection jobs found for asset id {asset_id}")


def suspend_protection_jobs_for_protection_policy(context: Context, protection_policy_id: str):
    """Suspend all the protections job that is associated with respective protection policy
    Args:
        context (Context): context
        protection_policy_id (str): protection policy id
    """
    task_ids = list()
    protection_jobs = context.policy_manager.get_protections_jobs_for_the_protection_policy(protection_policy_id)
    for protection_job in protection_jobs.items:
        logger.info(f"{protection_job.operational=} == {SuspendOperational.active.value=}")
        wait(
            lambda: protection_job.operational == SuspendOperational.active.value,
            timeout_seconds=180,
            sleep_seconds=10,
        )
        schedules_ids = []
        for protection in protection_job.protections:
            for schedules in protection.schedules:
                schedules_ids.append(schedules.schedule_id)
        task_id = context.policy_manager.suspend_protection_job(protection_job.id, schedules_ids)
        task_ids.append(task_id)
    for task_id in task_ids:
        tasks.wait_for_task(task_id=task_id, user=context.user, timeout=300)


def resume_protection_jobs_for_protection_policy(context: Context, protection_policy_id: str):
    """Resume all the protections job that is associated with respective protection policy
    Args:
        context (Context): context
        protection_policy_id (str): protection policy id
    """
    task_ids = list()
    protection_jobs = context.policy_manager.get_protections_jobs_for_the_protection_policy(protection_policy_id)
    for protection_job in protection_jobs.items:
        schedules_ids = []
        for protection in protection_job.protections:
            for schedules in protection.schedules:
                schedules_ids.append(schedules.schedule_id)
        task_ids.append(
            context.policy_manager.resume_protection_job(
                protection_job_id=protection_job.id,
                schedules_ids=schedules_ids,
            )
        )
    for task_id in task_ids:
        tasks.wait_for_task(task_id=task_id, user=context.user, timeout=300)


def unprotect_policy_from_standard_protection_groups(context: Context, asset_set: AssetSet):
    """Unprotect Protection Policy from Standard Protection Groups

    Args:
        context (Context): Context object
        asset_set (AssetSet): Asset Set for Standard Protection Groups
    """
    for asset_id in asset_set.standard_pg_id_list:
        unassign_all_protection_policies(context, asset_id)


def delete_policy_expect_failure(context: Context, protection_policy_id: str, error_msg: str):
    """Delete Protection Policy Expecting a Failure

    Args:
        context (Context): Context object
        protection_policy_id (str): Protection Policy ID
        error_msg (str): Expected Error Message
    """
    response = context.policy_manager.delete_protection_policy(UUID(protection_policy_id))
    assert (
        response.status_code == codes.bad_request
    ), f"FAIL - Protection policy {protection_policy_id} deleted - delete should fail: {response.content}"
    assert error_msg in response.text, f"Error message is not in response text: {response.text}"
    logger.info(f"Successfully validated error message Expected: {error_msg} Actual: {response.text}")


def delete_protection_jobs(context: Context, protection_job_ids: list[str]):
    """Delete from Policy Manager the list of Protection Job IDs provided
    Args:
        context (Context): The test Context
        protection_job_ids (list[str]): A list of Protection Job IDs
    """
    for id in protection_job_ids:
        task_id: str = context.policy_manager.delete_protection_job(id)
        tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.standard_task_timeout,
        )


# TODO: Duplicate function. replace with unassign_all_protection_policies()
def delete_asset_protection_jobs(context: Context, asset_id: str):
    """Delete Asset's Protection Jobs

    Args:
        context (Context): Context object
        asset_id (str): Asset ID
    """
    protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id=asset_id)
    for protection_job in protection_jobs.items:
        task_id = context.policy_manager.delete_protection_job(protection_job_id=protection_job.id)
        tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.standard_task_timeout,
        )


def delete_protection_jobs_and_policy(context: Context, protection_policy_name: str, raise_error: bool = False):
    """Delete from Policy Manager any Protection Jobs associated with the provided protection policy as well as deleting the protection policy
    Args:
        context (Context): The test Context
        protection_policy_name (str): A Protection Policy Name
    """
    # Delete any protection jobs before deleting the protection policy
    protection_job_ids: list[str] = []
    protection_policy = context.policy_manager.get_protection_policy_by_name(
        protection_policy_name=protection_policy_name
    )
    if protection_policy:
        logger.info(f"Protection Policy found: {protection_policy_name} : {protection_policy.id}")
        protection_jobs = context.policy_manager.get_protections_jobs_for_the_protection_policy(
            protection_policy_id=protection_policy.id
        )
        if protection_jobs.total != 0:
            for protection_job in protection_jobs.items:
                protection_job_ids.append(protection_job.id)

        try:
            delete_protection_jobs(context=context, protection_job_ids=protection_job_ids)
            logger.info(f"Successfully deleted {len(protection_job_ids)} protection jobs")
            context.policy_manager.delete_protection_policy(protection_policy_id=protection_policy.id)
            logger.info(f"Successfully deleted Protection Policy: {protection_policy_name}")
        except AssertionError as e:
            # Rename the Protection Policy since it is assigned to an asset that no longer exists in DSCC - BUG: AT-17729
            # date_time.strftime("%c") -> 2022-09-27 20:23:18.071872
            date_time = datetime.now()
            new_protection_policy_name: str = f"Invalid-{protection_policy_name}-{date_time.strftime('%c')}"

            # AssertionError: b'{"errorCode":"200000","error":"string does not match regex \\"^[a-zA-Z0-9-_,&\\\\s]+$\\" in body->name"}'
            #   A : character is no longer allowed in a Protection Policy name. We'll replace them with a _
            new_protection_policy_name = new_protection_policy_name.replace(":", "_")

            # Only care about updating name, all other paramaters can be ignored since this is a temporary fix for the BUG: AT-17729
            # update_protection_policy() will create both backup & cloud_backup as default along with the name change
            update_protection_policy(
                context=context,
                policy_id=protection_policy.id,
                name=new_protection_policy_name,
            )
            logger.info(f"Renamed the Protection Policy to {new_protection_policy_name}")
            logger.error(f"Failed to delete Protection Jobs: {e}")

            if raise_error:
                raise e


def create_protection_job_for_asset(
    context: Context,
    asset_id: str,
    asset_type: AssetType,
    protection_policy_id: str,
    wait_for_task: bool = True,
) -> str:
    """Create a Protection Job for the given Asset ID and Asset Type using the given Protection Policy ID
    Args:
        context (Context): The test Context
        asset_id (str): Asset ID
        asset_type (AssetType): Type of asset (SVC2) EC2Instance, EBSVolume, AWSProtectionGroup
        protection_policy_id (str): Protection Policy ID
        wait_for_task (bool, optional): If False, task_id will return immediately. Defaults to True (bug DCS-3511)
    Returns:
        task_id (str): Task ID of the initiated Create Protection Job operation
    """
    protection_policy_id = protection_policy_id if protection_policy_id else context.protection_policy_id
    protection_policy = context.policy_manager.get_protection_policy(protection_policy_id)
    backup_id: UUID = ""
    cloud_backup_id: UUID = ""

    for protection in protection_policy.protections:
        protection_type = protection.type
        if protection_type == ProtectionType.BACKUP.value:
            backup_id = protection.id
        elif protection_type == ProtectionType.CLOUD_BACKUP.value:
            cloud_backup_id = protection.id

    task_id = context.policy_manager.post_protection_jobs(
        asset_id=asset_id,
        asset_type=asset_type.value,
        protection_policy_id=protection_policy_id,
        backup_id=backup_id,
        cloud_backup_id=cloud_backup_id,
    )

    if wait_for_task:
        # Note: the status is returned lowercase; TaskStatus enum is uppercase
        protection_job_task_status: str = tasks.wait_for_task(
            task_id, context.user, TimeoutManager.standard_task_timeout
        )
        assert protection_job_task_status.upper() == TaskStatus.success.value
    logger.info(f"Protection policy assigned to {asset_type.value} - {asset_id}")

    return task_id


def get_protection_policies_containing_name(context: Context, name_part: str) -> list[ProtectionPolicy]:
    """Returns a list of ProtectionPolicy whose name contains the "name_part" provided
    Args:
        context (Context): The test Context
        name_part (str): The name part to filter on
    Returns:
        list[ProtectionPolicy]: A list of Protection Policy objects whose name includes the "name_part" provided
    """
    return_list: list[ProtectionPolicy] = []

    # find any Policies that contain the "name_part"
    protection_policy_list = context.policy_manager.get_protection_policies()
    for policy in protection_policy_list.items:
        if name_part in policy.name:
            return_list.append(policy)
    return return_list


def get_execution_statuses_for_protection_job_backup_type(
    context: Context, protection_job_id: str, protection_type: BackupType
) -> list[ProtectionJobs.ExecutionStatus]:
    """Return the ExecutionStatus list for the 'protection_type' provided.
    Args:
        context (Context): Test Context
        protection_job_id (str): Protection Job ID
        protection_type (BackupType): BackupType
    Returns:
        list[ExecutionStatus]: A list of ExecutionStatus objects
    """
    # get protection job
    protection_job = context.policy_manager.get_protection_job(protection_job_id=protection_job_id)
    the_protection: ProtectionJobs.Protection = None

    # get Protection 'protection_type'
    for protection in protection_job.protections:
        if protection.type == protection_type.value:
            the_protection = protection
            break

    assert the_protection, f"Protection type {protection_type} not found in Protection Job: {protection_job_id}"

    return the_protection.schedules[0].execution_statuses


def validate_protection_job_status_for_policy(
    context: Context,
    asset_id: str,
    policy_id: str,
    backup_types: list[BackupType] = [BackupType.BACKUP],
):
    """Validate the 'execution status' values for 'protection_job' using 'policy_id' provided are 'Ok' for 'asset_id' provided
    Args:
        context (Context): Test Context
        asset_id (str): The DSCC Asset ID
        policy_id (str): The DSCC Protection Policy ID
        backup_types (list[BackupType], optional): list of BackupType to validate. Defaults to [BackupType.BACKUP].
    """
    protection_job_list = context.policy_manager.get_protection_job_by_asset_id(asset_id=asset_id)
    assert protection_job_list.total, "Expected at least 1 Protection Job, but found none"
    logger.info(f"num jobs: {protection_job_list.total}")

    # get job pertaining to 'policy_id' provided
    protection_job: ProtectionJobs.ProtectionJob = None

    for job in protection_job_list.items:
        if UUID(policy_id) == job.protection_policy_info.id:
            protection_job = job
            break

    assert protection_job, f"Did not find protection job for policy_id: {policy_id}"

    # check all requested backup_type statuses
    for backup_type in backup_types:
        # statuses
        execution_statuses = get_execution_statuses_for_protection_job_backup_type(
            context=context,
            protection_job_id=protection_job.id,
            protection_type=backup_type,
        )
        assert len(
            execution_statuses
        ), f"Expected to find at least 1 {backup_type.value} execution status for protection job: {protection_job.id}, but found: {execution_statuses}"
        logger.info(f"num status entries: {len(execution_statuses)}")

        # ensure only "Ok" execution status
        for status in execution_statuses:
            if not compare_dates(date_new=datetime.now(), date_old=status.timestamp, days_offset=1):
                continue

            assert (
                status.status == ProtJobExecutionStatus.OK.value
            ), f"None-Ok {backup_type.value} execution status for protection job: {status}"


def is_asset_protected_by_policy(asset: any, policy_name: str, policy_id: str, asset_type: AssetType) -> bool:
    """Check if provided asset has a protection job from provided policy name and id.
    Args:
        asset (any): CSPMachineInstance, CSPVolume, CSPRDSInstance or ProtectionGroup asset.
        policy_name (str): Name of the Protection Policy to validate.
        policy_id (str): ID pf the Protection Policy to validate.
        asset_type (AssetType): CSP_MACHINE_INSTANCE, CSP_VOLUME, CSP_RDS_DATABASE_INSTANCE, or CSP_PROTECTION_GROUP
    Returns:
        bool: True if the asset has a Protection Job associated with the Policy data provided, False otherwise.
    """

    # CSPMachineInstance, CSPVolume and ProtectionGroup all have "protectionJobInfo" field
    # CSPRDSInstance has "protection_job_info"
    if asset_type == AssetType.CSP_RDS_DATABASE_INSTANCE:
        rds_protection_jobs: list[RDSProtectionJobInfo] = asset.protection_job_info
        for job in rds_protection_jobs:
            if job.protection_policy_info.name == policy_name and policy_id in job.protection_policy_info.resourceUri:
                return True
    else:
        protection_jobs: list[CspProtectionJobInfo] = asset.protectionJobInfo
        for job in protection_jobs:
            if job.protection_policy_info.name == policy_name and policy_id in job.protection_policy_info.resourceUri:
                return True
    return False
