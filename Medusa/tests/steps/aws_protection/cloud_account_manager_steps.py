import asyncio
import logging
import time
from functools import partial
from typing import Union
from waiting import wait, TimeoutExpired

import requests
from lib.common.common import FailedRetryWithResponseException
from lib.common.enums.asset_type_uri_prefix import AssetTypeURIPrefix
from lib.common.enums.csp_type import CspType
from lib.common.enums.provided_users import ProvidedUser
from lib.common.enums.task_status import TaskStatus
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.action_required_page import ActionRequiredPage
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.device_code import DeviceCodePage
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.microsoft_sign_in_page import (
    MicrosoftSignInPage,
)
from lib.dscc.backup_recovery.aws_protection.accounts.azure_oauth.pages.permission_requested_page import (
    PermissionRequestedPage,
)
from selenium.webdriver import Remote, Chrome
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import (
    CSPAccountListModel,
    CSPAccountModel,
    CSPAccountValidateModel,
    CSPOnboardingTemplateModel,
    PatchCSPAccountModel,
)


from lib.platform.aws_boto3.aws_factory import AWS
import tests.e2e.aws_protection.constants as Constants
from tests.e2e.aws_protection.context import Context
from tests.e2e.ms365_protection.ms_office_context import MSOfficeContext
from tests.steps.aws_protection.settings.dual_auth_steps import (
    authorize_dual_auth_request,
    get_pending_request_by_name_and_resource_uri,
)
from tests.steps.tasks import tasks
from lib.dscc.tasks.payload.task import Task, TaskList
from utils.common_helpers import generate_random_string
from utils.timeout_manager import TimeoutManager


logger = logging.getLogger()

DELETE_ACCOUNT_SLEEP_SECONDS: int = 240
UNPROTECT_ACCOUNT_SLEEP_SECONDS: int = 60
DUAL_AUTH_UNPROTECT_ACCOUNT_TASK_NAME: str = "Unprotect CSP account"


def get_csp_account_by_aws_account_id(context: Context, aws_account_id: str) -> CSPAccountModel:
    """Return CSP account given AWS account id

    Args:
        context (Context): test Context
        aws_account_id (str): AWS account id

    Returns:
        CSPAccount: CSP account for given AWS account
    """
    csp_filter = f"cspId eq 'arn:aws:iam::{aws_account_id}:'"
    csp_accounts = context.cloud_account_manager.get_csp_accounts(filter=csp_filter)
    if csp_accounts.total:
        return csp_accounts.items[0]


def get_csp_accounts(context: Context, filter: str = "") -> CSPAccountListModel:
    """Get CSP Accounts, with optional filter applied.

    Args:
        context (Context): The test context
        filter (str, optional): A filter to apply to the GET call. Defaults to "".

    Returns:
        CSPAccountListModel: The returned list of CSP Accounts
    """
    logger.info(f"Getting CSP accounts: filter = {filter}")
    csp_accounts: CSPAccountListModel = context.cloud_account_manager.get_csp_accounts(filter=filter)
    logger.info(f"Success - Get CSP accounts: {csp_accounts.count} returned")
    return csp_accounts


def get_csp_account_by_csp_id(context: Context, csp_account_id: str) -> CSPAccountModel:
    """Get CSP account using the csp id

    Args:
        context (Context): context object
        account_id (str): account id

    Returns:
        CSPAccountModel: CSP account object
    """
    logger.info(f"Getting CSP account by id {csp_account_id}.")
    csp_account: CSPAccountModel = context.cloud_account_manager.get_csp_account_by_id(csp_account_id)
    assert csp_account is not None, f"Failed to retrieve csp_account: {csp_account_id}"
    logger.debug(f"CSP account info: {csp_account}")
    return csp_account


def get_csp_account_by_csp_name(context: Context, account_name: str, is_found_assert=True) -> CSPAccountModel:
    """Get CSP account using the csp name

    Args:
        context (Context): context object
        account_name (str): account name
        is_found_assert (bool): flag to assert if the account is found (default: True)

    Returns:
        CSPAccountModel: CSP account object
    """
    logger.info(f"Getting CSP account by name {account_name}.")
    csp_account: CSPAccountModel = context.cloud_account_manager.get_csp_account_by_name(account_name)
    if is_found_assert:
        assert csp_account is not None, f"Failed to retrieve csp_account: {account_name}"
    logger.debug(f"CSP account info: {csp_account}")
    return csp_account


