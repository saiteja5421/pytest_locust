"""inventory_manager_steps.py contains the relevant steps/commands to help perform Inventory Manager related tests.

DEPRECATION NOTICE:  Functions in this file use the original /api/v1 REST endpoints via calls to
lib/dscc/backup_recovery/aws_protection/ec2/api/inventory_manager.py.  Those endpoints can be considered deprecated.
Use the functions in inventory_manager_v1beta1_steps.py instead.

Below are the following Region categories of this file:
-   Inventory Sync
-   CSP Instance
-   CSP Volume
-   Tags
-   Subnets
-   VPCs
-   Protection Groups
-   Asset State
-   Asset Protection Status
-   Protection Jobs
-   Basic Compare/Validate Asset Functions

NOTE: If you can't find a method function in the expected region, try looking in another related region.
"""

import fcntl
import glob
import inspect
import logging
import os
import requests
import tempfile
import time
import uuid

from datetime import datetime, timedelta
from os.path import exists
from typing import Any, Union
from uuid import UUID
from waiting import TimeoutExpired, wait

from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.asset_type_uri_prefix import AssetTypeURIPrefix
from lib.common.enums.az_regions import AZRegion
from lib.common.enums.kafka_inventory_asset_type import KafkaInventoryAssetType
from lib.common.enums.csp_resource_type import CSPResourceType
from lib.common.enums.protection_group_dynamic_filter_type import ProtectionGroupDynamicFilterType
from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.protection_summary import ProtectionStatus
from lib.common.enums.task_status import TaskStatus
from lib.common.enums.ec2_state import Ec2State
from lib.common.enums.state import State
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import GLCPErrorResponse
import lib.dscc.backup_recovery.aws_protection.common.models.asset_set_dto as AwsAssetsDto
from lib.common.error_codes import (
    TaskErrorCodeSyncAccountInProgress,
    TaskErrorCodeSyncAccountInstances,
    TaskErrorCodeSyncAccountVolumes,
)

# DSCC Model classes
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
    ItemList,
    CSPTag,
    ObjectCountType,
    ObjectNameResourceType,
    ObjectNameResourceTypeId,
    CspProtectionJobInfo,
    TagKeyValue,
)

