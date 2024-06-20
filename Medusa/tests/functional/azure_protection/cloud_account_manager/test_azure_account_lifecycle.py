import json
import logging
import os
import uuid

from pytest import fixture, mark
from requests import codes, Response

from lib.common.enums.account_validation_status import ValidationStatus
from lib.common.enums.csp_type import CspType
from lib.common.enums.provided_users import ProvidedUser
from lib.dscc.backup_recovery.aws_protection.accounts.models.csp_account import CSPAccount
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.cloud_account_manager_steps import (
    create_csp_account,
    create_csp_account_failure,
    delete_csp_account_with_expectation,
    get_csp_account_by_csp_id,
    get_csp_account_by_csp_name,
    modify_csp_account,
    negative_modify_csp_account,
    validate_csp_account,
)


logger = logging.getLogger()
tenant_id = os.environ.get("AZURE_TENANT_ID")
azure_account_name = "AzureAccount-" + str(uuid.uuid4())
updated_azure_account_name: str = "UpdatedAzureAccount-" + str(uuid.uuid4())


@fixture(scope="session")
def context():
    return Context(test_provided_user=ProvidedUser.user_one, initialize_minimal=True)


@mark.cam_azure
@mark.xfail
def test_register_azure_account(context: Context):
    # Register an Azure account
    azure_account: CSPAccount = create_csp_account(context, tenant_id, azure_account_name, CspType.AZURE)

    # Fetching registered account
    fetched_azure_account: CSPAccount = get_csp_account_by_csp_id(context=context, csp_account_id=azure_account.id)
    assert azure_account.name == fetched_azure_account.name


@mark.cam_azure
@mark.xfail
def test_register_duplicate_azure_account(context: Context):
    # Register a duplicate Azure account
    create_csp_account_failure(
        context=context,
        csp_id=tenant_id,
        name=azure_account_name,
        csp_type=CspType.AZURE,
        status_code=codes.bad_request,
    )


@mark.cam_azure
@mark.xfail
def test_validate_csp_account_before_update(context: Context):
    # Fetching created account
    account: CSPAccount = get_csp_account_by_csp_name(context, account_name=azure_account_name)

    # Validating customer account
    validate_csp_account(context=context, csp_account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = get_csp_account_by_csp_id(context=context, csp_account_id=account.id)
    validation_status = fetched_csp_account.validationStatus
    assert (
        validation_status == ValidationStatus.passed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"


@mark.cam_azure
@mark.xfail
def test_suspend_csp_account(context: Context):
    # Fetching created account
    account: CSPAccount = get_csp_account_by_csp_name(context, account_name=azure_account_name)

    # Updating account name and suspending it
    modify_csp_account(context=context, csp_account_id=account.id, name=updated_azure_account_name, suspended=True)

    # Fetching the updated account
    account: CSPAccount = get_csp_account_by_csp_id(context=context, csp_account_id=account.id)
    assert account.name == updated_azure_account_name
    assert account.suspended is True


@mark.cam_azure
@mark.xfail
def test_validate_csp_account_while_suspended(context: Context):
    # Fetching created account
    account: CSPAccount = get_csp_account_by_csp_name(context, account_name=updated_azure_account_name)

    # Validating customer account
    validate_csp_account(context=context, csp_account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = get_csp_account_by_csp_id(context=context, csp_account_id=account.id)
    validation_status = fetched_csp_account.validationStatus
    assert (
        validation_status == ValidationStatus.failed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"


@mark.cam_azure
@mark.xfail
def test_resume_csp_account(context: Context):
    # Fetching created account
    account: CSPAccount = get_csp_account_by_csp_name(context, account_name=updated_azure_account_name)

    # Resuming Account
    modify_csp_account(context=context, csp_account_id=account.id, name=updated_azure_account_name, suspended=False)

    # Fetching the updated account
    account: CSPAccount = get_csp_account_by_csp_id(context=context, csp_account_id=account.id)
    assert account.suspended is False


@mark.cam_azure
@mark.xfail
def test_validate_csp_account_after_resume(context: Context):
    # Fetching created account
    account: CSPAccount = get_csp_account_by_csp_name(context, account_name=updated_azure_account_name)

    # Validating customer account
    validate_csp_account(context=context, csp_account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = get_csp_account_by_csp_id(context=context, csp_account_id=account.id)
    validation_status = fetched_csp_account.validationStatus
    assert (
        validation_status == ValidationStatus.passed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"


@mark.cam_azure
@mark.xfail
def test_invalid_update_csp_account(context: Context):
    # Fetching created account
    account: CSPAccount = get_csp_account_by_csp_name(context, account_name=updated_azure_account_name)

    # Updating Account Immutable Fields
    updatedCustomerId = account.customerId + "extra"
    negative_modify_csp_account(
        context=context,
        csp_account_id=account.id,
        payload=json.dumps({"customerId": f"{updatedCustomerId}"}),
        expected_status_code=codes.bad_request,
    )

    # Fetching the updated account
    account2: CSPAccount = get_csp_account_by_csp_id(context=context, csp_account_id=account.id)
    assert account2.customerId == account.customerId, (
        f"PATCH /csp-accounts/{azure_account_name} allowed customerId update "
        + f"{account.customerId} to {account2.customerId}"
    )


@mark.cam_azure
@mark.xfail
def test_delete_csp_account(context: Context):
    account: CSPAccount = get_csp_account_by_csp_name(context, account_name=updated_azure_account_name)

    # Deleting created account
    delete_csp_account_with_expectation(context, account.id)

    # Validating that the deleted account is no longer present
    deleted_account: CSPAccount = get_csp_account_by_csp_name(
        context, account_name=updated_azure_account_name, is_found_assert=False
    )
    assert deleted_account is None