def delete_csp_account(
    context: Context,
    csp_account_name: str,
    unprotect_account: bool = True,
    approve_dual_auth_request: bool = False,
    dual_auth_user: ProvidedUser = ProvidedUser.user_two,
    ms_office_context: MSOfficeContext = None,
    hpe_service_principal_name: str = "HPE GreenLake Discovery Application",
    csp_type: CspType = CspType.AWS,
):
    """
    Unregister AWS Account found by its name.
    Verify all purge tasks created after unregister request.

    Args:
        context (Context):  AWS protection context
        csp_account_name (str): csp aws account name
        unprotect_account (bool, optional): Unprotects account if set to True. Defaults to True.
        approve_dual_auth_request (bool, optional): Approves DualAuth request if set to 'True'
        dual_auth_user (ProvidedUser, optional): User who is supposed to authorize the Unprotect Account request
        ms_office_context (MSOfficeContext, optional): MSOfficeContext object. Provide if csp_type is AWS or MS365. Defaults to None
        hpe_service_principal_name (str, optional): Service Principal to be deleted from the Microsoft account. Defaults to 'HPE GreenLake Discovery Application'
        csp_type (CspType, optional): Type of the account. Defaults to 'CspType.AWS'
    """

    def _fetch_purge_task_and_wait_for_task_completion(context: Context, func: partial):
        logger.info(f"Validating {func} task")
        try:
            purge_tasks: Union[TaskList, list] = wait(
                lambda: func(),
                timeout_seconds=2400,
                sleep_seconds=60,
            )
        except TimeoutExpired:
            raise TimeoutError("Task was not found.")

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
            task_id=purge_task.id, user=context.user, timeout=TimeoutManager.unregister_purge_timeout
        )
        assert status.upper() == TaskStatus.success.value, f"Task {purge_task.name}: {purge_task.id} failed"
        logger.info(f"Task {purge_task.name}: {purge_task.id} successfully")
        # logger.info("Check for DPM child tasks")

        # TODO: Child task Purge EBS/EC2 Backups for Account - will not fail
        # tasks.wait_for_child_tasks(root_task_id=purge_task.id, user=context.user)
        # logger.info("Child tasks completed successfully")

    csp_account = context.cloud_account_manager.get_csp_account_by_name(name=csp_account_name)
    assert csp_account, f"Account not found: {csp_account_name}"

    if unprotect_account:
        logger.info(f"Unprotecting account {csp_account.id}")
        unprotect_csp_account(
            context=context,
            account_id=csp_account.id,
            approve_dual_auth_request=approve_dual_auth_request,
            dual_auth_user=dual_auth_user,
        )

    logger.info(f"Unregister AWS Account {csp_account.id}")
    delete_csp_account_with_expectation(context, csp_account_id=csp_account.id)

    # after delete account is complete, let's pause for some time to allow the purge tasks to get created.
    # Manual testing shows that the "Purge Backups for Account" task can appear at least 1 minute after
    # the "Purge asset inventory" task is complete.
    time.sleep(DELETE_ACCOUNT_SLEEP_SECONDS)

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_resource,
            user=context.user,
            task_name=Constants.UNREGISTER_INVENTORY_PURGE_TASK,
            resource_uri=f"{AssetTypeURIPrefix.ACCOUNTS_RESOURCE_URI_PREFIX_V1BETA1.value}{csp_account.id}",
            time_offset_minutes=60,
        ),
    )

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_resource,
            user=context.user,
            task_name=Constants.UNREGISTER_RDS_INVENTORY_PURGE_TASK.format(csp_account.name),
            resource_uri=f"{AssetTypeURIPrefix.ACCOUNTS_RESOURCE_URI_PREFIX.value}{csp_account.id}",
            time_offset_minutes=60,
        ),
    )

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_resource,
            user=context.user,
            task_name=Constants.UNREGISTER_SCHEDULER_PURGE_TASK,
            resource_uri=f"{AssetTypeURIPrefix.ACCOUNTS_RESOURCE_URI_PREFIX.value}{csp_account.id}",
            time_offset_minutes=60,
        ),
    )

    _fetch_purge_task_and_wait_for_task_completion(
        context=context,
        func=partial(
            tasks.get_tasks_by_name_and_customer_account,
            user=context.user,
            task_name=Constants.UNREGISTER_DPM_PURGE_TASK.format(csp_account.name),
            customer_id=csp_account.customerId,
            time_offset_minutes=180,
        ),
    )

    logger.info(f" AWS Account {csp_account.id} - Unregistered")

    if csp_type == CspType.AZURE or csp_type == CspType.MS365:
        logger.info(f"Retrieving Service Principal {hpe_service_principal_name}")
        ms_office_context = MSOfficeContext(initialize_users=False)
        service_principals = asyncio.get_event_loop().run_until_complete(
            ms_office_context.ms_one_outlook_manager.list_service_principals()
        )
        hpe_service_principals = [
            service_principal
            for service_principal in service_principals.value
            if service_principal.display_name == hpe_service_principal_name
        ]
        logger.info(f"Service Principals found: {hpe_service_principals}")

        for hpe_service_principal in hpe_service_principals:
            logger.info(f"Deleting Service Principal {hpe_service_principal.id}")
            asyncio.get_event_loop().run_until_complete(
                ms_office_context.ms_one_outlook_manager.delete_service_principal_by_id(hpe_service_principal.id)
            )


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


