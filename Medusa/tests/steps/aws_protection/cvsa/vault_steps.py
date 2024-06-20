import logging

from requests import Response

from lib.common.enums.cvsa import VaultCredentialType
from lib.platform.storeonce.models.store_once import StoreOnceCredentials
from lib.platform.vault import VaultManager
from waiting import wait

logger = logging.getLogger()


def call_vault_for_credentials(cvsa_id, credential_type: VaultCredentialType) -> Response:
    logger.info(f"Get call for {cvsa_id} credentials from vault")
    vault_manager = VaultManager()
    secret_path = f"/storagecentral/app/atlantia/cvsa/{cvsa_id}/{credential_type.value}"
    response = vault_manager.get_secret(secret_path)
    logger.info(f"Get call for {cvsa_id} credentials from vault: {response}")
    return response


def verify_deleted_cvsa_credentials(cvsa_id):
    logger.info(f"Verify vault credentials cvsa id deletion:{cvsa_id}")
    all_secret_names = [
        VaultCredentialType.ADMIN,
        VaultCredentialType.CATALYST_STORE,
        VaultCredentialType.CATALYST_STORE_CLIENT,
        VaultCredentialType.CATALYST_STORE_ENCRYPTION_KEY,
        VaultCredentialType.CONSOLE,
    ]
    for credential_type in all_secret_names:
        wait(
            lambda: call_vault_for_credentials(cvsa_id=cvsa_id, credential_type=credential_type).status_code == 404,
            timeout_seconds=300,
            sleep_seconds=15,
        )
    logger.info(f"Vault credentials deletion verified, cvsa id: {cvsa_id}")


def get_cvsa_credentials(cvsa_id: str, credential_type: VaultCredentialType) -> StoreOnceCredentials:
    logger.info(f"Get cvsa {cvsa_id} credentials from vault")
    vault_manager = VaultManager()
    secret_path = f"/storagecentral/app/atlantia/cvsa/{cvsa_id}/{credential_type.value}"
    secret = vault_manager.get_secret(secret_path).json()["data"]["data"]
    logger.info(f"Cvsa {cvsa_id} - {credential_type.value} credentials found in vault")
    return StoreOnceCredentials(username=secret["user"], password=secret["password"])


def verify_vault_credentials(cvsa_id: str):
    logger.info(f"Verify vault credentials cvsa id:{cvsa_id}")
    all_secret_names = [
        VaultCredentialType.ADMIN,
        VaultCredentialType.CATALYST_STORE,
        VaultCredentialType.CATALYST_STORE_CLIENT,
        VaultCredentialType.CATALYST_STORE_ENCRYPTION_KEY,
        VaultCredentialType.CONSOLE,
    ]
    for credential_type in all_secret_names:
        credential = get_cvsa_credentials(cvsa_id=cvsa_id, credential_type=credential_type)
        assert credential.username
        assert credential.password
    logger.info(f"Vault credentials verified, cvsa id:{cvsa_id}")


def get_credentials_for_copy(cvsa_id: str):
    all_secret_names = [
        VaultCredentialType.CATALYST_STORE,
        VaultCredentialType.CATALYST_STORE_ENCRYPTION_KEY,
    ]
    return [get_cvsa_credentials(cvsa_id, credential_type) for credential_type in all_secret_names]
