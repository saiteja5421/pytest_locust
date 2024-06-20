"""Documentation

https://learn.microsoft.com/en-us/python/api/azure-mgmt-compute/azure.mgmt.compute.v2020_09_30.operations.disksoperations?view=azure-python
"""

import logging
from typing import Union

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (
    Disk,
    DiskAccess,
    DiskSku,
    DiskUpdate,
    NetworkAccessPolicy,
    OperatingSystemTypes,
    DiskStorageAccountTypes,
    CreationData,
    DiskCreateOption,
)
from azure.core.exceptions import HttpResponseError
from lib.common.enums.az_regions import AZRegion, AZZone
from lib.platform.aws_boto3.models.instance import Tag

logger = logging.getLogger()


class AZDiskManager:
    def __init__(
        self,
        credential: Union[DefaultAzureCredential, ClientSecretCredential],
        subscription_id: str,
    ) -> None:
        self.compute_client = ComputeManagementClient(credential, subscription_id)

    def get_disk_by_name(self, resource_group_name: str, disk_name: str) -> Disk:
        """Returns disk queried by its name

        Args:
            resource_group_name (str): Resource Group name
            disk_name (str): Disk name

        Returns:
            Disk: Disk object if found, None otherwise
        """
        disk: Disk = None

        try:
            disk = self.compute_client.disks.get(resource_group_name=resource_group_name, disk_name=disk_name)
            logger.info(f"Fetched disk is {disk}")
        except HttpResponseError as error:
            logger.info(f"Error in GET call: {error.message}")

        return disk

    def get_all_disks_in_subscription(self) -> list[Disk]:
        """Fetches all the Disks under account's subscription

        Returns:
            list[Disk]: list of Disk
        """
        all_disks = self.compute_client.disks.list()
        disks: list[Disk] = [disk for disk in all_disks]
        logger.info(f"Disks found are {disks}")
        return disks

    def get_all_disks_by_resource_group_name(self, resource_group_name: str) -> list[Disk]:
        """Fetches all the Disks under the provided resource group

        Args:
            resource_group_name (str): Resource Group Name

        Returns:
            list[Disk]: list of Disk
        """
        all_disks = self.compute_client.disks.list_by_resource_group(resource_group_name=resource_group_name)
        disks: list[Disk] = [disk for disk in all_disks]
        logger.info(f"Disks under RG {resource_group_name} are {disks}")
        return disks

    def get_all_disks_by_tag(self, tag: Tag) -> list[Disk]:
        """Fetches all the Disks containing the provided Tag
        NOTE: Azure does not have a tag model class.
        It expects a dict[str, str], that's why reusing Tag class from AWS

        Args:
            tag (Tag): Tag of the VMs

        Returns:
            list[Disk]: list of Virtual Machines
        """
        all_disks = self.get_all_disks_in_subscription()
        disks: list[Disk] = [
            disk
            for disk in all_disks
            if disk.tags and tag.Key in disk.tags.keys() and disk.tags.get(tag.Key) == tag.Value
        ]
        logger.info(f"Disks with tag {tag} are {disks}")
        return disks

    def get_all_disks_in_resource_group_by_tag(self, resource_group_name: str, tag: Tag) -> list[Disk]:
        """Fetches all the Disks containing the provided Tag
        NOTE: Azure does not have a tag model class.
        It expects a dict[str, str], that's why reusing Tag class from AWS

        Args:
            resource_group_name (str): Resource Group name
            tag (Tag): Tag of the VMs

        Returns:
            list[Disk]: list of Virtual Machines
        """
        all_disks = self.get_all_disks_by_resource_group_name(resource_group_name=resource_group_name)
        disks: list[Disk] = [
            disk
            for disk in all_disks
            if disk.tags and tag.Key in disk.tags.keys() and disk.tags.get(tag.Key) == tag.Value
        ]
        logger.info(f"Disks with tag {tag} are {disks}")
        return disks

    def get_all_disks_by_location(self, resource_group_name: str, location: AZRegion) -> list[Disk]:
        """Fetches all the Disks under the provided location

        Args:
            resource_group_name (str): Resource Group name
            location (AZRegion): Location under which disks should be found

        Returns:
            list[Disk]: list of Virtual Machines
        """
        all_disks = self.get_all_disks_by_resource_group_name(resource_group_name=resource_group_name)
        disks: list[Disk] = [disk for disk in all_disks if disk.location == location.value]
        logger.info(f"Disks under location {location} are {disks}")
        return disks

    def create_disk(
        self,
        resource_group_name: str,
        disk_name: str,
        disk_size_gb: int,
        disk_iops_read_only: int,
        tags: dict[str, str] = {},
        location: AZRegion = AZRegion.UK_SOUTH,
        az_zones: list[AZZone] = [AZZone.ZONE_1],
        os_type: OperatingSystemTypes = OperatingSystemTypes.LINUX,
        disk_storage_account_type: DiskStorageAccountTypes = DiskStorageAccountTypes.STANDARD_SSD_LRS,
    ) -> Disk:
        """Creates a disk with the specified parameters

        Args:
            resource_group_name (str): Resource Group name
            disk_name (str): Disk name
            disk_size_gb (int): Disk size in GB
            disk_iops_read_only (int): Disk IOPS. Some valid values are 500, 2000, 4000, and 6000
            Check documentation for more: https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types

            tags (dict[str, str], optional): Tags to be added to the disk. Defaults to {}.
            location (AZRegion, optional): Location where the disk should be created. Defaults to AZRegion.UK_SOUTH.
            az_zones (list[AZZone], optional): Zone under which the disk should be created. Defaults to [AZZone.ZONE_1].
            os_type (OperatingSystemTypes, optional): OS type of the disk. Defaults to OperatingSystemTypes.LINUX.
            disk_storage_account_type (DiskStorageAccountTypes, optional): Disk type.
            Defaults to DiskStorageAccountTypes.STANDARD_SSD_LRS -> cheapest option

        Returns:
            Disk: Created Disk object
        """
        zones = [zone.value for zone in az_zones]

        disk_sku = DiskSku(name=disk_storage_account_type)

        disk = Disk(
            location=location.value,
            sku=disk_sku,
            tags=tags,
            zones=zones,
            os_type=os_type,
            disk_size_gb=disk_size_gb,
            disk_iops_read_only=disk_iops_read_only,
            creation_data=CreationData(create_option=DiskCreateOption.EMPTY),  # For creating an empty disk
        )

        logger.info(f"Creating disk {disk_name} in location {location.value}, in RG {resource_group_name}")
        disk: Disk = self.compute_client.disks.begin_create_or_update(
            resource_group_name=resource_group_name,
            disk_name=disk_name,
            disk=disk,
        ).result()

        assert disk.provisioning_state == "Succeeded"

        logger.info(f"Disk {disk_name} created successfully")
        return disk

    def create_vm_shared_disk(
        self,
        resource_group_name: str,
        disk_name: str,
        disk_size_gb: int,
        disk_iops_read_only: int,
        tags: dict[str, str] = {},
        max_shares: int = 1,
        location: AZRegion = AZRegion.UK_SOUTH,
        az_zones: list[AZZone] = [AZZone.ZONE_1],
        os_type: OperatingSystemTypes = OperatingSystemTypes.LINUX,
        disk_storage_account_type: DiskStorageAccountTypes = DiskStorageAccountTypes.STANDARD_SSD_LRS,
    ) -> Disk:
        """Creates a Shared Disk so it can be attached to multiple VMs.

        NOTE: Only ultra disks, premium SSD v2, premium SSD, and standard SSDs can enable shared disks.

        Args:
            resource_group_name (str): Resource group name
            disk_name (str): Disk name
            disk_size_gb (int): Disk size in GB
            disk_iops_read_only (int): Disk IOPS. Some valid values are 500, 2000, 4000, and 6000
            tags (dict[str, str], optional): Tags to be added to the disk. Defaults to {}.
            max_shares (int, optional): Maximum number of nodes that can share a disk. Defaults to 1.
                Certain disk sizes may have a limit for max_shares.
                Check Documentation for more: https://learn.microsoft.com/en-us/azure/virtual-machines/disks-shared-enable?tabs=azure-cli
            location (AZRegion, optional): Location where the disk should be created. Defaults to AZRegion.UK_SOUTH.
            az_zones (list[AZZone], optional): Zone(s) under which the disk should be created. Defaults to [AZZone.ZONE_1].
            os_type (OperatingSystemTypes, optional): OS type of the disk. Defaults to OperatingSystemTypes.LINUX.
            disk_storage_account_type (DiskStorageAccountTypes, optional): Disk type. Defaults to DiskStorageAccountTypes.STANDARD_SSD_LRS.

        Returns:
            Disk: Shared disk object
        """
        zones = [zone.value for zone in az_zones]

        disk_sku = DiskSku(name=disk_storage_account_type)

        disk = Disk(
            location=location.value,
            sku=disk_sku,
            tags=tags,
            zones=zones,
            os_type=os_type,
            disk_size_gb=disk_size_gb,
            disk_iops_read_only=disk_iops_read_only,
            max_shares=max_shares,
            creation_data=CreationData(create_option=DiskCreateOption.EMPTY),  # For creating an empty disk
        )

        logger.info(f"Creating shared disk {disk_name} in location {location.value}, in RG {resource_group_name}")
        disk: Disk = self.compute_client.disks.begin_create_or_update(
            resource_group_name=resource_group_name,
            disk_name=disk_name,
            disk=disk,
        ).result()

        assert disk.provisioning_state == "Succeeded"

        logger.info(f"Disk {disk_name} created successfully")
        return disk

    def delete_disk(self, resource_group_name: str, disk_name: str):
        """Deletes the specified disk

        Args:
            resource_group_name (str): Resource Group name
            disk_name (str): Disk name
        """
        logger.info(f"Deleting disk {disk_name}")
        self.compute_client.disks.begin_delete(
            resource_group_name=resource_group_name,
            disk_name=disk_name,
        ).result()
        logger.info(f"Disk {disk_name} successfully deleted")

    def update_disk(
        self,
        resource_group_name: str,
        disk_name: str,
        disk_size: int = None,
        os_type: OperatingSystemTypes = None,
        disk_sku: DiskStorageAccountTypes = None,
        disk_iops_read_write: int = None,
        disk_m_bps_read_write: int = None,
        disk_iops_read_only: int = None,
        disk_m_bps_read_only: int = None,
        max_shares: int = None,
        network_access_policy: NetworkAccessPolicy = None,
        disk_access_id: str = None,
        tier: str = None,
        bursting_enabled: bool = None,
    ) -> Disk:
        """Update the settings of a Disk

        Args:
            resource_group_name (str): The Resource Group name
            disk_name (str): The Disk name
            disk_size (int, optional): The new Disk Size in GB. Must be larger than the current capacity. Defaults to None.
            os_type (OperatingSystemTypes, optional): The new Operating System type; Windows or Linux. Defaults to None.
            disk_sku (DiskStorageAccountTypes, optional): The new Disk Storage, such as Standard_LRS and Premium_LRS. Defaults to None.
            disk_iops_read_write (int, optional): New IOPS for Read/Write apply only to Premium and Ultra Disk Storage. Defaults to None.
            disk_m_bps_read_write (int, optional): New MBPS for Read/Write apply only to Premium and Ultra Disk Storage. Defaults to None.
            disk_iops_read_only (int, optional): New IOPS for ReadOnly apply only to Premium and Ultra Disk Storage. IOPS across all VMs mounting the shared disk as Read Only. Defaults to None.
            disk_m_bps_read_only (int, optional): New MBPS for ReadOnly apply only to Premium and Ultra Disk Storage. MBPS across all VMs mounting the shared disk as Read Only Defaults to None.
            max_shares (int, optional): The new maximum number of share connections allowed. Values > 1 indicates Disk can be mounted to multiple VMs. Defaults to None.
            network_access_policy (NetworkAccessPolicy, optional): The new Network Access Policy. Defaults to None.
            disk_access_id (str, optional): The ID of a DiskAccess object. Used only if NetworkAccessPolicy is ALLOW_PRIVATE. Defaults to None.
            tier (str, optional): For Premium SSD only, the IOPS and MBPS for Read/Write can be modified (e.g. "E3", "P4"). This setting may only be changed once every 12 hours. Defaults to None.
            bursting_enabled (bool, optional): For Premium SSD only. This setting may only be changed once every 12 hours. Defaults to None.

        Returns:
            Disk: The updated Disk object if successful, None otherwise
        """
        disk = self.get_disk_by_name(resource_group_name=resource_group_name, disk_name=disk_name)

        # The Disk must already exist
        if not disk:
            logger.info(f"Disk must exist: {disk_name}")
            return disk

        logger.info(f"Found Disk: {disk.name}")

        # Build DiskUpdate object
        disk_update = DiskUpdate(
            disk_size_gb=disk_size,
            os_type=os_type,
            sku=DiskSku(name=disk_sku) if disk_sku else None,
            disk_iops_read_write=disk_iops_read_write,
            disk_m_bps_read_write=disk_m_bps_read_write,
            disk_iops_read_only=disk_iops_read_only,
            disk_m_bps_read_only=disk_m_bps_read_only,
            max_shares=max_shares,
            tier=tier,
            bursting_enabled=bursting_enabled,
            network_access_policy=network_access_policy,
            disk_access_id=disk_access_id,
        )

        # call update on the Disk object
        updated_disk: Disk = None

        try:
            updated_disk = self.compute_client.disks.begin_update(
                resource_group_name=resource_group_name,
                disk_name=disk_name,
                disk=disk_update,
            ).result()
            logger.info(f"Disk updated: {updated_disk.name}")
        except HttpResponseError as error:
            logger.info(f"Error in begin_update() call: {error.message}")

        return updated_disk

    def add_tags_to_disk(self, resource_group_name: str, disk_name: str, tags: dict[str, str]):
        """Adds the provided tags to the VM

        Args:
            resource_group_name (str): Resource Group Name
            disk_name (str): Disk Name
            tags (dict[str, str]): Tags
        """
        disk: Disk = self.get_disk_by_name(resource_group_name=resource_group_name, disk_name=disk_name)

        logger.info(f"Appending {tags} to existing Disk tags {disk.tags}")
        disk.tags = {**disk.tags, **tags}

        logger.info(f"Setting tags {tags} to Disk {disk_name}")
        disk: Disk = self.compute_client.disks.begin_create_or_update(
            resource_group_name=resource_group_name,
            disk_name=disk_name,
            disk=disk,
        ).result()

        logger.info(f"Tags for Disk {disk_name} are {disk.tags}")

    def remove_tags_from_disk(self, resource_group_name: str, disk_name: str, tag_keys: list[str]):
        """Adds the provided tags to the Disk

        Args:
            resource_group_name (str): Resource Group Name
            disk_name (str): Disk Name
            tag_keys (list[str]): Tag Keys
        """
        disk: Disk = self.get_disk_by_name(resource_group_name=resource_group_name, disk_name=disk_name)

        for tag_key in tag_keys:
            if tag_key in disk.tags.keys():
                del disk.tags[tag_key]

        logger.info(f"Removing tags {tag_keys} to Disk {disk_name}")
        disk: Disk = self.compute_client.disks.begin_create_or_update(
            resource_group_name=resource_group_name,
            disk_name=disk_name,
            disk=disk,
        ).result()

        logger.info(f"Tags for Disk {disk_name} are {disk.tags}")

    ### Disk Access, used for Disk Private Network Access Policy

    def create_disk_access(
        self, resource_group_name: str, disk_access_name: str, location: AZRegion, tags: dict[str, str] = {}
    ) -> DiskAccess:
        """Create a DiskAccess object

        Args:
            resource_group_name (str): The Resource Group name
            disk_access_name (str): The Disk Access name
            location (AZRegion): The location for the Disk Access
            tags (dict[str, str], optional): Any tags to add to the Disk Access. Defaults to {}.

        Returns:
            DiskAccess: The created DiskAccess object
        """
        disk_access: DiskAccess = None
        disk_access_payload = DiskAccess(location=location.value, tags=tags)

        try:
            disk_access = self.compute_client.disk_accesses.begin_create_or_update(
                resource_group_name=resource_group_name,
                disk_access_name=disk_access_name,
                disk_access=disk_access_payload,
            ).result()
            logger.info(f"Disk Access create: {disk_access.id}")
        except HttpResponseError as error:
            logger.info(f"Error in begin_create_or_update() call: {error.message}")

        return disk_access

    def delete_disk_access(self, resource_group_name: str, disk_access_name: str) -> bool:
        """Delete a DiskAccess object

        Args:
            resource_group_name (str): The Resource Group name
            disk_access_name (str): The Disk Access name

        Returns:
            bool: True if the delete is successful, False otherwise
        """
        try:
            self.compute_client.disk_accesses.begin_delete(
                resource_group_name=resource_group_name, disk_access_name=disk_access_name
            ).result()
            return True
        except HttpResponseError as error:
            logger.info(f"Error in begin_delete() call: {error.message}")
            return False

    def get_disk_access_by_name(self, resource_group_name: str, disk_access_name: str) -> DiskAccess:
        """Get a DiskAccess by name

        Args:
            resource_group_name (str): The Resource Group name
            disk_access_name (str): The Disk Access name

        Returns:
            DiskAccess: The DiskAccess object if found, None otherwise
        """
        disk_access: DiskAccess = None

        try:
            disk_access = self.compute_client.disk_accesses.get(
                resource_group_name=resource_group_name, disk_access_name=disk_access_name
            )
            logger.info(f"Disk Access found: {disk_access.id}")
        except HttpResponseError as error:
            logger.info(f"Error in get() call: {error.message}")

        return disk_access