# Domain Model classes
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subnet_model import (
    CSPSubnetModel,
    CSPSubnetListModel,
)
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import (
    CSPVolumeModel,
    CSPVolumeListModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import (
    CSPMachineInstanceListModel,
    CSPMachineInstanceModel,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.protection_group_model import (
    ProtectionGroupModel,
    ProtectionGroupListModel,
    ProtectionJobInfoModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_vpc_model import CSPVPCModel, CSPVPCListModel
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_resource_group_model import (
    CSPResourceGroupModel,
    CSPResourceGroupListModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subscription_model import (
    CSPSubscriptionModel,
    CSPSubscriptionListModel,
)

# Domain Model payloads
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.csp_protection_group_payload_model import (
    PostCustomProtectionGroupStaticMembersModel,
    PostUpdateCSPTagsModel,
    PostDynamicProtectionGroupModel,
    DynamicMemberFilterModel,
    PostCustomProtectionGroupModel,
)

from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.aws_boto3.aws_factory import AWS

from tests.e2e.aws_protection.context import Context
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps
from tests.e2e.azure_protection.azure_context import AzureContext
import tests.steps.aws_protection.common_steps as CommonSteps
from tests.steps.tasks import tasks
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()

REFRESH_IN_PROGRESS_SLEEP_TIME: int = 60


# region Inventory Refresh
def account_inventory_refresh_lock_file(account_id: str) -> str:
    """Lock file used by account_inventory_refresh() to serialize refresh requests

    Args:
        account_id (str): CSP Account ID

    Returns:
        str: Temp File/Directory Path
    """
    return os.path.join(tempfile.gettempdir(), f"account_inventory_refresh_lock_file-{account_id}")


def account_inventory_refresh(
    context: Context,
    account_id: str,
    timeout: int = TimeoutManager.standard_task_timeout,
    retry_count: int = 5,
):
    """Perform an account inventory refresh.

    This function is a wrapper around the _account_inventory_refresh_with_retry() function.  See
    that function for details on the input properties.

    Args:
        context (Context): Context object
        account_id (str): CSP Account ID
        timeout (int, optional): Timeout for Inventory Refresh. Defaults to TimeoutManager.standard_task_timeout.
        retry_count (int, optional): Number of attempts to refresh inventory. Defaults to 5.
    """

    def account_inventory_refresh_wrapper() -> str:
        return context.inventory_manager.trigger_account_inventory_sync(account_id)

    _account_inventory_refresh_with_retry(
        context=context,
        refresh_trigger_func=account_inventory_refresh_wrapper,
        account_id=account_id,
        timeout=timeout,
        retry_count=retry_count,
    )


def _account_inventory_refresh_with_retry(
    context: Context,
    refresh_trigger_func,
    account_id: str,
    timeout: int,
    retry_count: int,
):
    """This function is a wrapper around the _account_inventory_refresh() function.  See that function for
    details on the input properties (excluding `retry_count` which is detailed below).

    While _account_inventory_refresh() is performing an inventory refresh, other parallel functional
    tests could be updating assets in the datastore.  For example, a functional test might be adding a
    protection job which causes that asset's generation to increment.  When inventory manager tries to
    update an asset in the datastore, that asset's generation may no longer match what was initially
    enumerated.  That causes the datastore request to fail along with the Cadence activity.  This failure
    can repeat itself through all Cadence retries.  Could be a different asset or an ever incrementing
    generation value on the same asset.  Either way, Inventory Manager could eventually fail the inventory
    refresh.

    If an inventory refresh fails, where success was expected, this function will retry `retry_count`
    additional times (default five).

    Args:
        context (Context): Context object
        refresh_trigger_func: A closure function that triggers an account inventory refresh and returns a task ID.
        account_id (str): CSP Account ID
        timeout (int, optional): Timeout for Inventory Refresh.
        retry_count (int, optional): Number of attempts to refresh inventory.
    """

    for i in range(retry_count + 1):
        refresh_task_status, task_id = _account_inventory_refresh(
            context=context, account_id=account_id, refresh_trigger_func=refresh_trigger_func, timeout=timeout
        )

        # If an error occurs, retrieve the task error message
        task_error_code: int = 0
        if refresh_task_status.upper() != TaskStatus.success.value:
            task_error_code = tasks.get_task_error_code(task_id, context.user)

        # If the refresh request failed with a retriable error code, and there are retry attempts remaining,
        # log a warning and retry the request.
        retriable_error_codes = [
            TaskErrorCodeSyncAccountInProgress,
            TaskErrorCodeSyncAccountInstances,
            TaskErrorCodeSyncAccountVolumes,
        ]
        if (task_error_code in retriable_error_codes) and (i < retry_count):
            logger.warn(f"Inventory Manager refresh retry required, task_error_code={task_error_code}")
            if task_error_code == TaskErrorCodeSyncAccountInProgress:
                # If the Refresh Task fails due to: TaskErrorCodeSyncAccountInProgress, then we'll
                # sleep for a minute before continuing the loop.
                # The Refresh that is in progress cannot be trusted to sync all the assets we need.  For example
                # it might have already synced the target region before our changes were made there.
                #
                # E           AssertionError: Refresh failure, refresh_task_status=failed, task_error_code=200
                logger.warn(
                    f"An Inventory Refresh is in progress for account: {account_id}. "
                    f"Sleeping for {REFRESH_IN_PROGRESS_SLEEP_TIME} seconds..."
                )
                time.sleep(REFRESH_IN_PROGRESS_SLEEP_TIME)
            continue

        # Assert on failure
        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"Refresh failure, refresh_task_status={refresh_task_status}, task_error_code={task_error_code}"
        break
    logger.info("inventory refreshed")


def _account_inventory_refresh(
    context: Context,
    refresh_trigger_func,
    account_id: str,
    timeout: int = TimeoutManager.standard_task_timeout,
):
    """
        This routine performs a synchronous inventory manager account refresh.  The following factors need to be taken
        into consideration when submitting a refresh request:

        1.) The inventory manager can only support one refresh at a time.  If a refresh request is received, while
            another request is still in process, the new request will fail with a conflict error.
        2.) A refresh request can take a reasonable amount of time to complete.
        3.) Multiple inventory functional tests are run in parallel resulting in concurrent refresh requests

        The code performs the following steps to serialize and group refresh requests to ensure optimal performance
        and reliability:

        1.) Create a "sync_needed" signature file in the /tmp folder with a unique filename.
        2.) Get exclusive file lock on "/tmp/account_inventory_refresh_lock_file" (i.e. file mutex).
        3.) Enumerate all "sync_needed" signature files that are present in the /tmp file.
        4.) If "sync_needed" signature file (created at step #1) is no longer present, there is nothing further to do.
            Another process has already performed the refresh for the current instance.  Mutex released and successful
            status is returned.  Remaining steps not taken.
        5.) Execute a synchronous inventory manager refresh
        6.) If refresh successful, delete all "sync_needed" signature files enumerated at step #3.  These were files
            created by processes which are blocked waiting on the file lock.  Once they get the file lock, they will
            see that the file is deleted and know that some other process successfully completed the refresh.

    Args:
        context (Context): test execution context
        refresh_trigger_func: A closure function that triggers an account inventory refresh and returns a task ID.
            It is intended to enable the use of serialization controls for both the legacy v1 and v1beta1 APIs.
        account_id (str): CSP Account ID
        timeout (int, optional): refresh timeout
    """

    # Log details about the refresh request
    logger.info(
        "account_inventory_refresh, caller=%s, account_id=%s, timeout=%s"
        % (
            inspect.stack()[1].function,
            account_id,
            timeout,
        )
    )

    # Create a unique inventory sync needed signature file
    sync_needed_signature_file = f"{account_inventory_refresh_lock_file(account_id)}-{str(uuid.uuid4())}"
    open(sync_needed_signature_file, "a").close()

    start_time = time.time()
    with open(account_inventory_refresh_lock_file(account_id), "w") as lock_file:
        # Serialize inventory refresh requests
        fcntl.lockf(lock_file, fcntl.LOCK_EX)
        lock_time = time.time()

        # Before initiating the inventory sync, enumerate the current list of signature files to determine if an
        # inventory sync is needed or if it was handled by another process.
        search_path = f"{account_inventory_refresh_lock_file(account_id)}-*"
        sync_needed_signature_files = glob.glob(search_path)
        is_sync_needed = sync_needed_signature_file in sync_needed_signature_files

        refresh_task_status = TaskStatus.success.value
        task_id = None
        if is_sync_needed:
            task_id = refresh_trigger_func()
            refresh_task_status = tasks.wait_for_task(
                task_id=task_id, user=context.user, timeout=timeout, log_result=True
            )

            # Delete the signature files that were enumerated prior to initiating the inventory sync
            if refresh_task_status.upper() == TaskStatus.success.value:
                for f in sync_needed_signature_files:
                    assert os.path.isfile(f)
                    os.remove(f)
            elif exists(sync_needed_signature_file):
                os.remove(sync_needed_signature_file)

        end_time = time.time()
        fcntl.lockf(lock_file, fcntl.LOCK_UN)

        # Log time to complete inventory refresh
        logger.info(
            (
                "account_inventory_refresh, caller=%s, status=%s, is_sync_needed=%s, lock_duration=%.1fs"
                ", refresh_duration=%.1fs"
            )
            % (
                inspect.stack()[1].function,
                refresh_task_status,
                is_sync_needed,
                lock_time - start_time,
                end_time - lock_time,
            )
        )

        return (refresh_task_status, task_id)


# endregion

# region CSP Instance


def get_csp_instances(
    context: Context, sort_by: str = "name", filter: str = "", tag_filter: str = ""
) -> CSPMachineInstanceListModel:
    """Get a list of CSP Machine Instances
    Args:
        context (Context): Context object
        sort_by (str, optional): Parameter of how to sort the list of CSP Machine Instances. Defaults to "name".
        filter (str, optional): Parameter of how to filter the list of CSP Machine Instances. Defaults to "".
        tag_filter (str, Optional): Parameter of what key/value tags to further filter the CSP Machine Instances. Defaults to "".
    Returns:
        csp_machine_instances (CSPMachineInstanceListModel): List of CSP Machine Instance objects
    """
    csp_machine_instances: CSPMachineInstanceListModel = context.inventory_manager.get_csp_machine_instances(
        sort=sort_by, filter=filter, tag_filter=tag_filter
    )
    return csp_machine_instances


def get_csp_instance_by_id(
    context: Context,
    csp_machine_id: str,
    response_code: int = requests.codes.ok,
) -> CSPMachineInstanceModel:
    """Get a CSP Machine Instance object by CSP Machine Instance ID
    Args:
        context (Context): Context object
        csp_machine_id (str): CSP Machine Instance ID
        response_code (int, optional): Expected response code of API call. Defaults to requests.codes.ok.
    Returns:
        csp_machine_instance (CSPMachineInstanceModel): CSP Machine Instance object
    """
    inventory_manager = context.inventory_manager
    csp_machine_instance: CSPMachineInstanceModel = inventory_manager.get_csp_machine_instance_by_id(
        csp_machine_id=csp_machine_id,
        response_code=response_code,
    )
    return csp_machine_instance


def get_csp_instances_by_name(context: Context, csp_machine_name: str) -> list[CSPMachineInstanceModel]:
    """Get a list of CSP Machine Instance objects by CSP Machine Instance Name
    Args:
        context (Context): Context object
        csp_machine_name (str): CSP Machine Instance Name
    Returns:
        ec2_instances (list[CSPMachineInstanceModel]): List of CSP Machine Instance objects
    """
    inventory_manager = context.inventory_manager
    csp_machine_instances: CSPMachineInstanceListModel = inventory_manager.get_csp_machine_instances()
    ec2_instances = [instance for instance in csp_machine_instances.items if csp_machine_name in instance.name]
    return ec2_instances


def get_csp_instance_by_name(context: Context, csp_machine_name: str) -> CSPMachineInstanceModel:
    """Get a CSP Machine Instance object by CSP Machine Instance Name
    Args:
        context (Context): Context object
        csp_machine_name (str): CSP Machine Instance Name
    Returns:
        ec2_instance (CSPMachineInstanceModel): CSP Machine Instance object
    """
    csp_machine_instances = get_csp_instances_by_name(context, csp_machine_name)
    ec2_instance = next(iter(csp_machine_instances))
    return ec2_instance


def get_csp_instances_by_tag(context: Context, tag: CSPTag, filter: str = "") -> list[CSPMachineInstanceModel]:
    """Get a list of CSP Machine Instance objects by CSP Tag
    Args:
        context (Context): Context object
        tag (CSPTag): Tag of CSP asset
        filter (str, optional): Parameter of how to filter the list of CSP Machine Instances. Defaults to "".
    Returns:
        list[CSPMachineInstanceModel]: List of CSP Machine Instance objects
    """
    csp_instances = get_csp_instances(context, filter=filter)
    return [
        instance for instance in csp_instances.items if instance.cspInfo.cspTags and tag in instance.cspInfo.cspTags
    ]


def csp_machine_instance_refresh(context: Context, csp_machine_id: str):
    """Refresh CSP Machine Instance by CSP Machine Instance ID & validate task is successful
    Args:
        context (Context): Context object
        csp_machine_id (str): CSP Machine Instance ID
    """
    task_id: str = context.inventory_manager.trigger_csp_machine_instance_sync(csp_machine_id=csp_machine_id)
    refresh_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    assert refresh_task_status.upper() == TaskStatus.success.value


def verify_csp_machine_tag_keys(
    csp_instances: CSPMachineInstanceListModel,
    tag_key_list: ItemList,
):
    """Verify CSP Instance Tag Keys
    Args:
        csp_instances (CSPMachineInstanceList): List of CSP Machine Instance objects
        tag_key_list (ItemList): List of Tag Keys
    """
    tags: list[CSPTag] = []
    if csp_instances:
        for csp_instance in csp_instances.items:
            tags: list[CSPTag] = csp_instance.cspInfo.cspTags
            if tags:
                verify_csp_tag_keys(tags=tags, tag_key_list=tag_key_list)


def verify_csp_machine_tag_values(context: Context, csp_instances: CSPMachineInstanceListModel, account_id: str):
    """Verify CSP Machine Instance Tag Values
    Args:
        context (Context): Context object
        csp_instances (CSPMachineInstanceList): List of CSP Machine Instance objects
        account_id (str): CSP Account ID
    """
    tags: list[CSPTag] = []
    if csp_instances:
        for csp_instance in csp_instances.items:
            tags: list[CSPTag] = csp_instance.cspInfo.cspTags
            if tags:
                verify_csp_tag_values(context=context, tags=tags, account_id=account_id)


def verify_csp_instance_volume_attachment_info(csp_volumes: CSPVolumeListModel, csp_instance: CSPMachineInstanceModel):
    """Verify CSP Instance's Volume Attachment Info
    Args:
        csp_volumes (CSPVolumeList): List of CSP Volume objects
        csp_instance (CSPMachineInstance): CSP Machine Instance object
    """
    if csp_instance:
        if csp_instance.volumeAttachmentInfo:
            for attachment in csp_instance.volumeAttachmentInfo:
                if csp_volumes:
                    for csp_volume in csp_volumes.items:
                        if attachment.attachedTo.name == csp_volume.id:
                            logger.info(
                                f"----- csp_instance_volume_attachment_info_name = {attachment.attachedTo.name} -----\n"
                                + f"csp_volume_name = {csp_volume.name}\n"
                            )
                            assert attachment.attachedTo.name in csp_volume.name
    else:
        logger.info(f"---- csp_instance = {csp_instance}\n")
        assert False


def get_csp_instance_by_ec2_instance_id(
    context: Context, ec2_instance_id: str, account_id: str = None
) -> Union[CSPMachineInstanceModel, None]:
    """
        Retrieve an Inventory Manager machine instance object by the provided EC2 instance ID.

        An `account_id` must be provided when it is possible for multiple accounts to contain the same
        asset IDs, such as when registering multiple accounts backed by LocalStack.  Otherwise, the
        results of this function are unpredictable, with the potential for collisions between unrelated tests
        running in parallel.

        An assertion failure will occur if the enumerated asset count does not equal one.  If this occurs,
        the caller likely did not specify an `account_id` filter.

    Args:
        context (Context): Test execution context
        ec2_instance_id (str): EC2 instance ID
        account_id (str, optional): Account ID

    Returns:
        Union[CSPMachineInstanceModel, None]: Returns None if instance not found else CSPMachineInstance object
    """
    filter = f"cspId eq '{ec2_instance_id}'"
    if account_id:
        filter += f" and accountInfo/id eq {account_id}"
    csp_machine_instances: CSPMachineInstanceListModel = get_csp_instances(context=context, filter=filter)
    if csp_machine_instances.total:
        assert csp_machine_instances.total == 1
        return csp_machine_instances.items[0]
    else:
        return None


def get_csp_instance_protection_jobs(context: Context, csp_instance_id: str) -> list[CspProtectionJobInfo]:
    """Get CSP Instance's Protection Jobs
    Args:
        context (Context): Context object
        csp_instance_id (str): CSP Instance ID
    Returns:
        list[CspProtectionJobInfo]: List of Protection Job Info
    """
    csp_instance = context.inventory_manager.get_csp_machine_instance_by_id(csp_machine_id=csp_instance_id)
    return csp_instance.protectionJobInfo


def wait_for_instance_protection_group_associations(
    context: Context, csp_id: str, account_id: str, protection_group_ids: list[str]
) -> CSPMachineInstanceModel:
    """Wait for CSP Instance Protection Group associations
    Args:
        context (Context): Context object
        csp_id (str): CSP Instance ID
        account_id (str): CSP Account ID
        protection_group_ids (list[str]): List of Protection Group IDs
    Returns:
        CSPMachineInstanceModel: CSP Machine Instance object
    """
    return _wait_for_asset_protection_group_associations(
        context=context,
        asset_type=AssetType.CSP_MACHINE_INSTANCE,
        csp_id=csp_id,
        account_id=account_id,
        protection_group_ids=protection_group_ids,
    )


def is_instance_in_list(instance_id: str, instance_list: list[CSPMachineInstanceModel]) -> bool:
    """Returns True if there exists instance with id instance_id in passed list of instance objects,
        else returns False

    Args:
        instance_id (str): Id of instance which has to be checked for presence in list
        instance_list (list[CSPMachineInstanceModel]): list of instance objects

    Returns:
        Bool: True if instance found in the list
    """
    for instance in instance_list:
        if instance.id == instance_id:
            return True
    return False


# endregion

# region CSP Volume


def csp_volume_refresh(context: Context, csp_volume_id: str):
    """Refresh CSP Volume by CSP Volume ID & validate task is successful
    Args:
        context (Context): Context object
        csp_volume_id (str): CSP Volume ID
    """
    task_id: str = context.inventory_manager.trigger_csp_volume_sync(csp_volume_id=csp_volume_id)
    refresh_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    assert refresh_task_status.upper() == TaskStatus.success.value


def get_csp_volumes(context: Context, sort: str = "name", filter: str = "", tag_filter: str = "") -> CSPVolumeListModel:
    """Get list of CSP Volume objects
    Args:
        context (Context): Context object
        sort (str, optional): Parameter of how to sort the list of CSP Volumes. Defaults to "name".
        filter (str, optional): Parameter of how to filter the list of CSP Volumes. Defaults to "".
        tag_filter (str, Optional): Parameter of what key/value tags to further filter the CSP Volumes. Defaults to "".
    Returns:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
    """
    csp_volumes: CSPVolumeListModel = context.inventory_manager.get_csp_volumes(
        sort=sort, filter=filter, tag_filter=tag_filter
    )
    return csp_volumes


def get_csp_volume_by_id(
    context: Context,
    csp_volume_id: str,
    response_code: int = requests.codes.ok,
) -> CSPVolumeModel:
    """Get CSP Volume by CSP Volume ID
    Args:
        context (Context): Context object
        csp_volume_id (str): CSP Volume ID
        response_code (int, optional): Expected response of API call. Defaults to requests.codes.ok.
    Returns:
        csp_volume (CSPVolumeModel): CSP Volume object
    """
    inventory_manager = context.inventory_manager
    csp_volume: CSPVolumeModel = inventory_manager.get_csp_volume_by_id(
        csp_volume_id=csp_volume_id,
        response_code=response_code,
    )
    return csp_volume


def get_csp_volumes_by_name(context: Context, csp_volume_name: str) -> list[CSPVolumeModel]:
    """Get list of CSP Volume objects by CSP Volume Name
    Args:
        context (Context): Context object
        csp_volume_name (str): CSP Volume Name
    Returns:
        ebs_instances (list[CSPVolumeModel]): List of CSP Volume objects
    """
    inventory_manager = context.inventory_manager
    csp_volume_instances: CSPVolumeListModel = inventory_manager.get_csp_volumes()
    ebs_instances = [instance for instance in csp_volume_instances.items if csp_volume_name in instance.name]
    return ebs_instances


def get_csp_volume_by_name(context: Context, csp_volume_name: str) -> CSPVolumeModel:
    """Get CSP Volume by CSP Volume Name
    Args:
        context (Context): Context object
        csp_volume_name (str): CSP Volume Name
    Returns:
        ebs_instance (CSPVolumeModel): CSP Volume object
    """
    csp_volume_instances = get_csp_volumes_by_name(context, csp_volume_name)
    ebs_instance = next(iter(csp_volume_instances))
    return ebs_instance


def get_csp_volume_generation(csp_volumes: CSPVolumeListModel, ebs_volume_id: str) -> int:
    """Get CSP Volume Generation by AWS EBS Volume ID
    Args:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        ebs_volume_id (str): AWS EBS Volume ID
    Returns:
        csp_volume.generation (int): CSP Volume generation value
    """
    if csp_volumes:
        for csp_volume in csp_volumes.items:
            if csp_volume.name == ebs_volume_id:
                return csp_volume.generation


def get_csp_volumes_by_tag(context: Context, tag: CSPTag, filter: str = "") -> list[CSPVolumeModel]:
    """Get list of CSP Volume objects by CSP Tag
    Args:
        context (Context): Context object
        tag (CSPTag): CSP Tag of CSP assets
        filter (str, optional): Parameter of how to filter the list of CSP Volumes. Defaults to "".
    Returns:
        list[CSPVolumeModel]: List of CSP Volume objects
    """
    csp_volumes = get_csp_volumes(context, filter=filter)
    return [volume for volume in csp_volumes.items if volume.cspInfo.cspTags and tag in volume.cspInfo.cspTags]


def get_csp_volume_by_cspinfo_id(csp_volumes: CSPVolumeListModel, ebs_volume_id: str) -> CSPVolumeModel:
    """Get CSP Volume object by AWS EBS Volume ID
    Args:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        ebs_volume_id (str): AWS EBS Volume ID
    Returns:
        csp_volume (CSPVolumeModel): CSP Volume object
    """
    if csp_volumes:
        for csp_volume in csp_volumes.items:
            if csp_volume.cspId == ebs_volume_id:
                return csp_volume


def verify_csp_volume_tag_keys(csp_volumes: CSPVolumeListModel, tag_key_list: ItemList):
    """Verify CSP Volume Tag Keys
    Args:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        tag_key_list (ItemList): List of Tag Keys
    """
    tags: list[CSPTag] = []
    if csp_volumes:
        for csp_volume in csp_volumes.items:
            tags: list[CSPTag] = csp_volume.cspInfo.cspTags
            if tags:
                verify_csp_tag_keys(tags=tags, tag_key_list=tag_key_list)


def verify_csp_volume_tag_values(context: Context, csp_volumes: CSPVolumeListModel, account_id: str):
    """Verify CSP Volume Tag Values
    Args:
        context (Context): Context object
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        account_id (str): CSP Account ID
    """
    tags: list[CSPTag] = []
    if csp_volumes:
        for csp_volume in csp_volumes.items:
            tags: list[CSPTag] = csp_volume.cspInfo.cspTags
            if tags:
                verify_csp_tag_values(context=context, tags=tags, account_id=account_id)


def verify_csp_volume_tag_add_against_ebs_volume(
    csp_volumes: CSPVolumeListModel, ebs_volume_id: str, ebs_volume_tags: list[CSPTag]
):
    """Verify CSP Volume Tags match AWS EBS Volume Tags
    Args:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        ebs_volume_id (str): AWS EBS Volume ID
        ebs_volume_tags (list[Tag]): List of AWS EBS Volume Tags
    """
    flag: int = 0
    tags: list[CSPTag] = get_csp_volume_by_cspinfo_id(
        csp_volumes=csp_volumes, ebs_volume_id=ebs_volume_id
    ).cspInfo.cspTags
    if tags:
        for tags_pair in tags:
            for ebs_tag_pair in ebs_volume_tags:
                if ebs_tag_pair.Key == tags_pair.key:
                    logger.info(
                        f"----- EBS Volume Tag = {ebs_tag_pair.Key}, {ebs_tag_pair.Value}"
                        + f" ----- CSP Volume Tag = {tags_pair.key}, {tags_pair.value}"
                    )
                    flag += 1
                    assert ebs_tag_pair.Value in tags_pair.value
        if flag != len(ebs_volume_tags):
            assert False
    else:
        logger.info(f"----- tags = {tags}\n")
        assert False


def verify_csp_volume_tag_delete_against_ebs_volume(
    csp_volumes: CSPVolumeListModel, ebs_volume_id: str, ebs_volume_tags: list[CSPTag]
):
    """Verify CSP Volume Tags was deleted to match AWS EBS Volume Tags
    Args:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        ebs_volume_id (str): AWS EBS Volume ID
        ebs_volume_tags (list[Tag]): List of AWS EBS Volume Tags
    """
    tags: list[CSPTag] = get_csp_volume_by_cspinfo_id(
        csp_volumes=csp_volumes, ebs_volume_id=ebs_volume_id
    ).cspInfo.cspTags
    if tags:
        for tags_pair in tags:
            for ebs_tag_pair in ebs_volume_tags:
                if ebs_tag_pair.Key == tags_pair.key:
                    logger.info(
                        f"----- EBS Volume Tag = {ebs_tag_pair.Key}, {ebs_tag_pair.Value} ----\n"
                        + f"CSP Volume Tag = {tags_pair.key}, {tags_pair.value}"
                    )
                    assert False
    else:
        logger.info(f"---- tags = {tags}\n")
        assert True


def verify_csp_volume_machine_instance_attachment_info(
    csp_volumes: CSPVolumeListModel, csp_instance: CSPMachineInstanceModel
):
    """Verify CSP Volume's Machine Instance Attachment Info
    Args:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        csp_instance (CSPMachineInstanceModel): CSP Machine Instance object
    """
    if csp_volumes:
        for csp_volume in csp_volumes.items:
            if csp_volume.machineInstanceAttachmentInfo:
                for instance_attachment in csp_volume.machineInstanceAttachmentInfo:
                    if csp_instance:
                        if instance_attachment.attachedTo.name == csp_instance.id:
                            logger.info(
                                f"----- csp_volume_machine_instance_name = {instance_attachment.attachedTo.name} -----"
                                + f"csp_instance_id = {csp_instance.id}\n"
                            )
                            assert instance_attachment.attachedTo.name in csp_instance.id
    else:
        logger.info(f"---- csp_volumes = {csp_volumes}\n")
        assert False


def verify_customer_id_in_csp_volumes(csp_volumes: CSPVolumeListModel, customer_id: str):
    """Verify AWS Customer ID in CSP Volumes
    Args:
        csp_volumes (CSPVolumeListModel): List of CSP Volume objects
        customer_id (str): CSP Customer ID
    """
    if csp_volumes:
        for csp_volume in csp_volumes.items:
            logger.info(f"---- customer_id = {csp_volume.customerId}\n")
            assert customer_id in csp_volume.customerId
    else:
        logger.info(f"---- csp_volumes = {csp_volumes}\n")
        assert False


def verify_ebs_present_csp_volumes(list_ebs: list, csp_volumes: CSPVolumeListModel):
    """Verify AWS EBS is present in CSP Volumes list
    Args:
        list_ebs (list): List of AWS EBS objects
        csp_volumes (CSPVolumeListModel): List of CSP Volumes
    """
    csp_volume_names = [volume.cspId for volume in csp_volumes.items]
    for ebs in list_ebs:
        # ebs.id is actually the name and should match when looking at the csp_volume_name
        logger.info(f" ----- ebs_name = {ebs.id}\n ----- csp_volume_name = {csp_volume_names}\n")
        assert ebs.id in csp_volume_names


def get_csp_volume_by_ebs_volume_id(
    context: Context, ebs_volume_id: str, account_id: str = None
) -> Union[CSPVolumeModel, None]:
    """
        Retrieve an Inventory Manager volume object by the provided EBS volume ID.

        An `account_id` must be provided when it is possible for multiple accounts to contain the same
        asset IDs, such as when registering multiple accounts backed by LocalStack.  Otherwise, the
        results of this function are unpredictable, with the potential for collisions between unrelated tests
        running in parallel.

        An assertion failure will occur if the enumerated asset count does not equal one.  If this occurs,
        the caller likely did not specify an `account_id` filter.

    Args:
        context (Context): Test execution context
        ebs_volume_id (str): EBS volume ID
        account_id (str, optional): Account ID

    Returns:
        Union[CSPVolumeModel, None]: Returns None if volume not found else CSPVolume object
    """
    filter = f"cspId eq '{ebs_volume_id}'"
    if account_id:
        filter += f" and accountInfo/id eq {account_id}"
    csp_volumes: CSPVolumeListModel = get_csp_volumes(context=context, filter=filter)
    if csp_volumes.total:
        assert csp_volumes.total == 1
        return csp_volumes.items[0]
    else:
        return None


def get_csp_volume_protection_jobs(context: Context, csp_volume_id: str) -> list[CspProtectionJobInfo]:
    """Get CSP Volume's Protection Jobs
    Args:
        context (Context): Context object
        csp_volume_id (str): CSP Volume ID
    Returns:
        list[CspProtectionJobInfo]: List of Protection Job Info
    """
    csp_volume = context.inventory_manager.get_csp_volume_by_id(csp_volume_id=csp_volume_id)
    return csp_volume.protectionJobInfo


def is_volume_in_list(ebs_id: str, volume_list: list[CSPVolumeModel]) -> bool:
    """Returns True if there exists volume with id ebs_id in passed list of volume objects,
        else returns False

    Args:
        ebs_id (str): Id of volume which has to be checked for presence in list
        volume_list (list[CSPVolumeModel]): list of volume objects

    Returns:
        Bool: True if volume is found in the list
    """
    for volume in volume_list:
        if volume.id == ebs_id:
            return True
    return False


def wait_for_volume_protection_group_associations(
    context: Context, csp_id: str, account_id: str, protection_group_ids: list[str]
) -> CSPVolumeModel:
    """Wait for CSP Volume Protection Group associations
    Args:
        context (Context): Context object
        csp_id (str): CSP Volume ID
        account_id (str): CSP Account ID
        protection_group_ids (list[str]): List of Protection Group IDs
    Returns:
        CSPVolumeModel: CSP Volume object
    """
    return _wait_for_asset_protection_group_associations(
        context=context,
        asset_type=AssetType.CSP_VOLUME,
        csp_id=csp_id,
        account_id=account_id,
        protection_group_ids=protection_group_ids,
    )


# endregion

# region Tags


def get_tag_keys(context: Context, account_id: str, regions: str = "us-east-1") -> ItemList:
    """Get Tag Keys by CSP Account ID and region
    Args:
        context (Context): Context object
        account_id (str): CSP Account ID
        regions (str, optional): Regions of targeted area. Defaults to "us-east-1".
    Returns:
        tag_keys (ItemList): Item list of tag keys
    """
    inventory_manager = context.inventory_manager
    tag_keys: ItemList = inventory_manager.get_tag_keys(account_id=account_id, regions=regions)
    return tag_keys


def get_tag_values(context: Context, key: str, account_id: str, regions: str = "us-east-1") -> TagKeyValue:
    """Get Tag Values by Tag Key, CSP Account ID, and region
    Args:
        context (Context): Context object
        key (str): Tag Key
        account_id (str): CSP Account ID
        regions (str, optional): Regions of targeted area. Defaults to "us-east-1".
    Returns:
        tag_key_values (TagKeyValue): Tag key values
    """
    inventory_manager = context.inventory_manager
    tag_key_values: TagKeyValue = inventory_manager.get_tag_key_values(key=key, account_id=account_id, regions=regions)
    return tag_key_values


# Tag class -> models.atlantia.common_objects
def verify_csp_tag_keys(tags: list[CSPTag], tag_key_list: ItemList):
    """Verify CSP Tag Keys
    Args:
        tags (list[CSPTag]): List of CSP Tags
        tag_key_list (ItemList): List of Tag Keys
    """
    tag_keys = [tag.key for tag in tags]
    result = all(item in tag_key_list.items for item in tag_keys)
    logger.info(f"-------Tag Keys = {tag_keys}------- Tag Keys from API = {tag_key_list.items}")
    assert result


# Tag class -> models.atlantia.common_objects
def verify_csp_tag_values(context: Context, tags: list[CSPTag], account_id: str):
    """Verify CSP Tag Values
    Args:
        context (Context): Context object
        tags (list[CSPTag]): List of CSP Tags
        account_id (str): CSP Account ID
    """
    for tag in tags:
        tag_key_values: TagKeyValue = get_tag_values(context=context, key=tag.key, account_id=account_id)
        tag_values: ItemList = tag_key_values.values
        logger.info(f"-------Tag Values= {tag_values}-------Tag Values from API={tag_key_values.values}")
        assert tag.value in tag_values


def add_tags_to_different_aws_resources_by_id_and_refresh_inventory(
    context: Context,
    aws: AWS,
    aws_resource_ids_list: list[str],
    tags_list: list[Tag],
    account_id: str,
):
    """Add Tags to different AWS Resources by AWS Resource ID and Refresh Inventory

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        aws_resource_ids_list (list[str]): List of AWS Resource IDs
        tags_list (list[Tag]): List of Tags
        account_id (str): CSP Account ID
    """
    aws.ec2.create_tags_to_different_aws_resource_types_by_id(
        resource_ids_list=aws_resource_ids_list, tags_list=tags_list
    )
    account_inventory_refresh(context=context, account_id=account_id)


def delete_tags_from_different_aws_resources_by_id_and_refresh_inventory(
    context: Context,
    aws: AWS,
    aws_resource_ids_list: list[str],
    tags_list: list[Tag],
    account_id: str,
):
    """Delete AWS Tag from AWS Resource and Refresh Inventory
    Args:
        context (Context): Context object
        aws (AWS): AWS object
        aws_resource_ids_list (list[str]): List of AWS Resource IDs, ex: EBS Volume ID, Subnet ID, VPC ID, etc
        tags_list (list[Tag]): List of AWS Tags
        account_id (str): CSP Account ID
    """
    aws.ec2.remove_tags_from_different_aws_resources_by_id(
        aws_resource_id_list=aws_resource_ids_list, tags_list=tags_list
    )
    account_inventory_refresh(context=context, account_id=account_id)


def update_assets_tags(
    context: Context,
    csp_machine_instance_ids: list[str] = list(),
    csp_volume_ids: list[str] = list(),
    tags_to_add: list[CSPTag] = list(),
    tags_to_remove: list[CSPTag] = list(),
    wait_for_task: bool = True,
    expected_status_code=requests.codes.accepted,
) -> list:
    """
    Add and remove specified tags on sets of EC2 instances and EBS volumes.

    Args:
        context (Context): Context object
        csp_machine_instance_ids (list[str]): List of CSP Machine Instance IDs. Defaults to empty list
        csp_volume_ids (list[str]): List of CSP Volume IDs. Defaults to empty list
        tags_to_add (list[CSPTag]): List of Tags to add. Defaults to empty list
        tags_to_remove (list[CSPTag]): List of Tags to remove. Defaults to empty list
        wait_for_task (bool, optional): Boolean value to wait of the task. Defaults to True.
        expected_status_code (requests.codes): Expected response code from the API response.

    Returns:
        task_id_list (list): List of task IDs
    """
    if tags_to_remove and type(tags_to_remove[0]) is CSPTag:
        tags_to_remove = [tag.key for tag in tags_to_remove]

    payload = PostUpdateCSPTagsModel(tags_to_add, tags_to_remove)
    task_id_list = []
    if csp_machine_instance_ids:
        task_id = context.inventory_manager.update_csp_tags(
            asset_type=AssetType.CSP_MACHINE_INSTANCE,
            asset_ids=csp_machine_instance_ids,
            post_update_csp_tags=payload,
            expected_status_code=expected_status_code,
        )
        assert isinstance(task_id, str), f"Error updating tags to the EC2 instances {task_id}"
        task_id_list.append(task_id)

    if csp_volume_ids:
        task_id = context.inventory_manager.update_csp_tags(
            asset_type=AssetType.CSP_VOLUME,
            asset_ids=csp_volume_ids,
            post_update_csp_tags=payload,
            expected_status_code=expected_status_code,
        )
        assert isinstance(task_id, str), f"Error updating tags to the EBS volumes {task_id}"
        task_id_list.append(task_id)

    if wait_for_task:
        for task_id in task_id_list:
            tasks.wait_for_task(
                task_id=task_id,
                user=context.user,
                timeout=TimeoutManager.health_status_timeout,
            )

    return task_id_list


def verify_assets_tags(
    context: Context,
    csp_machine_instance_ids: list[str] = None,
    csp_volume_ids: list[str] = None,
    csp_tags_included: list[CSPTag] = None,
    csp_tags_not_included: list[CSPTag] = None,
):
    """Verify Assets' Tags
    Args:
        context (Context): Context object
        csp_machine_instance_ids (list[str], optional): List of CSP Machine Instance IDs. Defaults to None.
        csp_volume_ids (list[str], optional): List of CSP Volume IDs. Defaults to None.
        csp_tags_included (list[CSPTag], optional): List of CSP Tags to include. Defaults to None.
        csp_tags_not_included (list[CSPTag], optional): List of CSP Tags to not include. Defaults to None.
    """
    asset_list = []
    if csp_machine_instance_ids:
        for csp_machine_id in csp_machine_instance_ids:
            asset = get_csp_instance_by_id(context=context, csp_machine_id=csp_machine_id)
            asset_list.append(asset)

    if csp_volume_ids:
        for csp_volume_id in csp_volume_ids:
            asset = get_csp_volume_by_id(context=context, csp_volume_id=csp_volume_id)
            asset_list.append(asset)

    asset: Union[CSPMachineInstanceModel, CSPVolumeModel]
    for asset in asset_list:
        if asset:
            actual_csp_tag_keys_values = []
            expected_csp_tag_keys_values = []
            not_expected_csp_tag_keys_values = []
            for actual_tag in asset.cspInfo.cspTags:
                actual_csp_tag_keys_values.append(actual_tag.key)
                actual_csp_tag_keys_values.append(actual_tag.value)

            if csp_tags_included:  # test case can have only remove tags
                for expected_tag in csp_tags_included:
                    expected_csp_tag_keys_values.append(expected_tag.key)
                    expected_csp_tag_keys_values.append(expected_tag.value)

            if csp_tags_not_included:  # test case can have only add tags
                for not_expected_tag in csp_tags_not_included:
                    not_expected_csp_tag_keys_values.append(not_expected_tag.key)
                    not_expected_csp_tag_keys_values.append(not_expected_tag.value)

            if csp_tags_included:
                assert set(expected_csp_tag_keys_values).issubset(
                    set(actual_csp_tag_keys_values)
                ), f"{asset.id} does not have {csp_tags_included} in csp tags: {asset.cspInfo.cspTags}"
            if csp_tags_not_included:
                assert not set(not_expected_csp_tag_keys_values).issubset(
                    set(actual_csp_tag_keys_values)
                ), f"{asset.id} should have {csp_tags_not_included} in csp tags: {asset.cspInfo.cspTags}"


# endregion

# region Subnets


def get_subnets(
    context: Context, account_id: str, response_code: int = requests.codes.ok, filter: str = "", sort: str = ""
) -> CSPSubnetListModel:
    """Get Subnets by CSP Account ID
    Args:
        context (Context): Context object
        account_id (str): CSP Account ID
        response_code (int, optional): Expected response code of API call. Defaults to requests.codes.ok.
        filter (str, optional): Parameter of how to filter the list of subnets. Defaults to "".
        sort (str, optional): Parameter of how to sort the list of subnets. Defaults to "".
    Returns:
        subnets (CSPSubnetListModel): List of Subnets
    """
    inventory_manager = context.inventory_manager
    subnets: CSPSubnetListModel = inventory_manager.get_subnets(
        account_id=account_id, filter=filter, sort=sort, response_code=response_code
    )
    logger.info(subnets)
    return subnets


def verify_all_ec2_subnets_present_in_csp_subnets(ec2_subnets: list, csp_subnets: CSPSubnetListModel):
    """Verify EC2 Subnets are present in CSP Subnet list
    Args:
        ec2_subnets (list): List of AWS EC2 Subnets
        csp_subnets (CSPSubnetListModel): List of CSP Subnets
    """
    for ec2_subnet in ec2_subnets:
        csp_subnets_ids = [subnet.id for subnet in csp_subnets.items]
        logger.info(f" ----- ec2_vpc_id = {ec2_subnet.id} ----- csp_vpcs = {csp_subnets.items} ----- ")
        assert ec2_subnet.id in csp_subnets_ids


# endregion

# region VPCs


def get_vpcs(
    context: Context, account_id: str, response_code: int = requests.codes.ok, filter: str = "", sort: str = ""
) -> CSPVPCListModel:
    """Get VPCs by CSP Account ID
    Args:
        context (Context): Context object
        account_id (str): CSP Account ID
        response_code (int, optional): Expected response code of API call. Defaults to requests.codes.ok.
        filter (str, optional): Parameter of how to filter the list of VPCs. Defaults to "".
        sort (str, optional): Parameter of how to sort the list of VPCs. Defaults to "".
    Returns:
        vpcs (CSPVPCListModel): List of VPCs
    """
    inventory_manager = context.inventory_manager
    vpcs: CSPVPCListModel = inventory_manager.get_vpcs(
        account_id=account_id, filter=filter, sort=sort, response_code=response_code
    )
    logger.info(vpcs)
    return vpcs


def verify_all_ec2_vpcs_present_in_csp_vpcs(ec2_vpcs: list, csp_vpcs: CSPVPCListModel):
    """Verify EC2 VPCs are present in CSP VPC list
    Args:
        ec2_vpcs (list): List of AWS EC2 VPCs
        csp_vpcs (CSPVPCListModel): List of CSP VPCs
    """
    for ec2_vpc in ec2_vpcs:
        csp_vpc_ids = [vpc.id for vpc in csp_vpcs.items]
        logger.info(f" ----- ec2_vpc_id = {ec2_vpc.id} ----- csp_vpcs = {csp_vpcs.items} ----- ")
        assert ec2_vpc.id in csp_vpc_ids


# endregion

# region Protection Groups


def create_custom_protection_group(
    context: Context,
    post_custom_protection_group: PostCustomProtectionGroupModel = None,
    asset_ids: list[str] = None,
    csp_account_id: str = None,
    asset_type: AssetType = None,
    group_name: str = None,
    region: Union[AWSRegionZone, AZRegion] = None,
    subscription_ids: list[str] = None,
    **kwargs,
) -> Union[str, ProtectionGroupModel, GLCPErrorResponse]:
    """Create a CustomProtectionGroup either by providing a PostCustomProtectionGroupModel payload,
    or the values necessary to create a PostCustomProtectionGroupModel payload.

    Args:
        context (Context): The test Context
        post_custom_protection_group (PostCustomProtectionGroupModel, optional): A populated PostCustomProtectionGroupModel payload. Defaults to None.
        asset_ids (list[str], optional): A list of CSP Asset IDs. Defaults to None.
        csp_account_id (str, optional): The CSP Account ID. Defaults to None.
        asset_type (AssetType, optional): The Asset Type. Defaults to None.
        group_name (str, optional): The name to give to the Protection Group. Defaults to None.
        region (AWSRegionZone | AZRegion, optional): The region to assign to the Protection Group. Defaults to None.
        subscription_ids (list[str], optional): A list CSP subsription. Defaults to None. It must contain a single
        subscription when 'accountIds' contains an Azure account.
        **kwargs: variable parameter list included to keep this method backward compatible as it is referenced by
        multiple tests. e.g. is_error=True needed for negative test cases

    Returns:
        ProtectionGroupModel: The new ProtectionGroup from Inventory Manager or task_id in case of failures
    """
    protection_group_payload = post_custom_protection_group

    # if not provided, create payload
    if not protection_group_payload:
        protection_group_payload = PostCustomProtectionGroupModel(
            account_ids=[csp_account_id],
            static_member_ids=asset_ids,
            name=group_name,
            csp_regions=[region.value],
            asset_type=asset_type.value,
            subscription_ids=subscription_ids,
        )

    # create_protection_group() returns: tasks.get_task_id(response)
    task_id = context.inventory_manager.create_protection_group(post_protection_group=protection_group_payload)

    # Note: the status is returned lowercase; TaskStatus enum is uppercase
    task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)

    # If is_error kwargs is passed, the task status is supposed to be FAILED and we should return
    # without further validations
    if "is_error" in kwargs and kwargs["is_error"] is True:
        assert task_status.upper() == TaskStatus.failed.value
        return task_id

    assert task_status.upper() == TaskStatus.success.value

    # Get created protection group ID from completed task
    protection_group_id = tasks.get_task_source_resource_uuid(
        task_id=task_id,
        user=context.user,
        source_resource_type=CSPResourceType.PROTECTION_GROUP_RESOURCE_TYPE.value,
    )
    protection_group: ProtectionGroupModel = context.inventory_manager.get_protection_group_by_id(
        protection_group_id=protection_group_id
    )
    return protection_group


def create_dynamic_protection_group(
    context: Context,
    post_dynamic_protection_group: PostDynamicProtectionGroupModel = None,
    filter_tags: list[CSPTag] = None,
    csp_account_id: str = None,
    asset_type: AssetType = None,
    group_name: str = None,
    region: Union[AWSRegionZone, AZRegion] = None,
    subscription_ids: list[str] = None,
    **kwargs,
) -> Union[str, ProtectionGroupModel, GLCPErrorResponse]:
    """Create a DynamicProtectionGroup either by providing a PostDynamicProtectionGroupModel payload,
    or the values necessary to create a PostDynamicProtectionGroupModel payload.

    Args:
        context (Context): The test Context
        post_dynamic_protection_group(PostDynamicProtectionGroupModel,optional):populated PostDynamicProtectionGroupModel payload. Defaults to None.
        filter_tags (list[CSPTag], optional): A list of CSPTag objects. Defaults to None.
        csp_account_id (str, optional): The CSP Account ID. Defaults to None.
        asset_type (AssetType, optional): The Asset Type. Defaults to None.
        group_name (str, optional): The name to give to the Protection Group. Defaults to None.
        region (AWSRegionZone | AZRegion, optional): The region to assign to the Protection Group. Defaults to None.
        subscription_ids (list[str], optional): A list CSP subsription. Defaults to None. It must contain a single
        subscription when 'accountIds' contains an Azure account.
        **kwargs: variable parameter list included to keep this method backward compatible as it is referenced by
        multiple tests. e.g. is_error=True needed for negative test cases

    Returns:
        ProtectionGroupModel: The new ProtectionGroup from Inventory Manager or task_id in case of failures
    """
    logger.info("Creating Protection Group")
    protection_group_payload = post_dynamic_protection_group

    # if not provided, create payload
    if not protection_group_payload:
        dynamic_member_filter = DynamicMemberFilterModel(filter_tags, ProtectionGroupDynamicFilterType.CSP_TAG.value)
        protection_group_payload = PostDynamicProtectionGroupModel(
            account_ids=[csp_account_id],
            name=group_name,
            csp_regions=[region.value],
            dynamic_member_filter=dynamic_member_filter,
            asset_type=asset_type.value,
            subscription_ids=subscription_ids,
        )

    # create_protection_group() returns: tasks.get_task_id(response)
    task_id = context.inventory_manager.create_protection_group(post_protection_group=protection_group_payload)

    # Note: the status is returned lowercase; TaskStatus enum is uppercase
    task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)

    # If is_error kwargs is passed, the task status is supposed to be FAILED and we should return
    # without further validations
    if "is_error" in kwargs and kwargs["is_error"] is True:
        assert task_status.upper() == TaskStatus.failed.value
        return task_id

    assert task_status.upper() == TaskStatus.success.value
    logger.info("Protection Group created")

    # Get created protection group ID from completed task
    protection_group_id = tasks.get_task_source_resource_uuid(
        task_id=task_id,
        user=context.user,
        source_resource_type=CSPResourceType.PROTECTION_GROUP_RESOURCE_TYPE.value,
    )
    protection_group: ProtectionGroupModel = context.inventory_manager.get_protection_group_by_id(
        protection_group_id=protection_group_id
    )
    return protection_group


def update_custom_protection_group_static_members(
    context: Context,
    protection_group_id: str,
    post_custom_protection_group_static_members: PostCustomProtectionGroupStaticMembersModel = None,
    list_asset_ids_added: list = None,
    list_asset_ids_removed: list = None,
):
    """Update the static members of a custom Protection Group
    Args:
        context (Context): Context object
        protection_group_id (str): CSP Protection Group ID
        post_custom_protection_group_static_members (PostCustomProtectionGroupStaticMembersModel, optional): Post
            Custom PG object. Defaults to None.
        list_asset_ids_added (list, optional): List of CSP Asset IDs that will be newly added. Defaults to None.
        list_asset_ids_removed (list, optional): List of CSP Asset IDs that will be removed. Defaults to None.
    """
    if not post_custom_protection_group_static_members:
        post_custom_protection_group_static_members = PostCustomProtectionGroupStaticMembersModel(
            static_members_added=list_asset_ids_added,
            static_members_removed=list_asset_ids_removed,
        )

    task_id: str = context.inventory_manager.update_custom_protection_group_static_members(
        protection_group_id=protection_group_id,
        post_custom_protection_group_static_members=post_custom_protection_group_static_members,
    )

    # Note: the status is returned lowercase; TaskStatus enum is uppercase
    task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    assert task_status.upper() == TaskStatus.success.value


def delete_protection_group(
    context: Context,
    protection_group_id: str,
    response_status_code: int = requests.codes.accepted,
) -> Union[str, ErrorResponse]:
    """Delete a Protection Group from Inventory Manager
    Args:
        context (Context): The test Context.
        protection_group_id (str): The ID of the Protection Group to delete.
        response_status_code (int, optional): The expected response code. Defaults to requests.codes.accepted.
    Returns:
        ErrorResponse object if the status_code from the delete() call is NOT "requests.codes.accepted".
        str containing a Task ID if the status_code from the delete() call is "requests.codes.accepted".
    """
    response = context.inventory_manager.delete_protection_group(
        protection_group_id=protection_group_id,
        response_status_code=response_status_code,
    )
    # if 'str' - then it's a task_id
    if isinstance(response, str):
        tasks.wait_for_task(task_id=response, user=context.user, timeout=TimeoutManager.task_timeout)
    return response


def delete_protection_groups(context: Context, protection_group_ids: list[str]):
    """Delete from Inventory Manager the Protection Groups in the provided list

    Args:
        context (Context): The test Context.
        protection_group_ids (list[str]): A list of Protection Group IDs to delete.
    """
    logger.info(f"Deleting protection groups {context.protection_group_ids}")
    for id in protection_group_ids:
        if id:
            delete_protection_group(context=context, protection_group_id=id)


def get_protection_group_by_name_and_validate(
    context: Context, pg_name: str, validate_pg_found: bool = True
) -> Union[ProtectionGroupModel, None]:
    """Get CSP Protection Group by Name
    Args:
        context (Context): Context object
        pg_name (str): CSP Protection Group Name
        validate_pg_found (bool): True | False to validate if Protection Group is found via Assertion. Defaults to True
    Returns:
        ProtectionGroupModel | None: CSP Protection Group object or None (used by negative test cases)
    """
    # get Protection Group filtered on name: 'pg_name'
    name_filter: str = f"name eq '{pg_name}'"
    pg_list: ProtectionGroupListModel = context.inventory_manager.get_protection_groups(filter=name_filter)

    if validate_pg_found:
        assert pg_list.total > 0, f"Protection Group '{pg_name}' not found"
        return pg_list.items[0]
    else:
        if pg_list.total == 0:
            logger.info(f"Did not find Protection Group: {pg_name}")
            return None
        else:
            return pg_list.items[0]


def create_custom_aws_protection_group(
    context: Context,
    name: str,
    type: AssetType,
    asset_list: list[str],
    region: str = None,
    csp_account_name: str = None,
) -> str:
    """Create Custom Protection Group
    Args:
        context (Context): Context object
        name (str): Protection Group Name
        type (AssetType): Asset Type for Protection Group
        asset_list (list[str]): Asset ID list for Protection Group
        region (str, optional): Targeted region based off of assets. Defaults to None.
        csp_account_name (str, optional): CSP Account Name. Defaults to None.
    Returns:
        str: Protection Group ID
    """
    if not region:
        region = context.aws_one_region_name
    if not csp_account_name:
        csp_account_name = context.aws_one_account_name
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name=csp_account_name)
    payload = PostCustomProtectionGroupModel(
        [csp_account.id],
        type.value,
        name,
        [region],
        asset_list,
    )
    task_id = context.inventory_manager.create_protection_group(payload)
    create_pg_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    assert create_pg_task_status.upper() == TaskStatus.success.value
    pg_id = get_protection_group_by_name_and_validate(context=context, pg_name=name).id
    return pg_id


def create_automatic_aws_protection_group(
    context: Context,
    name: str,
    type: AssetType,
    key_list: list[str] = ["test_id"],
    value_list: list[str] = ["default"],
    filter_type: str = "CSP_TAG",
    region: str = None,
    csp_account_name: str = None,
) -> str:
    """Create Automatic Protection Group
    Args:
        context (Context): Context object
        name (str): Protection Group Name
        type (AssetType): Asset type for Protection Group
        key_list (list[str], optional): CSP Tag Key list. Defaults to ["test_id"].
        value_list (list[str], optional): CSP Tag Value list. Defaults to ["default"].
        filter_type (str, optional): Targeted filter. Defaults to "TAG".
        region (str, optional): Targeted region based off of assets. Defaults to None.
        csp_account_name (str, optional): CSP Account Name. Defaults to None.
    Returns:
        str: Protection Group ID
    """
    if not region:
        region = context.aws_one_region_name
    if not csp_account_name:
        csp_account_name = context.aws_one_account_name
    tags: list = []
    for key, value in zip(key_list, value_list):
        tags.append(CSPTag(key=key, value=value))
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name=csp_account_name)
    payload = PostDynamicProtectionGroupModel(
        [csp_account.id],
        name,
        [region],
        DynamicMemberFilterModel(tags, filter_type),
        asset_type=type.value,
    )
    task_id = context.inventory_manager.create_protection_group(payload)
    create_pg_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    assert create_pg_task_status.upper() == TaskStatus.success.value
    pg_id = get_protection_group_by_name_and_validate(context=context, pg_name=name).id
    return pg_id


