import logging
from functools import partial
from typing import Union
from uuid import UUID
from requests import Response
import requests

from lib.platform.aws_boto3.aws_factory import AWS
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.csp_account import (
    CSPAccount,
)
import tests.e2e.aws_protection.constants as Constants
from tests.e2e.aws_protection.context import Context
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.payload.csp_account_update import (
    CSPAccountUpdate,
)
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.resource_uri_prefix import (
    ResourceURIPrefix,
)
from lib.common.enums.task_status import TaskStatus
from tests.steps.tasks import tasks
from lib.dscc.tasks.payload.task import TaskList
from utils.timeout_manager import TimeoutManager


logger = logging.getLogger()


def get_csp_account_by_aws_account_id(context: Context, aws_account_id: str) -> CSPAccount:
    """Return CSP account given AWS account id

    Args:
        context (Context): test Context
        aws_account_id (str): AWS account id

    Returns:
        CSPAccount: CSP account for given AWS account
    """
    csp_filter = f"cspId eq 'arn:aws:iam::{aws_account_id}:'"
    csp_accounts = context.cam_client_v1beta1.get_csp_accounts(filter=csp_filter)
    if csp_accounts.total:
        return csp_accounts.items[0]


def delete_csp_account(context: Context, csp_account_name: str):
    """
    Unregister AWS Account found by its name.
    Verify all purge tasks created after unregister request.

    Args:
        context (Context): AWS protection context
        csp_account_name (str): csp aws account name

    """

    def _fetch_purge_task_and_wait_for_task_completion(context: Context, func: partial):
        logger.info(f"Validating {func} task")
        purge_tasks: Union[TaskList, list] = func()

        # It has been observed that "delete_csp_account()" can error with:
        #   purge_task = purge_tasks[0] if isinstance(purge_tasks, list) else purge_tasks.items[0]
        #   IndexError: list index out of range
        # This has been seen looking for the UNREGISTER_SCHEDULER_PURGE_TASK, it can take a few minutes to appear.
        # Because that task is found within a TaskList object, the assert does not fail if the TaskList has no "items".
        # We will also move the check on UNREGISTER_SCHEDULER_PURGE_TASK to the end of the line.
        purge_task = None
        if isinstance(purge_tasks, list) and len(purge_tasks):
            purge_task = purge_tasks[0]
        elif purge_tasks.total:
            purge_task = purge_tasks.items[0]
        assert purge_task, "Task not found"

        status = tasks.wait_for_task(
            task_id=purge_task.id,
            user=context.user,
            timeout=TimeoutManager.standard_task_timeout,
        )
        assert status.upper() == TaskStatus.success.value, f"Task {purge_task.name}: {purge_task.id} failed"
        logger.info(f"Task {purge_task.name}: {purge_task.id} successfully")
        logger.info("Check for DPM child tasks")

        # TODO: Child task Purge EBS/EC2 Backups for Account - will not fail
        # tasks.wait_for_child_tasks(root_task_id=purge_task.id, user=context.user)
        # logger.info("Child tasks completed successfully")

    csp_account = context.cam_client_v1beta1.get_csp_account_by_name(name=csp_account_name)
    assert csp_account, f"Account not found: {csp_account_name}"
    logger.info(f"Unregister AWS Account {csp_account.id}")
    delete_csp_account_and_wait_for_task(context=context, csp_account_id=csp_account.id)

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_resource,
            user=context.user,
            task_name=Constants.UNREGISTER_INVENTORY_PURGE_TASK,
            resource_uri=f"{ResourceURIPrefix.CSP_ACCOUNT.value}{csp_account.id}",
        ),
    )

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_customer_account,
            user=context.user,
            task_name=Constants.UNREGISTER_DPM_PURGE_TASK.format(csp_account.name),
            customer_id=csp_account.customer_id,
        ),
    )

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_resource,
            user=context.user,
            task_name=Constants.UNREGISTER_RDS_INVENTORY_PURGE_TASK.format(csp_account.name),
            resource_uri=f"{ResourceURIPrefix.CSP_ACCOUNT.value}{csp_account.id}",
            time_offset_minutes=40,
        ),
    )

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_resource,
            user=context.user,
            task_name=Constants.UNREGISTER_SCHEDULER_PURGE_TASK,
            resource_uri=f"{ResourceURIPrefix.CSP_ACCOUNT.value}{csp_account.id}",
            time_offset_minutes=40,
        ),
    )

    logger.info(f" AWS Account {csp_account.id} - Unregistered")


