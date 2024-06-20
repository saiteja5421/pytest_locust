import logging

from lib.common.enums.cvsa import VaultCredentialType
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from tests.steps.aws_protection.cvsa.storeonce_steps import get_cvsa_storeonce
from tests.steps.aws_protection.cvsa.vault_steps import get_cvsa_credentials

logger = logging.getLogger()


def write_data_to_cvsa_cloud_store(cloud_vm_mgr: CloudVmManager, kafka, catalyst_store_name) -> str:
    logger.info(f"Write data to cloud store: {catalyst_store_name}, customer id: {kafka.account_id}")
    storeonce = get_cvsa_storeonce(cloud_vm_mgr, kafka)
    store_credentials = get_cvsa_credentials(kafka.cvsa_id, VaultCredentialType.CATALYST_STORE_CLIENT)
    target_id = storeonce.write_data(catalyst_store_name, kafka.cam_account_id, store_credentials=store_credentials)
    logger.info(f"Success - Write data to cloud store: {catalyst_store_name}, customer id: {kafka.account_id}")
    return target_id
