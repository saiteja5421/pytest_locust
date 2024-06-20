import logging
from lib.dscc.secret_manager.models.domain_model.secret_payload_model import (
    AddAzureSecretModel,
    ObjectAzureSPClientModel,
    ObjectAzureSubclassifierModel,
)
from lib.dscc.secret_manager.models.domain_model.secrets_model import SecretModel
from tests.e2e.aws_protection.context import Context

logger = logging.getLogger()


def add_azure_credentials_to_secrets(
    context: Context,
    name: str,
    client_id: str,
    client_secret: str,
    tenant_id: str,
    service: str = "Backup and Recovery Service",
) -> SecretModel:
    """
    Add azure credentials to secret

    Args:
        context (Context): Test context
        name (str): name of the secret to be added
        service (str): The name of the DSCC service associated with the Secret
        client_id (str): azure client id
        client_secret (str): azure client secret id
        tenant_id (str): azure tenant id
    Returns:
        SecretModel: Add secret payload
    """
    azure_sp_client: ObjectAzureSPClientModel = ObjectAzureSPClientModel(
        client_id=client_id, client_secret=client_secret, tenant_id=tenant_id
    )
    sub_classifier: ObjectAzureSubclassifierModel = ObjectAzureSubclassifierModel(azure_sp_client=azure_sp_client)

    azure_spclient_payload: AddAzureSecretModel = AddAzureSecretModel(name, service, sub_classifier)

    response = context.secret_manager.add_azure_secrets(add_secret_payload=azure_spclient_payload)

    logger.info(f"Response of the secret name {name} added {response}")

    return azure_spclient_payload