def attach_cam_roles_to_policies(aws: AWS, aws_account_id: str):
    """This method is specifically created to attach policies to roles
    as it is not happening on localstack upon CloudFormation Stack creation.
    This should not be required on the Sandbox.
    As per the reason stated above, all the roles and policies names are hard-coded
    in the method itself.

    Args:
        aws (AWS): AWS object
        aws_account_id (str): aws_account_id
    """
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-inventory-manager",
        policy_name="hpe-cam-inventory-manager",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-restore-manager",
        policy_name="hpe-cam-restore-manager",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-configuration-validator",
        policy_name="hpe-cam-iam-role-and-policy-validation",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-account-unregistrar",
        policy_name="hpe-cam-iam-role-and-policy-deletion",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-backup-manager",
        policy_name="hpe-cam-backup-manager",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-data-extractor",
        policy_name="hpe-cam-data-extraction",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-data-injector",
        policy_name="hpe-cam-data-injection",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-hci-ec2-cloud-manager",
        policy_name="hpe-hci-ec2-cloud-manager",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-csp-rds-inventory-manager",
        policy_name="hpe-cam-csp-rds-inventory-manager",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-csp-rds-data-protection-manager-backup",
        policy_name="hpe-cam-csp-rds-data-protection-manager-backup",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-csp-rds-data-protection-manager-restore",
        policy_name="hpe-cam-csp-rds-data-protection-manager-restore",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-csp-k8s-inventory-manager",
        policy_name="hpe-cam-csp-k8s-inventory-manager",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-csp-k8s-data-protection-manager-backup",
        policy_name="hpe-cam-csp-k8s-data-protection-manager-backup",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-csp-k8s-data-protection-manager-restore",
        policy_name="hpe-cam-csp-k8s-data-protection-manager-restore",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-gfrs-s3-bucket-manager",
        policy_name="hpe-cam-gfrs-s3-bucket-manager",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-cam-gfrs-s3-bucket-writer",
        policy_name="hpe-cam-gfrs-s3-bucket-writer",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-csp-ami-discovery",
        policy_name="hpe-csp-ami-discovery",
    )
    aws.iam.attach_existing_role_to_policy(
        aws_account_id=aws_account_id,
        role_name="hpe-sds-composer",
        policy_name="hpe-sds-composer",
    )


# DELETE /csp-accounts/{id} - SUCCESS
def delete_csp_account_and_wait_for_task(context: Context, csp_account_id: UUID) -> str:
    """Tries to delete a CSP Account by its ID and expects a success

    Args:
        context (Context): Context object
        csp_account_id (UUID): ID of the CSP account

    Returns:
        str: Task ID of the delete action
    """
    sync_task_id: str = delete_csp_account_with_expectation(
        context=context,
        account_id=csp_account_id,
        expectation=TaskStatus.success.value,
    )
    return sync_task_id


# DELETE /csp-accounts/{id}
def delete_csp_account_with_expectation(context: Context, account_id: UUID, expectation: str) -> str:
    """Tries to delete a CSP account and validates the expected task status

    Args:
        context (Context): Context object
        account_id (UUID): ID of the account
        expectation (str): TaskStatus.success.value or TaskStatus.failed.value

    Returns:
        str: Task ID of the delete action
    """
    logger.info(f"Trying to modify account {account_id}")
    response: Response = context.cam_client_v1beta1.raw_delete_csp_account(account_id=account_id)
    assert (
        response.status_code == requests.codes.accepted
    ), f"DELETE /csp-accounts/{account_id} Failed with status_code: {response.status_code}  response.text: {response.text}"

    # Validating task status
    sync_task_id = context.task_manager.get_task_id_from_header(response)
    logger.info(f"Waiting for delete_account task {sync_task_id} to complete")
    sync_task_status = context.task_manager.wait_for_task(sync_task_id, timeout=100)
    assert sync_task_status.upper() == expectation
    return sync_task_id


def delete_csp_account_expect_failure(context: Context, account_id: UUID) -> str:
    """Tries to delete a CSP Account by its ID and expects a failure

    Args:
        context (Context): Context object
        account_id (UUID): ID of the CSP account

    Returns:
        str: Task ID of the delete action
    """
    logger.info(f"Trying to delete account {account_id}")
    return delete_csp_account_with_expectation(
        context=context,
        account_id=account_id,
        expectation=TaskStatus.failed.value,
    )


# PATCH /csp-accounts/{id} - SUCCESS
def modify_csp_account(context: Context, account_id: UUID, name: str, suspended: bool) -> str:
    """Toggles account's 'suspended' state and 'name' field

    Args:
        context (Context): Context object
        account_id (UUID): ID of the CSP account
        name (str): Name of the CSP account
        suspended (bool): Set 'True' to suspend, set 'False' to resume

    Returns:
        str: Task ID of the modify account operation
    """
    logger.info(f"Trying to modify account {account_id}, name={name}, suspended={suspended}")
    sync_task_id = context.cam_client_v1beta1.modify_csp_account(
        account_id,
        CSPAccountUpdate(name=name, suspended=suspended).to_json(),
        requests.codes.accepted,
    )

    # Validating task status
    sync_task_status = context.task_manager.wait_for_task(sync_task_id, timeout=100)
    assert sync_task_status.upper() == TaskStatus.success.value
    return sync_task_id


# PATCH /csp-accounts/{id} - FAILURE
def negative_modify_csp_account(
    context: Context,
    account_id: UUID,
    payload: str,
    expected_status_code: int = requests.codes.bad_request,
) -> None:
    """Tries to modify the 'suspended' state and 'name' field of the account and expects a failure

    Args:
        context (Context): Context object
        account_id (UUID): ID of the CSP account
        payload (str): Payload to modify an account
        expected_status_code (requests.codes.bad_request): Defaults to codes.bad_request
    """
    logger.info(f"Trying to modify account {account_id}")
    context.cam_client_v1beta1.raw_modify_csp_account(
        account_id=account_id,
        payload=payload,
        expected_status_code=expected_status_code,
    )