def validate_protection_group_asset_count(context: Context, protection_group_name: str, num_assets_expected: int):
    """Validate Protection Group's Asset Count
    Args:
        context (Context): Context object
        protection_group_name (str): Protection Group Name
        num_assets_expected (int): Expected number of Assets
    """
    logger.info(f"Getting {protection_group_name}")
    protection_group = get_protection_group_by_name_and_validate(
        context=context,
        pg_name=protection_group_name,
    )
    # group should have "num_assets_expected" members
    assert protection_group.assetCount == num_assets_expected, (
        f"{protection_group_name} was expected to have {num_assets_expected} members, but instead has: "
        + f"{protection_group.assetCount}"
    )


def validate_protection_groups_asset_count(
    context: Context,
    num_ec2_assets_expected: int,
    num_ebs_assets_expected: int,
    protection_group_ec2_name: str,
    protection_group_ebs_name: str,
):
    """Validate Protection Groups' Asset Counts
    Args:
        context (Context): Context object
        num_ec2_assets_expected (int): Expected number of EC2 assets
        num_ebs_assets_expected (int): Expected number of EBS assets
        protection_group_ec2_name (str): EC2 Protection Group Name
        protection_group_ebs_name (str): EBS Protection Group Name
    """
    # Instances
    validate_protection_group_asset_count(
        context,
        protection_group_name=protection_group_ec2_name,
        num_assets_expected=num_ec2_assets_expected,
    )
    # Volumes
    validate_protection_group_asset_count(
        context,
        protection_group_name=protection_group_ebs_name,
        num_assets_expected=num_ebs_assets_expected,
    )


