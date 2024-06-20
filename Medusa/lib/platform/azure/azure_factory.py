import logging
import os

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource import SubscriptionClient

from lib.platform.azure.az_disk_manager import AZDiskManager
from lib.platform.azure.az_disk_snapshot_manager import AZDiskSnapshotManager
from lib.platform.azure.az_network_manager import AZNetworkManager
from lib.platform.azure.az_resource_manager import AZResourceManager
from lib.platform.azure.az_storage_manager import AZStorageManager
from lib.platform.azure.az_vm_image_manager import AZVMImageManager
from lib.platform.azure.az_vm_manager import AZVMManager

logger = logging.getLogger()


class InvalidSubscriptionID(BaseException): ...


class Azure:
    def __init__(
        self,
        subscription_id: str = None,
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        resource_group_name: str = None,
    ):
        if not tenant_id or not client_id or not client_secret:
            self._credential = DefaultAzureCredential()
        else:
            self._credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        if subscription_id:
            self.subscription_id = subscription_id
        else:
            self.subscription_id = self._get_subscription_id(self._credential)
        self.resource_group_name = resource_group_name

    @property
    def az_vm_manager(self):
        return AZVMManager(
            credential=self._credential,
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
        )

    @property
    def az_vm_image_manager(self):
        return AZVMImageManager(credential=self._credential, subscription_id=self.subscription_id)

    @property
    def az_disk_manager(self):
        return AZDiskManager(credential=self._credential, subscription_id=self.subscription_id)

    @property
    def az_disk_snapshot_manager(self):
        return AZDiskSnapshotManager(credential=self._credential, subscription_id=self.subscription_id)

    @property
    def az_storage_manager(self):
        return AZStorageManager(credential=self._credential, subscription_id=self.subscription_id)

    @property
    def az_resource_manager(self):
        return AZResourceManager(credential=self._credential, subscription_id=self.subscription_id)

    @property
    def az_network_manager(self):
        return AZNetworkManager(credential=self._credential, subscription_id=self.subscription_id)

    @staticmethod
    def _get_subscription_id(creds) -> str:
        subscription_client = SubscriptionClient(creds)
        try:
            subscription_ids = [x.subscription_id for x in subscription_client.subscriptions.list()]
        except ClientAuthenticationError as error:
            logger.error(f"ClientAuthenticationError for subscription_client: {repr(subscription_client)}")
            logging.error(
                "Environment credentials variables are: "
                f'{os.getenv("AZURE_FEDERATED_TOKEN_FILE")}, '
                f'{os.getenv("AZURE_TENANT_ID")}, '
                f'{os.getenv("AZURE_CLIENT_ID")},'
                f'{os.getenv("AZURE_AUTHORITY_HOST")}'
            )
            raise error
        if len(subscription_ids) < 1:
            raise InvalidSubscriptionID(
                f"No Subscriptions found: {subscription_ids} for {os.getenv('AZURE_TENANT_ID')}"
            )
        return subscription_ids[0]