def unprotect_csp_account(
    context: Context,
    account_id: str,
    delete_backups: bool = True,
    expected_status_code: int = requests.codes.accepted,
    approve_dual_auth_request: bool = False,
    dual_auth_user: ProvidedUser = ProvidedUser.user_two,
) -> None:
    """
    Deletes backups and protection jobs for assets in a cloud account and waits for task completion

    Args:
        context (Context): context object
        account_id (str): CSP Account ID
        delete_backups (bool, optional): To delete of backups while unprotect account and only value "True" is accepted at the moment. Defaults to True.
        expected_status_code (int, optional): Expected status code. Defaults to requests.codes.accepted.
        approve_dual_auth_request (bool, optional): Approves DualAuth request if set to 'True'. Defaults to False
        dual_auth_user (ProvidedUser, optional): User who is supposed to authorize the Unprotect Account request. Defaults to ProvidedUser.user_two
    """
    csp_account = get_csp_account_by_csp_id(context=context, csp_account_id=account_id)
    logger.info(f"Unprotecting account {account_id}")
    task_id: str = context.cloud_account_manager.unprotect_csp_account(
        account_id=account_id,
        delete_backups=delete_backups,
        expected_status_code=expected_status_code,
    )

    if isinstance(task_id, str):
        if approve_dual_auth_request:
            logger.info(f"Getting unprotect account dual auth request for account {csp_account.name}")
            unprotect_account_dual_auth_request = get_pending_request_by_name_and_resource_uri(
                context=context,
                pending_request_name=DUAL_AUTH_UNPROTECT_ACCOUNT_TASK_NAME,
                resource_uri=csp_account.resourceUri,
            )

            logger.info(f"Approving unprotect account request for account {csp_account.name}")

            # Initializing context to user_two because the same user who initiated the request cannot approve it
            dual_auth_context = Context(test_provided_user=dual_auth_user)
            authorized_request = authorize_dual_auth_request(
                context=dual_auth_context,
                id=unprotect_account_dual_auth_request.id,
                approve=True,
            )
            logger.info(f"Account unprotect action authorized {authorized_request}")

        logger.info(f"Fetching parent task {task_id}")
        parent_task: Task = context.task_manager.get_task_object(task_id)
        logger.info(f"Fetched parent task {parent_task.name} - {parent_task.id}")

        child_task_ids: list[str] = []
        customer_id: str = parent_task.customer_id

        time.sleep(UNPROTECT_ACCOUNT_SLEEP_SECONDS)

        logger.info(f"Fetching task {Constants.UNPROTECT_ACCOUNT_DELETE_PROTECTION_JOBS}")
        task_list: list[Task] = context.task_manager.get_tasks_by_name_and_customer_account(
            task_name=Constants.UNPROTECT_ACCOUNT_DELETE_PROTECTION_JOBS,
            customer_id=customer_id,
        )
        assert task_list, f"Did not find the '{Constants.UNPROTECT_ACCOUNT_DELETE_PROTECTION_JOBS}' task"
        # otherwise we have the task
        unprotect_account_delete_protection_jobs_task = task_list[0]

        logger.info(f"Waiting for task {unprotect_account_delete_protection_jobs_task.name}")
        tasks.wait_for_task(task_id=unprotect_account_delete_protection_jobs_task.id, user=context.user, timeout=300)
        child_task_ids.append(unprotect_account_delete_protection_jobs_task.id)

        # Another task with the following pattern will be created
        # Remove data protection from account : Backups [963327e4-6114-5b9b-b514-2cbefa6c8dc1]
        # It will contain 4 child tasks:
        #   1. Cloud Backup Store Deletion
        #   2. Remove data protection from account – Machine instance and volume backups
        #   3. Remove data protection from account – RDS backups
        #   4. Remove data protection from account - K8s Application Backups
        num_subtasks: int = 4

        unprotect_account_delete_backups_parent_task_name = (
            Constants.UNPROTECT_ACCOUNT_DELETE_BACKUPS_PARENT_TASK.format(account_id)
        )

        logger.info(f"Fetching task {unprotect_account_delete_backups_parent_task_name}")
        task_list = context.task_manager.get_tasks_by_name_and_customer_account(
            task_name=unprotect_account_delete_backups_parent_task_name,
            customer_id=customer_id,
        )

        if len(task_list) == 0:
            # "name": "Remove data protection from account - Backups"
            # displayName: "Remove data protection from account - Backups [account_uuid]"
            task_name = Constants.UNPROTECT_ACCOUNT_DELETE_BACKUPS_PARENT_TASK.replace("[{0}]", "").strip()
            filter = f"sourceResourceUri eq '{csp_account.resourceUri}' and name eq '{task_name}'&sort=createdAt desc"
            filtered_tasks: TaskList = context.task_manager.get_filtered_tasks(filter=filter)
            assert filtered_tasks.total, f"Did not find the '{task_name}' task"
            unprotect_account_delete_backup_task = filtered_tasks.items[0]
        else:
            unprotect_account_delete_backup_task = task_list[0]

        # should generally get 4 tasks
        child_task_ids.append(unprotect_account_delete_backup_task.id)
        filter = f"parent/id eq '{unprotect_account_delete_backup_task.id}'"
        try:
            wait(
                lambda: len(context.task_manager.get_filtered_tasks(filter=filter).items) == num_subtasks,
                timeout_seconds=1200,
                sleep_seconds=30,
            )
        except TimeoutExpired:
            raise TimeoutError(
                f"Child tasks for Backup Deletion task - {unprotect_account_delete_backup_task.id}, were not found."
            )

        delete_backup_tasks = context.task_manager.get_filtered_tasks(filter=filter)
        for delete_backup_task in delete_backup_tasks.items:
            logger.info(f"Waiting for purge backup child task {delete_backup_task.display_name}")
            child_task_ids.append(delete_backup_task.id)
            tasks.wait_for_task(task_id=delete_backup_task.id, user=context.user, timeout=1200)

        logger.info(f"Waiting for {unprotect_account_delete_backups_parent_task_name} task to complete")
        tasks.wait_for_task(task_id=unprotect_account_delete_backup_task.id, user=context.user, timeout=1200)

        error_logs: list[str] = []
        for child_task_id in child_task_ids:
            task: Task = context.task_manager.get_task_object(child_task_id)
            if task.state.upper() != TaskStatus.success.value:
                log_messages: str = " ".join([logs.message for logs in task.log_messages])
                error_message: str = f"Task {task.name} failed with error {log_messages}"
                logger.error(error_message)
                error_logs.append(error_message)

        assert len(error_logs) == 0, error_logs

        wait(
            lambda: len(context.cloud_account_manager.get_csp_account_by_id(csp_account_id=account_id).services) == 0,
            timeout_seconds=300,
            sleep_seconds=10,
        )