def get_protection_group_protection_jobs(context: Context, protection_group_id: str) -> list[ProtectionJobInfoModel]:
    """Get Protection Group's Protection Jobs
    Args:
        context (Context): Context object
        protection_group_id (str): Protection Group ID
    Returns:
        list[ProtectionJobInfoModel]: List of Protection Job Info
    """
    protection_group = context.inventory_manager.get_protection_group_by_id(protection_group_id=protection_group_id)
    return protection_group.protectionJobInfo


def get_protection_group_by_id(
    context: Context, protection_group_id: str, expected_status_code: int = requests.codes.ok
) -> Union[ProtectionGroupModel, GLCPErrorResponse]:
    """Get Protection Group info by id
    Args:
        context (Context): Context object
        protection_group_id (str): Protection Group ID
        expected_status_code(int): expected status code 'ok' by default
    Returns:
        protection_group(ProtectionGroup or GLCPErrorResponse): Protection group Info
    """
    protection_group = context.inventory_manager.get_protection_group_by_id(
        protection_group_id=protection_group_id, expected_status_code=expected_status_code
    )
    return protection_group


def is_asset_in_protection_group(
    protection_group_info: list[ObjectNameResourceTypeId],
    protection_group_id: str,
    protection_group_name: str,
) -> bool:
    """Check if Asset is in CSP Protection Group
    Args:
        protection_group_info (list[ObjectNameResourceType]): List of Protection Group Info
        protection_group_id (str): CSP Protection Group ID
        protection_group_name (str): CSP Protection Group Name
    Returns:
        bool: True | False if Asset is in the Protection Group
    """
    for protection_group in protection_group_info:
        if protection_group_id in protection_group.resource_uri and protection_group_name in protection_group.name:
            return True
    return False


