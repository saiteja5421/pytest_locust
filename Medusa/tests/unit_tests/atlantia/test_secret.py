import logging
import os

from pytest import fixture, mark
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.cloud_account_manager_steps import get_csp_account_by_csp_name, validate_csp_account
from tests.steps.azure_protection.common_steps import register_azure_account
import tests.steps.aws_protection.common_steps as CommonSteps
from lib.common.enums.task_status import TaskStatus
from tests.steps.secret_manager.secret_manager_steps import add_azure_credentials_to_secrets
from utils.timeout_manager import TimeoutManager
from tests.steps.tasks import tasks

logger = logging.getLogger()

os.environ["CONFIG_FILE"] = "variables_eks_sanity_scdev01"


@fixture(scope="module")
def context():
    context = Context()
    yield context
    logger.info(f"\n{'Test teardown Start'.center(40, '*')}")

    logger.info(f"\n{'Test teardown Complete'.center(40, '*')}")


@mark.eks_sanity
@mark.order(100)
def test_secret(context: Context):
    secret_response = context.secret_manager.get_secret_by_id(secret_id="aaf352fc-5e3e-11ee-b4bc-0100ea1bc234")
    logger.info(f"Response {secret_response}")

    # NOTE# For now implemented only to retrieve secrets of azure,oauth and ssh_pair
    all_secret_response = context.secret_manager.get_all_secrets()
    logger.info(f"Response {all_secret_response}")

    post_response = add_azure_credentials_to_secrets(
        context=context,
        name="test40",
        service="ser",
        client_id="6777",
        client_secret="777",
        tenant_id="888",
    )
    logger.info(f"Response {post_response}")

    register_azure_account(
        context=context,
        azure_account_name="azure-pqa-test",
        tenant_id="xxxx",
        client_id="xxxxx",
        client_secret="xxxx",
    )
    csp_account: CSPAccountModel = get_csp_account_by_csp_name(context, account_name="azure-pqa-test")
    task_id = validate_csp_account(context=context, csp_account_id=csp_account.id)
    # check the task
    task_status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=TimeoutManager.standard_task_timeout)
    assert task_status == TaskStatus.success.value.lower(), f"Validate account status: {task_status}"

    CommonSteps.refresh_inventory_with_retry(context, csp_account.id)