def validate_csp_account(context: Context, csp_account_id: str) -> str:
    logger.info(f"Validating CSP account {csp_account_id}")
    csp_account_validate_model = context.cloud_account_manager.validate_csp_account(csp_account_id)

    # Validating task status
    sync_task_status = context.task_manager.wait_for_task(csp_account_validate_model.task_id, timeout=180).upper()
    assert (
        sync_task_status == TaskStatus.success.value or sync_task_status == TaskStatus.failed.value
    ), f"Actual:{sync_task_status}Expected[{TaskStatus.success.value}]||{TaskStatus.failed.value}]"
    logger.info(f"Success - Validate CSP account {csp_account_id}")
    return csp_account_validate_model.task_id


def generate_random_password() -> str:
    pwd = generate_random_string(20)
    # Ensure that the password satisfies all Azure rules.
    # 1) Contains an uppercase character
    pwd += "A"
    # 2) Contains a lowercase character
    pwd += "a"
    # 3) Contains a numeric digit
    pwd += "0"
    # 4) Contains a special character
    pwd += "@"
    return pwd


def validate_microsoft_csp_account(
    ms_office_context: MSOfficeContext,
    csp_account_id: str,
    driver: Union[Remote, Chrome],
    user_principal_name: str,
    display_name: str,
    mail_nickname: str,
    password: str = generate_random_password(),
    role_name="Global Administrator",
) -> CSPAccountValidateModel:
    """Activates a Microsoft account for making it accessible from DSCC

    Args:
        ms_office_context (MSOfficeContext): MSOfficeContext object
        csp_account_id (str): CSP ID of the account to be activated
        driver (Union[Remote, Chrome]): WebDriver object
        user_principal_name (str): Email ID to be associated with the user to be created
        display_name (str): Display name of the user
        mail_nickname (str): Nick name of the user
        password (str, optional): Password to be associated with the user account. Defaults to generate_random_password().
        role_name (str, optional): Name of the role to be assigned to the user. Defaults to "Global Administrator".

    Returns:
        CSPAccountValidateModel: CSPAccountValidateModel
    """
    user, role_assignment = ms_office_context.ms_one_outlook_manager.create_user_and_assign_role(
        user_principal_name=user_principal_name,
        display_name=display_name,
        mail_nickname=mail_nickname,
        role_name=role_name,
    )

    logger.info(f"Validating CSP account {csp_account_id}")
    csp_validate_account_response = ms_office_context.cloud_account_manager.validate_csp_account(csp_account_id)
    url = csp_validate_account_response.device_login_url
    device_code = csp_validate_account_response.authentication_code
    logger.info(f"URL = {url}, device_code = {device_code}")

    logger.info(f"Navigating to {url} to enter device code {device_code}")
    driver.get(url=url)
    device_code_page = DeviceCodePage(driver=driver)
    device_code_page.enter_device_code(device_code=device_code)

    logger.info(f"Signing in with user {user_principal_name} and {password}")
    microsoft_sign_in_page = MicrosoftSignInPage(driver=driver)
    microsoft_sign_in_page.login(email_address=user_principal_name, password=password)

    logger.info("Skipping MFA setup")
    authenticator_page = ActionRequiredPage(driver=driver)
    authenticator_page.skip_setting_authentication()

    logger.info("Accepting permissions")
    permission_requested_page = PermissionRequestedPage(driver=driver)
    permission_requested_page.accept_permissions()

    logger.info(f"Waiting for account validation task {csp_validate_account_response.task_id} to complete")
    tasks.wait_for_task(task_id=csp_validate_account_response.task_id, user=ms_office_context.user, timeout=180)

    ms_office_context.ms_one_outlook_manager.remove_role_assignment_and_delete_user_account(
        role_assignment_id=role_assignment.id,
        user_id=user.id,
    )

    return csp_validate_account_response