def _wait_for_asset_protection_group_associations(
    context: Context,
    asset_type: AssetType,
    csp_id: str,
    account_id: str,
    protection_group_ids: list[str],
) -> Union[CSPMachineInstanceModel, CSPVolumeModel]:
    """
        As detailed in DCS-5787, after successful completion of an asset refresh, that asset's protection group
        associations could be delayed if there is an account sync occurring in parallel.  This function waits
        for the asset to have the expected protection group associations.

        TODO:  When or if the timing issue in Inventory Manager is resolved, the use of this function should
        be removed from the functional tests.

    Args:
        context (Context): test execution context
        asset_type (AssetType): aws asset type (AssetType.CSP_MACHINE_INSTANCE or AssetType.CSP_VOLUME)
        csp_id (str): aws asset csp id
        account_id (str): account ID
        protection_group_ids (list[str]): asset expected to be a member of these protection group IDs

    Returns:
        Union[CSPMachineInstanceModel, CSPVolumeModel]: last retrieved asset
    """
    asset: Union[CSPMachineInstanceModel, CSPVolumeModel] = None

    # Wait function returns True when the asset's protection groups meet expectations
    def _wait_protection_group_association():
        nonlocal asset
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            asset = get_csp_instance_by_ec2_instance_id(context=context, ec2_instance_id=csp_id, account_id=account_id)
        else:
            asset = get_csp_volume_by_ebs_volume_id(context=context, ebs_volume_id=csp_id, account_id=account_id)
        return {x.resourceUri for x in asset.protectionGroupInfo} == {
            AssetTypeURIPrefix.PROTECTION_GROUPS_RESOURCE_URI_PREFIX.value + x for x in protection_group_ids
        }

    try:
        wait(_wait_protection_group_association, timeout_seconds=120, sleep_seconds=1)
    except TimeoutExpired:
        raise TimeoutError(
            f"Protection group association mismatch, protection_group_ids={protection_group_ids}, asset={asset}"
        )

    # Return last retrieved asset
    return asset


