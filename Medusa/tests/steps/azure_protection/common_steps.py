import logging
from lib.common.enums.csp_type import CspType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.secret_manager.models.domain_model.secrets_model import SecretModel

from tests.e2e.aws_protection.context import Context
from tests.steps.secret_manager.secret_manager_steps import add_azure_credentials_to_secrets
from lib.common.enums.secret_subclassifier_properties import SubclassifierProperties
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps


logger = logging.getLogger()


def register_azure_account(
    context: Context, azure_account_name: str, tenant_id: str, client_id: str, client_secret: str
) -> CSPAccountModel:
    """
    Unregisters the azure account from DSCC if already present and re-registers it
    Add azure secret credentials before register an azure account

    Args:
        context (Context): Specify the context
        azure_account_name (str): Azure account name
        Note: Secret name and azure account name should be same
        tenant_id (str): azure tenant id
        client_id (str): azure application client id
        client_secret (str):azure application client secret value
    Returns:
        CSPAccountModel: Registered CSP Account
    """
    logger.info(f"Add azure secret name: {azure_account_name} into service")
    add_secret_response = _verify_and_add_azure_secret_credentials(
        context=context,
        azure_account_name=azure_account_name,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    assert add_secret_response, f"Could not add the azure secret with name : {azure_account_name}"
    logger.info(f"Successfully added azure secret with the name {azure_account_name}")

    logger.info(f"Registering account NAME: {azure_account_name} for tenant id {tenant_id}")
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, azure_account_name)
    if csp_account:
        logger.info("Removing Regression test account")
        CAMSteps.delete_csp_account(context=context, csp_account_name=csp_account.name)
    csp_account = CAMSteps.create_csp_account(context, tenant_id, azure_account_name, CspType.AZURE)
    return csp_account


def _verify_and_add_azure_secret_credentials(
    context: Context, azure_account_name: str, tenant_id: str, client_id: str, client_secret: str
) -> SecretModel:
    """
    Add azure secret credentials into DSCC secret if azure_account_name or tenant id already exists delete it

    Args:
        context (Context): Specify the context
        azure_account_name (str): Azure account name
        tenant_id (str): azure tenant id
        client_id (str): azure application client id
        client_secret (str):azure application client secret value
    Returns:
        SecretModel: Reference to secret definition
    """
    filter = f"subclassifier eq '{SubclassifierProperties.AZURE_SPCLIENT.value}'"
    # Get all the secret definitions as response based on filter
    all_secret_response = context.secret_manager.get_all_secrets(filter=filter)
    logger.info(f"Response of all secret definitions {all_secret_response} with filter {filter}")

    # verify secret name and tenant id exists and delete it if exists
    for secret_response in all_secret_response.items:
        if secret_response.subclassifier.properties.CLIENT_ID == client_id and (
            secret_response.subclassifier.properties.TENANT_ID == tenant_id
            or secret_response.name == azure_account_name
        ):
            context.secret_manager.delete_secret_by_id(secret_id=secret_response.id)
            logger.info(f"Secret id {secret_response.id} is successfully deleted from service")

    post_secret_response = add_azure_credentials_to_secrets(
        context=context,
        name=azure_account_name,
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
    )
    return post_secret_response