def modify_csp_account(context: Context, csp_account_id: str, name: str, suspended: bool) -> str:
    """Modify the Name and Suspended state of a CSP Account and wait for task completion.

    Args:
        context (Context): The test Context
        csp_account_id (str): DSCC Account ID
        name (str): The Name to set on the Account
        suspended (bool): The Suspended state to set on the Account

    Returns:
        str: The Modify Account Task ID
    """
    logger.info(f"Modifying CSP account {csp_account_id} with name {name} and suspended {suspended}")
    sync_task_id = context.cloud_account_manager.modify_csp_account(
        csp_account_id, PatchCSPAccountModel(name=name, suspended=suspended), requests.codes.accepted
    )

    # Validating task status
    sync_task_status = context.task_manager.wait_for_task(sync_task_id, timeout=100)
    assert sync_task_status.upper() == TaskStatus.success.value
    logger.info(f"Success - Modify CSP account {csp_account_id}")
    return sync_task_id


def negative_modify_csp_account(context: Context, csp_account_id: str, payload: str, expected_status_code: int) -> None:
    context.cloud_account_manager.modify_csp_account(csp_account_id, payload, expected_status_code)


def delete_csp_account_with_expectation(
    context: Context, csp_account_id: str, expectation: TaskStatus = TaskStatus.success.value
):
    status_code, task_id = context.cloud_account_manager.raw_delete_csp_account_status_code_task_id(
        csp_account_id=csp_account_id
    )
    assert (
        status_code == requests.codes.accepted
    ), f"DELETE /csp-accounts/{csp_account_id} Failed with status_code: {status_code}"

    sync_task_status = context.task_manager.wait_for_task(task_id, timeout=100)
    assert sync_task_status.upper() == expectation