def verify_protection_group_and_policy_of_assets(
    context: Context, pg_name: str, protection_policy_name: str, pg_id: str, asset_list: list[str], type: AssetType
):
    """Verifies if assets are protected by expected protection group/protection policy combination
    Args:
        context (Context): Context object
        pg_name (str): Protection group name
        protection_policy_name (str): Name of protection policy
        pg_id (str): Protection group id
        asset_list (list[str]): List of asset ids which need to be verified
        type (AssetType): Type of assets ex. either AssetType.CSP_MACHINE_INSTANCE or AssetType.CSP_VOLUME
    """
    for asset in asset_list:
        if type == AssetType.CSP_MACHINE_INSTANCE:
            asset_instance = get_csp_instance_by_id(context=context, csp_machine_id=asset)
        elif type == AssetType.CSP_VOLUME:
            asset_instance = get_csp_volume_by_id(context=context, csp_volume_id=asset)
        protection_group_info = asset_instance.protectionGroupInfo
        assert is_asset_in_protection_group(
            protection_group_info, protection_group_id=pg_id, protection_group_name=pg_name
        ), f"Unable to find asset {asset_instance.name} in {pg_name}"
        protection_job_list = asset_instance.protectionJobInfo
        protection_policy_info_list = [protection_job.protection_policy_info for protection_job in protection_job_list]
        assert is_asset_protected_by_policy(
            protection_policy_info_list, policy_name=protection_policy_name
        ), f"Unable to verify if asset {asset_instance.name} is protected by policy {protection_policy_name}"


# endregion

# region Asset State


def wait_for_asset_to_be_deleted(
    context: Context,
    asset_csp_id: str,
    asset_type: AssetType,
    account_id: str = None,
) -> bool:
    """
    This utility waits for an asset to be deleted from Inventory Manager with a periodic
    check of 1 second for a maximum of 120 seconds.

    Args:
        context (Context):  aws connection context
        asset_csp_id (str): aws assets csp id
        asset_type (AssetType): Asset type i.e CSPVolume or CSPMachineInstance
        account_id (str): CSP Account ID

    Returns:
        bool: True | False if Assets were deleted
    """

    def _wait_for_asset_deletion():
        filter = f"cspId eq '{asset_csp_id}'"
        if account_id:
            filter += f" and accountInfo/id eq {account_id}"
        if asset_type == AssetType.CSP_VOLUME:
            csp_volumes: CSPVolumeListModel = context.inventory_manager.get_csp_volumes(filter=filter)
            return csp_volumes.total == 0
        elif asset_type == AssetType.CSP_MACHINE_INSTANCE:
            csp_machine_instances: CSPMachineInstanceListModel = context.inventory_manager.get_csp_machine_instances(
                filter=filter
            )
            return csp_machine_instances.total == 0

    # wait for Asset to be removed from Inventory Manager
    wait(_wait_for_asset_deletion, timeout_seconds=120, sleep_seconds=1)


