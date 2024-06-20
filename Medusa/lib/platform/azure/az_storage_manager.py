import logging
from typing import Union

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.storage import StorageManagementClient

logger = logging.getLogger()


class AZStorageManager:
    def __init__(
        self,
        credential: Union[DefaultAzureCredential, ClientSecretCredential],
        subscription_id: str,
    ) -> None:
        self.storage_client = StorageManagementClient(credential, subscription_id)
