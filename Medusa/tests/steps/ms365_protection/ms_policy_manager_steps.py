"""
This file is for Policy Manager steps like protection policy creation, deletion and
protection group creation and deletion etc.,
"""

import logging
from time import sleep
from typing import Union
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.task_status import TaskStatus
from lib.common.enums.csp_resource_type import CSPResourceType
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.csp_ms_protection_groups import (
    MS365CSPProtectionGroupCreate,
    ProtectionGroupMembershipType,
    MS365CSPProtectionGroupList,
    MS365CSPProtectionGroup,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
)
import tests.steps.aws_protection.policy_manager_steps as PolicyManagerSteps
from tests.steps.tasks import tasks
from tests.e2e.ms365_protection.ms_office_context import MSOfficeContext
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def create_protection_policy_for_ms365_resource(
    ms_context: MSOfficeContext,
    protection_policy_name: str,
    immutable: bool = False,
) -> str:
    """This method creates protection policy for MS365 resource

    Args:
        ms_context (MSOfficeContext): MS365 Test Context Object
        protection_policy_name (str): The name for the protection policy
        immutable (bool): If user wants a immutable protection policy provide True, Defaults to False.

    Returns:
        str: The ID of the Protection Policy created.
    """
    logger.info(f"Creating protection policy with name: {protection_policy_name} for MS365 resource")
    # TODO: Currently making use of common protection policy method if needed we can add/modify other steps accordingly
    policy_name = protection_policy_name if protection_policy_name else ms_context.protection_policy_name
    protection_policy_id = PolicyManagerSteps.create_protection_policy(
        context=ms_context, name=policy_name, immutable=immutable, ms365_schedule=True
    )
    logger.info(f"Protection Policy created: {protection_policy_id}")
    return protection_policy_id


def assign_protection_policy_to_ms365_resource(
    ms_context: MSOfficeContext, asset_id: str, asset_type: str, protection_policy_id: str = None
):
    """This method is used for assigning protection policy to a MS 365 resource.

    Args:
        ms_context (MSOfficeContext): MS365 Context object
        asset_id (str): CSP Asset ID to assign the policy
        asset_type (str): CSP Asset type to assign the policy
        protection_policy_id (str, optional): Protection Policy ID. Defaults to None
    """
    logger.info("Assign protection policy to MS365 resource")
    # TODO: Need to implement fully when the APIs are available. we are not clear about asset type and id.
    PolicyManagerSteps.assign_protection_policy(
        context=ms_context,
        asset_id=asset_id,
        asset_type=asset_type,
        protection_policy_id=protection_policy_id,
    )
    logger.info(f"Protection policy successfully assigned to the {asset_id}")


def create_ms365_protection_group(
    ms_context: MSOfficeContext,
    protection_group_name: str,
    asset_type: AssetType = AssetType.MS365_USER,
    description: str = "MS365 Protection Group",
    membership_type: str = ProtectionGroupMembershipType.STATIC,
    organization_ids: Union[str, list] = [],
    static_member_ids: Union[str, list] = [],
    is_negative: bool = False,
) -> str:
    """This method creates protection group for MS365 with Static set of member resources.
    TODO: Dynamic protection groups are not implemented currently.

    Args:
        ms_context (MSOfficeContext): Context Object for MS365
        protection_group_name (str): A name to assign to the MS365 protection group.
        asset_type (AssetType, optional): The type of assets to include in the protection group. Defaults to AssetType.MS365_USER.
        description (str, optional): A brief description of the MS365 protection group. Defaults to "MS365 Protection Group".
        membership_type (str, optional): Indicates whether assets are included by explicit enumeration (STATIC) or by attribute filtering (DYNAMIC). Defaults to ProtectionGroupMembershipType.STATIC.
        organization_ids (Union[str, list], optional): IDs of the MS365 organizations containing the assets to include in the protection group. Defaults to [].
        static_member_ids (Union[str, list], optional): IDs of assets to include in the protection group. Defaults to [].
        is_negative (bool, optional): If user expecting creation of protection group to fail in negative scenario he should provide True. Defaults to False.

    Returns:
        str: UUID of the created protection group ID
    """
    logger.info(f"Started Creating Protection group with name {protection_group_name} in MS365...")
    organization_ids = [organization_ids] if not isinstance(organization_ids, list) else organization_ids
    static_member_ids = [static_member_ids] if not isinstance(static_member_ids, list) else static_member_ids
    protection_group_payload: MS365CSPProtectionGroupCreate = MS365CSPProtectionGroupCreate(
        asset_type=asset_type,
        description=description,
        membership_type=membership_type,
        name=protection_group_name,
        staticMember_ids=static_member_ids,
    )
    task_id = ms_context.protection_group_manager.create_ms365_protection_group(
        post_protection_group=protection_group_payload
    )
    task_id = task_id.strip('"')
    task_status: str = tasks.wait_for_task(task_id, ms_context.user, TimeoutManager.task_timeout)
    protection_group_id: str = ""
    if not is_negative:
        assert (
            task_status.upper() == TaskStatus.success.value
        ), f"Here Create protection group task is expected to succeed, instead the task is: {task_status}"
        protection_group_id = tasks.get_task_source_resource_uuid(
            task_id=task_id,
            user=ms_context.user,
            source_resource_type=CSPResourceType.MS365_PROTECTION_GROUP.value,
        )
        logger.info(
            f"Successfully Created Protection group with name: {protection_group_name} and id: {protection_group_id}"
        )
    else:
        assert (
            task_status.upper() == TaskStatus.failed.value
        ), f"Here create protection group task is expected to fail, instead the task is: {task_status}"
    return protection_group_id