def get_asset_state(context: Context, asset_id: str, asset_type: AssetType) -> str:
    """Get CSP Asset State
    Args:
        context (Context): Context object
        asset_id (str): CSP Asset ID
        asset_type (AssetType): CSP Asset type
    Returns:
        str: CSP Asset state
    """
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        asset = get_csp_instance_by_id(context, asset_id)
    if asset_type == AssetType.CSP_VOLUME:
        asset = get_csp_volume_by_id(context, asset_id)
    return asset.state


def validate_asset_state(context: Context, asset_id: str, asset_type: AssetType, expected_state: State):
    """Validate Asset State
    Args:
        context (Context): Context object
        asset_id (str): CSP Asset ID
        asset_type (AssetType): CSP Asset Type
        expected_state (State): Expected state of Asset
    """
    state = get_asset_state(context=context, asset_id=asset_id, asset_type=asset_type)
    assert state == expected_state.value, f"Expected state: {expected_state.value} does not match actual state: {state}"


# endregion

# region Asset Protection Status


def get_asset_protection_status(context: Context, asset_id: str, asset_type: AssetType) -> str:
    """Get Asset Protection Status
    Args:
        context (Context): Context object
        asset_id (str): CSP Asset ID
        asset_type (AssetType): CSP Asset Type
    Returns:
        status (str): Protection Status of Asset
    """
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        asset = get_csp_instance_by_id(context, asset_id)
        status = asset.protectionStatus
    if asset_type == AssetType.CSP_VOLUME:
        asset = get_csp_volume_by_id(context, asset_id)
        status = asset.protectionStatus
    if asset_type == AssetType.CSP_PROTECTION_GROUP:
        asset = context.inventory_manager.get_protection_group_by_id(asset_id)
        if len(asset.protectionJobInfo) > 0:
            status = ProtectionStatus.PROTECTED.value
        else:
            status = ProtectionStatus.UNPROTECTED.value

    return status


def is_asset_protected_by_policy(protection_policy_info_list: list[ObjectNameResourceType], policy_name: str) -> bool:
    """Returns True if any of protectionPolicyInfo extracted from asset matches expected policy_name.
        i.e. if asset is protected by policy_name passed as parameter; else returns False

    Args:
        protection_policy_info_list: list of protection policy info extracted from csp instance/volume
        policy_name: Policy which has to checked for protection

    Returns:
        Bool: True if asset is protected by policy_name
    """
    for policy_info in protection_policy_info_list:
        if policy_name in policy_info.name:
            return True
    return False


def wait_for_asset_protection_status_for_assets(
    context: Context,
    volume_assets: list[str],
    ec2_assets: list[str],
    expected_status: ProtectionStatus,
    account_id: str,
):
    """Wait for expected Protection Status for a list of Assets
    Args:
        context (Context): Context object
        volume_assets (list[str]): List of EBS Volume assets
        ec2_assets (list[str]): List of EC2 Instance assets
        expected_status (ProtectionStatus): Expected Protection Status of the Asset
        account_id (str): CSP Account ID
    """
    for volume_id in volume_assets:
        wait_for_asset_protection_status(
            context=context,
            asset_id=volume_id,
            expected_status=expected_status,
            asset_type=AssetType.CSP_VOLUME,
            account_id=account_id,
        )
    for ec2_id in ec2_assets:
        wait_for_asset_protection_status(
            context=context,
            asset_id=ec2_id,
            expected_status=expected_status,
            asset_type=AssetType.CSP_MACHINE_INSTANCE,
            account_id=account_id,
        )


def wait_for_asset_protection_status(
    context: Context,
    asset_id: str,
    expected_status: ProtectionStatus,
    asset_type: AssetType,
    account_id: str,
):
    """Wait for Asset Protection Status
    Args:
        context (Context): Context object
        asset_id (str): CSP Asset ID
        expected_status (ProtectionStatus): Expected Asset Protection Status
        asset_type (AssetType): Asset Type
        account_id (str): CSP Account ID
    """
    asset: tuple[CSPMachineInstanceModel, CSPVolumeModel] = None

    def _wait_for_protection_job():
        # Define the asset variable as non-local, causing it to bind to the nearest non-global variable
        nonlocal asset
        if asset_type == AssetType.CSP_VOLUME:
            asset = get_csp_volume_by_ebs_volume_id(context=context, ebs_volume_id=asset_id, account_id=account_id)
        elif asset_type == AssetType.CSP_MACHINE_INSTANCE:
            asset = get_csp_instance_by_ec2_instance_id(
                context=context, ec2_instance_id=asset_id, account_id=account_id
            )
        else:
            assert False, "Not supported asset type"
        return asset.protectionStatus == expected_status.value

    # wait for job completion
    try:
        wait(_wait_for_protection_job, timeout_seconds=240, sleep_seconds=10)
    except TimeoutExpired:
        assert False, f"wait_for_asset_protection_status timeout, asset={asset}, expected_status={expected_status}"


def validate_protection_status(
    context: Context, asset_id: str, asset_type: AssetType, expected_status: ProtectionStatus, validate: bool = True
) -> bool:
    """Validate Protection Status of Asset
    Args:
        context (Context): Context object
        asset_id (str): CSP Asset ID
        asset_type (AssetType): CSP Asset Type
        expected_status (ProtectionStatus): Expected Protection Status of Asset
        validate (bool, optional): Apply assertion of Protection Status validation. Defaults to True.
    Returns:
        bool: Protection Status of Asset validation
    """
    status = get_asset_protection_status(context=context, asset_id=asset_id, asset_type=asset_type)
    if validate:
        assert status == expected_status.value
    return status == expected_status.value


# endregion

# region Protection Jobs


def wait_for_protection_job_assignments(context: Context, asset_id_list: list[str], asset_type_list: list[AssetType]):
    """Wait for Protection Job assignments

    All standard assets have had a Protection Policy assigned.
    Wait for the assets to reflect that they now have a Protection Job.

    Args:
        context (Context): Context object
        asset_id_list (list[str]): List of CSP Asset IDs
        asset_type_list (list[AssetType]): List of CSP Asset Types
    """

    def instance_lambda(x):
        return len(get_csp_instance_protection_jobs(context=context, csp_instance_id=x)) > 0

    def volume_lambda(x):
        return len(get_csp_volume_protection_jobs(context=context, csp_volume_id=x)) > 0

    def prot_group_lambda(x):
        return len(get_protection_group_protection_jobs(context=context, protection_group_id=x)) > 0

    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if asset_id:
            if asset_type == AssetType.CSP_MACHINE_INSTANCE:
                CommonSteps.wait_for_condition(
                    lambda: instance_lambda(x=asset_id),
                    error_msg=f"CSP Instance {asset_id} does not claim to be protected",
                )
            elif asset_type == AssetType.CSP_VOLUME:
                CommonSteps.wait_for_condition(
                    lambda: volume_lambda(x=asset_id),
                    error_msg=f"CSP Volume {asset_id} does not claim to be protected",
                )
            elif asset_type == AssetType.CSP_PROTECTION_GROUP:
                CommonSteps.wait_for_condition(
                    lambda: prot_group_lambda(x=asset_id),
                    error_msg=f"CSP Protection Group {asset_id} does not claim to be protected",
                )


def wait_for_protection_job_unassignments(context: Context, asset_id_list: list[str], asset_type_list: list[AssetType]):
    """Wait for Protection Job unassignments

    All standard assets have had a Protection Policy un-assigned.
    Wait for the assets to reflect that they no longer have a Protection Job.

    Args:
        context (Context): Context object
        asset_id_list (list[str]): List of CSP Asset IDs
        asset_type_list (list[AssetType]): List of CSP Asset Types
    """

    def instance_lambda(x):
        return len(get_csp_instance_protection_jobs(context=context, csp_instance_id=x)) == 0

    def volume_lambda(x):
        return len(get_csp_volume_protection_jobs(context=context, csp_volume_id=x)) == 0

    def prot_group_lambda(x):
        return len(get_protection_group_protection_jobs(context=context, protection_group_id=x)) == 0

    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if asset_id:
            if asset_type == AssetType.CSP_MACHINE_INSTANCE:
                CommonSteps.wait_for_condition(
                    lambda: instance_lambda(x=asset_id),
                    error_msg=f"CSP Instance {asset_id} still claims to be protected",
                )
            elif asset_type == AssetType.CSP_VOLUME:
                CommonSteps.wait_for_condition(
                    lambda: volume_lambda(x=asset_id),
                    error_msg=f"CSP Volume {asset_id} still claims to be protected",
                )
            elif asset_type == AssetType.CSP_PROTECTION_GROUP:
                CommonSteps.wait_for_condition(
                    lambda: prot_group_lambda(x=asset_id),
                    error_msg=f"CSP Protection Group {asset_id} still claims to be protected",
                )


# endregion

# region Basic Compare/Validate Asset Functions


def validate_backup_info(
    context: Context,
    asset_type: AssetType,
    asset_id: str,
    backup_info: list[ObjectCountType],
) -> None:
    """
        Retrieves the given asset ID and validates that the asset's backupInfo object contains the same
        properties as the input `backup_info` list.  Python sets are used to support an unordered list
        comparison.

    Args:
        context (Context): fixture that provides test execution context
        asset_type (AssetType): AssetType.CSP_MACHINE_INSTANCE or AssetType.CSP_VOLUME
        asset_id (str): inventory manager asset ID
        backup_info (list[ObjectCountType]): expected asset backup information
    """
    actual_backup_info: list[ObjectCountType]
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        csp_machine_instance: CSPMachineInstanceModel = get_csp_instance_by_id(context=context, csp_machine_id=asset_id)
        actual_backup_info = csp_machine_instance.backupInfo
    elif asset_type == AssetType.CSP_VOLUME:
        csp_volume: CSPVolumeModel = get_csp_volume_by_id(context=context, csp_volume_id=asset_id)
        actual_backup_info = csp_volume.backupInfo
    else:
        assert False, f"Not supported asset type: {asset_type}"
    assert len(actual_backup_info) == len(backup_info)
    assert {x.to_json() for x in actual_backup_info} == {x.to_json() for x in backup_info}


def compare_aws_and_dscc_assets(context: Context, csp_account_id: str):
    """Compare AWS and DSCC assets
    Args:
        context (Context): Context object
        csp_account_id (str): CSP Account ID
    """
    aws = context.aws_one

    aws_ec2_instance_list = aws.ec2.get_all_instances()
    atlantia_ec2_instance_list: CSPMachineInstanceListModel = get_csp_instances(context)
    compare_asset_lists(
        aws,
        aws_ec2_instance_list,
        atlantia_ec2_instance_list,
        AssetType.CSP_MACHINE_INSTANCE,
        csp_account_id,
        context.aws_one_region_name,
    )

    aws_ebs_instance_list = aws.ebs.get_all_volumes()
    atlantia_ebs_volumes: CSPVolumeListModel = get_csp_volumes(context)
    compare_asset_lists(
        aws,
        aws_ebs_instance_list,
        atlantia_ebs_volumes,
        AssetType.CSP_VOLUME,
        csp_account_id,
        context.aws_one_region_name,
    )