def delete_csp_account_failure(context: Context, csp_account_id: str):
    logger.info(f"Trying to delete CSP account {csp_account_id} using user with 'Operator' role. Expecting failure")
    try:
        context.cloud_account_manager.raw_delete_csp_account_status_code_task_id(csp_account_id=csp_account_id)
    except FailedRetryWithResponseException as e:
        response = e.response
        assert response.status_code == 403
        logger.info("delete_csp_account_return_response() status_code: 403")


def create_csp_account(context: Context, csp_id: str, name: str, csp_type: CspType = CspType.AWS) -> CSPAccountModel:
    """Create a Cloud Service Provider account

    Args:
        context (Context): The test Context
        csp_id (str): Cloud Service Provider ID
           For CspType.AWS, this is in the form:     arn:aws:iam::{aws_csp_id}:
           For CspType.AZURE, this is in the form:   {azure_tenant_id}
           For CspType.MS365, this is in the form:   {ms_tenant_id}
        name (str): The name to give to the CSP Account
        csp_type (CspType, optional): The Cloud Service Provider type. Defaults to CspType.AWS

    Returns:
        CSPAccountModel: The CSPAccount object
    """
    logger.info(f"Creating CSP account with name {name} and csp_id {csp_id} ,{csp_type=}")
    csp_account = context.cloud_account_manager.create_csp_account(csp_id=csp_id, name=name, csp_type=csp_type)
    assert csp_account, f"Failed to create csp_account: {name}"
    logger.info(f"Success - Create CSP account with name {name} and csp_id {csp_id}")
    return csp_account


def create_csp_account_failure(
    context: Context, name: str, csp_id: str, csp_type: CspType = CspType.AWS, status_code: int = 403
):
    """Create a Cloud Service Provider account expecting failure.

    Args:
        context (Context): The test Context
        name (str): The name to give to the CSP Account
        csp_id (str): Cloud Service Provider ID
           For CspType.AWS, this is in the form:     arn:aws:iam::{aws_csp_id}:
           For CspType.AZURE, this is in the form:   {azure_tenant_id}
           For CspType.MS365, this is in the form:   {ms_tenant_id}
        csp_type (CspType, optional): The Cloud Service Provider type. Defaults to CspType.AWS.
        status_code (int, optional): The expected status code. Defaults to 403.
    """
    try:
        context.cloud_account_manager.create_csp_account_status_code(csp_id=csp_id, name=name, csp_type=csp_type)
    except FailedRetryWithResponseException as e:
        response = e.response
        assert response.status_code == status_code
        logger.info("create_csp_account() status_code: 403")


def get_csp_account_onboarding_template(context: Context, csp_account_id: str) -> CSPOnboardingTemplateModel:
    logger.info(f"Getting CSP account onboarding template for {csp_account_id}")
    onboarding_template = context.cloud_account_manager.get_csp_account_onboarding_template(
        csp_account_id=csp_account_id
    )
    assert onboarding_template, "failed to get onboarding template"
    logger.info(f"Success - Get CSP account onboarding template for {csp_account_id}")
    return onboarding_template
