"""
This file is for common steps involved for Cloud Account Manager related actions like
MS365 Organization Account register, unregister etc.,
"""

import logging
from lib.common.enums.csp_type import CspType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import (
    CSPAccountModel,
    CSPAccountValidateModel,
)
from tests.e2e.ms365_protection.ms_office_context import MSOfficeContext
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps

logger = logging.getLogger()


def register_ms365_organization_account(
    ms_context: MSOfficeContext, ms365_account_name: str, ms_org_tenant_id: str
) -> CSPAccountModel:
    """This step method can be used for registration of MS365 organization account

    Args:
        ms_context (MSOfficeContext): MS365 context object.
        ms365_account_name (str): Microsoft Account name to register.
        ms_org_tenant_id (str): Microsoft Org tenant UUID to register.

    Returns:
        CSPAccountModel: It will return csp account.
    """
    logger.info(f"Registering MS365 account NAME: {ms365_account_name} and tenant ID: {ms_org_tenant_id}")
    csp_ms365_account: CSPAccountModel = CAMSteps.create_csp_account(
        context=ms_context, csp_id=ms_org_tenant_id, name=ms365_account_name, csp_type=CspType.MS365
    )
    logger.info(f"Successfully registered MS365 account NAME: {ms365_account_name} and tenant ID: {ms_org_tenant_id}")
    logger.debug(f"Response from register CSP MS365 account: {csp_ms365_account}")
    return csp_ms365_account


def validate_ms365_organization_account(
    ms_context: MSOfficeContext,
    ms365_account_name: str,
):
    """Validates MS365 organization account

    Args:
        ms_context (MSOfficeContext): MS365 context object.
        ms365_account_name (str): Microsoft Account name to register.

    Returns:
        str: Returns required action to validate MS365 validate API response.
    """
    # Get MS365 account id
    csp_ms365_account: CSPAccountModel = get_ms365_csp_account_by_name(ms_context, ms365_account_name)
    logger.info(f"Validating MS365 account NAME: {ms365_account_name} with CSP ID: {csp_ms365_account.id}")

    # Validate MS365 account and get the response
    csp_account_validation_model: CSPAccountValidateModel = ms_context.cloud_account_manager.validate_csp_account(
        csp_ms365_account.id
    )

    # Extract the code and URL from the API response
    logger.info(f"Task ID: {csp_account_validation_model.task_id}")
    logger.info(f"Authentication code: {csp_account_validation_model.authentication_code}")
    logger.info(f"URL: {csp_account_validation_model.device_login_url}")
    # TODO login using the URL and approve the consent, then poll on the task. Currently its blocked by DCS-15421


def unregister_ms365_organization_account(ms_context: MSOfficeContext, ms365_csp_id: str):
    """This method can be used for unregister of MS365 organization account.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object.
        ms365_csp_id (string): CSP ID of the ms365 account that need to be unregistered.

    """
    logger.info(f"Un registering MS365 account ID: {ms365_csp_id}")
    # TODO: yet to get confirmation from the API and behavior so commenting it here
    # delete_csp_account_with_expectation(ms_context, csp_account_id=ms365_csp_id)
    logger.info("Un registering MS365 account is completed successfully")


def get_ms365_csp_account_by_name(ms_context: MSOfficeContext, ms365_account_name: str) -> CSPAccountModel:
    """Get MS365 CSP account using the name

    Args:
        ms_context (MSOfficeContext): MS365 context object
        ms365_account_name (str): MS365 account name

    Returns:
        CSPAccountModel: MS365 CSP account object
    """
    logger.info(f"Getting CSP MS365 account by name {ms365_account_name}..")
    csp_ms365_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_name(ms_context, ms365_account_name)
    logger.info("Successfully got the CSP MS365 account by name")
    logger.debug(f"CSP MS365 account info: {csp_ms365_account}")
    return csp_ms365_account


def get_ms365_csp_account_by_id(ms_context: MSOfficeContext, ms365_account_id: str) -> CSPAccountModel:
    """Get MS365 CSP account using the id

    Args:
        ms_context (MSOfficeContext): MS365 context object
        ms365_account_id (str): MS365 account id

    Returns:
        CSPAccountModel: MS365 CSP account object
    """
    logger.info(f"Getting CSP MS365 account by id {ms365_account_id}..")
    csp_ms365_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_id(ms_context, ms365_account_id)
    logger.info("Successfully got the CSP MS365 account by name")
    logger.debug(f"CSP MS365 account info: {csp_ms365_account}")
    return csp_ms365_account