def compare_asset_lists(
    aws: AWS,
    aws_list: list[Any],
    atlantia_list: Union[CSPMachineInstanceListModel, CSPVolumeListModel],
    asset_type: AssetType,
    csp_account_id: str,
    region: str,
):
    """Compare Asset Lists
    Args:
        aws (AWS): AWS object
        aws_list (list[Any]): AWS asset list
        atlantia_list (list[Union[CSPMachineInstanceListModel, CSPVolumeListModel]]): DSCC asset list
        asset_type (AssetType): Asset type
        csp_account_id (str): CSP Account ID
        region (str): Targeted region of assets
    """
    atlantia_ebs_list = [
        item.cspId
        for item in atlantia_list.items
        if item.accountInfo.id == csp_account_id and region in item.cspInfo.cspRegion
    ]
    for aws_item in aws_list:
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            # NOTE: "terminated" EC2 don't seem to be imported into DSCC
            state = aws.ec2.get_instance_state(aws_item.id)

            if state != Ec2State.TERMINATED.value:
                assert aws_item.id in atlantia_ebs_list
        elif asset_type == AssetType.CSP_VOLUME:
            assert aws_item.id in atlantia_ebs_list


def find_aws_asset_in_csp_vpc_assets(vpc_id: int, csp_vpcs: list[CSPVPCModel]) -> CSPVPCModel:
    """Determine if the given AWS VPC is present in the provided CSP VPC list

    Args:
        vpc_id (int): AWS VPC ID
        csp_vpcs (list[CSPVPCModel]): List of CSP VPC objects

    Returns:
        CSPVPCModel: Returns a VPC if the AWS VPC ID is found in the provided CSP VPC list, None otherwise
    """
    for csp_vpc in csp_vpcs:
        if csp_vpc.csp_id == vpc_id:
            return csp_vpc
    return None


def find_aws_asset_in_csp_subnet_assets(subnet_id: int, csp_subnets: list[CSPSubnetModel]) -> CSPSubnetModel:
    """Determine if the given AWS Subnet is present in the provided CSP Subnet list

    Args:
        subnet_id (int): AWS Subnet ID
        csp_subnets (list[CSPSubnetModel]): List of CSP Subnet objects

    Returns:
        CSPSubnetModel: Returns a Subnet if the AWS Subnet ID is found in the provided CSP Subnet list, None otherwise
    """
    for csp_subnet in csp_subnets:
        if csp_subnet.csp_id == subnet_id:
            return csp_subnet
    return None


def validate_aws_assets_present_in_inventory_manager(
    context: Context, csp_account_id: str, aws_assets: AwsAssetsDto
) -> bool:
    """Validate the provided AWS Assets are present in DSCC Inventory

    Args:
        context (Context): Test Context
        csp_account_id (str): CSP Account ID, used to get VPC and Subnet from Inventory Manager
        aws_assets (AwsAssetsDto): The AWS Assets to validate against

    Returns:
        bool: Return True if all of the provided AWS Assets are found in DSCC
    """
    validation = True

    # EC2 Instances
    num_ec2_instances = len(aws_assets.ec2_instances)
    num_csp_machine_instances = 0
    for ec2_instance in aws_assets.ec2_instances:
        if get_csp_instance_by_ec2_instance_id(context=context, ec2_instance_id=ec2_instance.id):
            num_csp_machine_instances += 1
    if num_csp_machine_instances != num_ec2_instances:
        logger.info(f"Not all CSP Machine Instances found: {num_csp_machine_instances} of {num_ec2_instances}")
        validation = False

    # EBS Volumes
    num_ebs_volumes = len(aws_assets.ebs_volumes)
    num_csp_volumes = 0
    for ebs_volume in aws_assets.ebs_volumes:
        if get_csp_volume_by_ebs_volume_id(context=context, ebs_volume_id=ebs_volume.id):
            num_csp_volumes += 1
    if num_csp_volumes != num_ebs_volumes:
        logger.info(f"Not all CSP Volumes found: {num_csp_volumes} of {num_ebs_volumes}")
        validation = False

    # VPCS
    num_vpcs = len(aws_assets.vpcs)
    num_csp_vpcs = 0
    csp_vpcs = context.inventory_manager.get_csp_vpcs(account_id=csp_account_id)
    for vpc in aws_assets.vpcs:
        if find_aws_asset_in_csp_vpc_assets(vpc_id=vpc.id, csp_vpcs=csp_vpcs.items):
            num_csp_vpcs += 1
    if num_csp_vpcs != num_vpcs:
        logger.info(f"Not all CSP VPCs found: {num_csp_vpcs} of {num_vpcs}")
        validation = False

    # SUBNETS
    num_subnets = len(aws_assets.subnets)
    num_csp_subnets = 0
    csp_subnets = context.inventory_manager.get_csp_subnets(account_id=csp_account_id)
    for subnet in aws_assets.subnets:
        if find_aws_asset_in_csp_subnet_assets(subnet.id, csp_subnets=csp_subnets.items):
            num_csp_subnets += 1
    if num_csp_subnets != num_subnets:
        logger.info(f"Not all CSP Subnets found: {num_csp_subnets} of {num_subnets}")
        validation = False

    return validation


def validate_aws_assets_present_in_inventory_manager_within_time(
    context: Context, csp_account_id: str, aws_assets: AwsAssetsDto, timeout_mins: int
):
    """Validate that all AWS Assets are present in DSCC Inventory within the timeout time

    Args:
        context (Context): Test Context
        csp_account_id (str): CSP Account ID
        aws_assets (AwsAssetsDto): AWS Assets to validate against
        timeout_mins (int): The timeout time for the validation
    """
    validation = False

    time_delta = timedelta(minutes=timeout_mins)
    time_start = datetime.now()
    time_end = time_start + time_delta

    while datetime.now() < time_end:
        validation = validate_aws_assets_present_in_inventory_manager(
            context=context, csp_account_id=csp_account_id, aws_assets=aws_assets
        )
        if validation:
            break

    time_duration = datetime.now() - time_start

    if validation:
        logger.info(f"All AWS Account assets found in DSCC. Time: {time_duration}")
    else:
        logger.info(f"Not all AWS Account Assets found in DSCC. Time: {time_duration}")

    assert validation


# endregion


def get_resource_groups(
    context: AzureContext,
    account_id: str,
    sort: str = "name",
    filter: str = "",
    response_code: requests.codes = requests.codes.ok,
    expected_error: str = "",
) -> Union[CSPResourceGroupListModel, ErrorResponse]:
    """
    Returns a list of Resource Group

    Args:
        context (AzureContext): Object of tests.e2e.azure_protection.azure_context.AzureContext
        account_id (str): ID of the azure account.
        sort (str): Sorting the output on the basis of cspId and name.
        filter (str): Filter the output on the basis of subscriptionId.
        response_code (requests.codes): Expected status code from the API response.
        expected_error (str): Expected error from API response if any.

    Returns:
        Returns a list of resource group.
    """
    resource_groups: CSPResourceGroupListModel = context.inventory_manager.get_csp_resource_groups(
        account_id=account_id,
        sort=sort,
        filter=filter,
        expected_status_code=response_code,
        expected_error=expected_error,
    )
    return resource_groups


def get_resource_group_by_id(
    context: AzureContext, account_id: str, csp_resource_group_id: str
) -> Union[CSPResourceGroupModel, ErrorResponse]:
    """
    Returns a specific resource group by ID.
    Args:
        context (AzureContext): Object of tests.e2e.azure_protection.azure_context.AzureContext
        account_id (str): ID of the azure account.
        csp_resource_group_id (str): ID of a specific Resource Group.
    Returns:
        Returns a specific resource group by ID.
    """
    resource_group: CSPResourceGroupModel = context.inventory_manager.get_csp_resource_group_by_id(
        account_id=account_id, resource_group_id=csp_resource_group_id
    )
    return resource_group


def get_subscriptions(
    context: AzureContext,
    account_id: str,
    sort: str = "name",
    response_code: requests.codes = requests.codes.ok,
    expected_error: str = "",
) -> Union[CSPSubscriptionListModel, ErrorResponse]:
    """
    Returns a list of Subscription.

    Args:
        context (AzureContext): Object of tests.e2e.azure_protection.azure_context.AzureContext
        account_id (str): ID of the azure account.
        sort (str): Sorting the output on the basis of cspId and name.
        response_code (requests.codes): Expected status code from the API response
        expected_error (str): Expected error from API response if any.

    Returns:
        Returns a list of Subscription.
    """
    subscriptions: CSPSubscriptionListModel = context.inventory_manager.get_csp_subscriptions(
        account_id=account_id, sort=sort, expected_status_code=response_code, expected_error=expected_error
    )
    return subscriptions


def get_subscription_by_id(
    context: AzureContext, account_id: str, csp_subscription_id: UUID
) -> Union[CSPSubscriptionModel, ErrorResponse]:
    """
    Returns a specific Subscription by ID.
    Args:
        context (AzureContext): Object of tests.e2e.azure_protection.azure_context.AzureContext
        account_id (str): ID of the azure account.
        csp_subscription_id (UUID): ID of a specific Subscription.
    Returns:
        Returns a specific Subscription by ID.
    """
    subscription: CSPSubscriptionModel = context.inventory_manager.get_csp_subscription_by_id(
        account_id=account_id, subscription_id=csp_subscription_id
    )
    return subscription


def get_vpc_by_id(context: AzureContext, account_id: str, csp_vpc_id: UUID) -> Union[CSPVPCModel, ErrorResponse]:
    """
    Returns a specific VPC by ID.

    Args:
        context (AzureContext): Object of tests.e2e.azure_protection.azure_context.AzureContext
        account_id (str): ID of the azure account.
        csp_vpc_id (UUID): ID of a specific vpc.

    Returns:
        Returns a specific VPC by ID.
    """
    vpc: CSPVPCModel = context.inventory_manager.get_csp_vpc_by_id(account_id=account_id, vpc_id=csp_vpc_id)
    return vpc


def get_subnet_by_id(
    context: AzureContext, account_id: str, csp_subnet_id: UUID
) -> Union[CSPSubnetModel, ErrorResponse]:
    """
    Returns a specific Subnet by ID.

    Args:
        context (AzureContext): Object of tests.e2e.azure_protection.azure_context.AzureContext
        account_id (str): ID of the azure account.
        csp_subnet_id (UUID): ID of a specific subnet.

    Returns:
        Returns a specific Subnet by ID.
    """
    subnet: CSPSubnetModel = context.inventory_manager.get_csp_subnet_by_id(
        account_id=account_id, subnet_id=csp_subnet_id
    )
    return subnet


def get_subnet_csp_id(context: Context, account_id: str, subnet_id: UUID) -> str:
    """Return the CSP ID of a Subnet by DSCC ID

    Args:
        context (Context): the Context object
        account_id (str): DSCC Account ID
        subnet_id (UUID): Subnet DSCC ID

    Returns:
        str: CSP ID of the requested Subnet
    """
    subnet_csp_id: str = ""

    csp_subnet: CSPSubnetModel = context.inventory_manager.get_csp_subnet_by_id(
        account_id=account_id, subnet_id=subnet_id
    )
    if isinstance(csp_subnet, CSPSubnetModel):
        subnet_csp_id = csp_subnet.csp_id
    return subnet_csp_id
