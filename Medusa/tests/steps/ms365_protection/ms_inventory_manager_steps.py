"""
This file is for common steps involved for Inventory Manager related actions like
getting users list, user details and groups etcs.,
"""

import logging
from tests.e2e.ms365_protection.ms_office_context import MSOfficeContext
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.csp_ms_users import (
    MS365CSPUser,
    MS365CSPUserList,
)
from lib.platform.ms365.ms_outlook_manager import MSOutlookManager
from lib.dscc.backup_recovery.aws_protection.accounts.models.csp_account import CSPAccount
from lib.common.enums.task_status import TaskStatus
from utils.timeout_manager import TimeoutManager
from tests.steps.tasks import tasks
from tests.steps.ms365_protection.ms_cloud_account_manager_steps import get_ms365_csp_account_by_name
from tests.steps.ms365_protection.ms_outlook_common_steps import get_ms365_org_users_count

logger = logging.getLogger()


def get_ms365_user_by_email(ms_context: MSOfficeContext, ms365_user_email: str) -> MS365CSPUser:
    """This method is to fetch MS365 user ID and its type

    Args:
        ms_context (MSOfficeContext): MS365 Context object
        ms365_user_email (str): email of the user which you want to fetch from the MS365 users list.

    Returns:
        MS365CSPUser: after filtering with the name it returns MS365 CSP user Object
    """
    all_users: MS365CSPUserList = ms_context.inventory_manager.get_ms365_csp_users_list(
        filter=f"cspInfo.emailAddress eq '{ms365_user_email}'"
    )
    assert all_users.count == 1, f"Expected to have one MS365 user with mail: {ms365_user_email}"
    logger.info(f"Successfully fetched ms365 user by mail: {ms365_user_email}")
    return all_users.items[0]


def list_and_validate_csp_ms365_users(
    ms_context: MSOfficeContext, ms_outlook_manager: MSOutlookManager = "", org_account_id: str = ""
) -> MS365CSPUserList:
    """List csp ms365 users information

    Args:
        ms_context (MSOfficeContext): MS365 Context object
        ms_outlook_manager (MSOutlookManager): microsoft user context. Defaults to ""

    Returns:
        MS365CSPUserList: csp ms365 users information
    """
    if not ms_outlook_manager:
        ms_outlook_manager = ms_context.ms_one_outlook_manager
    if not org_account_id:
        org_account_id = get_ms365_csp_account_by_name(ms_context, ms_context.ms365_org_account_name).id
    users_list = ms_context.inventory_manager.get_ms365_csp_users_list(filter=f"accountInfo/id eq '{org_account_id}'")
    dscc_users_count = users_list.count
    ms365_users_count = get_ms365_org_users_count(ms_context, ms_outlook_manager)
    assert (
        dscc_users_count == ms365_users_count
    ), f"Failed to validate the MS365 users list, MS365 users count: {ms365_users_count}  and dscc users count: {dscc_users_count} did not matched"
    logger.info("Successfully listed the MS365 users from dscc and validated the users list.")
    return users_list


def csp_ms365_inventory_refresh(ms_context: MSOfficeContext, ms365_account_name: str, wait_for_task: bool = True):
    """Refresh CSP MS365 inventory

    Args:
        ms_context (MSOfficeContext): MS365 Context object
        ms365_account_name (str): ms365 account name
        wait_for_task (bool, optional): flag to wait for the task. Defaults to True.

    Returns:
        str: Refresh inventory task id
    """
    # Get MS365 csp id
    csp_ms365_account: CSPAccount = get_ms365_csp_account_by_name(ms_context, ms365_account_name)
    csp_ms365_account_id = csp_ms365_account.id
    logger.info("Trigger MS365 account inventory refresh")
    task_id = ms_context.inventory_manager.trigger_ms365_inventory_refresh(csp_ms365_account_id)
    # work  around for sometime
    task_id = task_id[:-1]
    if wait_for_task:
        logger.info(f"Waiting for MS365 account inventory refresh for {csp_ms365_account_id} to complete")
        refresh_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=ms_context.user,
            timeout=TimeoutManager.task_timeout,
        )
        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"Account {csp_ms365_account_id} inventory refresh failure, refresh_task_status={refresh_task_status}"
    logger.info("Successfully refreshed MS365 account inventory")
    return task_id