def get_protection_group_by_name(ms_context: MSOfficeContext, protection_group_name: str) -> MS365CSPProtectionGroup:
    """This method first gets all the protection groups then fetches protection group details for provided group.

    Args:
        ms_context (MSOfficeContext): Context Object of MS365
        protection_group_name (str): Protection group name that user wants to fetch details.

    Raises:
        Exception: Raises key error exception incase if it fails to get all protection groups

    Returns:
        MS365CSPProtectionGroup: if success returns protection group details.
    """
    logger.info(f"Started fetching protection group details with name : {protection_group_name}")
    try:
        protection_group_details: Union[MS365CSPProtectionGroupList, ErrorResponse] = (
            ms_context.protection_group_manager.get_ms365_protection_groups(filter=f"name eq '{protection_group_name}'")
        )
        assert (
            protection_group_details.count == 1
        ), f"Expected to have one protection group with name: {protection_group_name}"
        logger.info(f"Successfully fetched protection group details with name : {protection_group_name}")
        return protection_group_details.items[0]
    except KeyError:
        raise Exception(
            f"There is KeyError exception occurred while fetching protection group by name: {protection_group_name} and response: {protection_group_details}"
        )


def delete_ms365_protection_policy(
    ms_context: MSOfficeContext,
    protection_policy_id: str,
):
    """This method deletes protection policy created for MS365 resource

    Args:
        ms_context (MSOfficeContext): MSOfficeContext Object
        protection_policy_id (str): The ID of protection policy to be deleted

    Returns:
        None.
    """
    logger.info(f"Deleting MS365 protection policy with ID: {protection_policy_id}")
    # TODO: Currently making use of common protection policy method if needed we can add/modify other steps accordingly
    policy_id = protection_policy_id if protection_policy_id else ms_context.protection_policy_id
    PolicyManagerSteps.delete_protection_policy(context=ms_context, policy_id=policy_id)
    logger.info(f"Deleted Protection Policy with ID: {policy_id}")


def unassign_protection_policy_from_ms365_resource(ms_context: MSOfficeContext, pg_name: str):
    """This method is used for unassign protection policies from a MS365 resource.

    Args:
        ms_context (MSOfficeContext): MS365 Context object
        pg_name (str): Protection group name to unassign the policy on it
    """
    logger.info("Unassign protection policy from MS365 resource")
    pg_id = get_protection_group_by_name(ms_context, pg_name).id
    PolicyManagerSteps.unassign_all_protection_policies(
        context=ms_context,
        asset_id=pg_id,
    )
    # adding a time sleep just to reflect unassign operaion from DSCC
    sleep(10)
    logger.info(f"Protection policy successfully unassigned for {pg_id}")


def perform_delete_protection_group_and_verify_task(ms_context: MSOfficeContext, pg_name: str):
    """This method deletes a protection group using its protection ID and
    verifies whether the deletion task was successful or not.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object.
        pg_name (str): protection group name that requires deletion.
    """
    logger.info(f"Deletion of protection group with ID:{pg_name} started")
    pg_id = get_protection_group_by_name(ms_context, ms_context.protection_group_name).id
    task_id = ms_context.protection_group_manager.delete_ms365_protection_group(pg_id)
    logger.info(f"waiting for the task {task_id} to complete...")
    task_id = task_id.strip('"') if '"' in task_id else task_id
    task_status: str = tasks.wait_for_task(task_id, ms_context.user, TimeoutManager.task_timeout)
    assert (
        task_status.upper() == TaskStatus.success.value
    ), f"Delete protection group task is expected to succeed, instead the task is: {task_status}"
    logger.info(f"protection group with id: {pg_id} deleted successfully")


def check_and_delete_ms365_protection_group(ms_context: MSOfficeContext, pg_name: str):
    """This method verifies the existence of a MS365 protection group with a specified name.
    If the group exists, it proceeds to check for associated protection policies and then deletes the protection group.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object.
        pg_name (str): The name of the protection group that needs deletion.
    """
    protection_group = ms_context.protection_group_manager.get_ms365_protection_groups(filter=f"name eq '{pg_name}'")
    if protection_group.count == 0:
        logger.info(f"There are currently no protection groups with the name {pg_name} that are available for deletion")
    else:
        pg_details = protection_group.items[0]
        # Unassign protection policy if exists
        if pg_details.protection_job_info == []:
            logger.info(f"There are no protection policy assigned to protection group {pg_name}")
        else:
            logger.info("Protection Group is assigned with a protection policy so unassign protection policy")
            unassign_protection_policy_from_ms365_resource(ms_context, pg_details.id)
        # perform deletion of protection group
        perform_delete_protection_group_and_verify_task(ms_context, pg_details.id)
        logger.info(f"protection group with name {pg_name} is deleted successfully")
