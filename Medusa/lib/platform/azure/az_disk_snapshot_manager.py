import logging
from typing import Union

from lib.common.enums.az_regions import AZRegion
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (
    OperatingSystemTypes,
    HyperVGeneration,
    CreationData,
    NetworkAccessPolicy,
    Disk,
    DiskCreateOption,
)
from azure.mgmt.compute.v2020_09_30.models._models_py3 import Snapshot

logger = logging.getLogger()


class AZDiskSnapshotManager:
    def __init__(
        self,
        credential: Union[DefaultAzureCredential, ClientSecretCredential],
        subscription_id: str,
    ) -> None:
        self.compute_client = ComputeManagementClient(credential, subscription_id)

    def create_vm_disk_snapshot(
        self,
        vm_disk: Disk,
        resource_group_name: str,
        snapshot_name: str,
        location: AZRegion,
        os_type: OperatingSystemTypes,
        disk_size_gb: int,
        hyper_v_generation: HyperVGeneration = HyperVGeneration.V2,
        create_option: DiskCreateOption = DiskCreateOption.COPY,
        network_access_policy: NetworkAccessPolicy = NetworkAccessPolicy.ALLOW_ALL,
        tags: dict[str, str] = {},
    ) -> Snapshot:
        """Create VM Disk Snapshot

        Args:
            vm_disk (Disk): Targeted VM Disk object
            resource_group_name (str): Name of Resource Group
            snapshot_name (str): Name of Snapshot
            location (AZRegion): Location of VM Disk
            os_type (OperatingSystemTypes): OS type
            disk_size_gb (int): VM Disk Size
            hyper_v_generation (HyperVGeneration, optional): Hypervisor generation of VM applicable to OS disks. Defaults to HyperVGeneration.V2.
            create_option (DiskCreateOption, optional): Enumerates possible sources of a disk's creation. Defaults to DiskCreateOption.COPY.
            network_access_policy (NetworkAccessPolicy, optional): Policy for accessing the disk via network. Defaults to NetworkAccessPolicy.ALLOW_ALL.
            tags (dict[str, str], optional): Tags for VM Disk Snapshot. Defaults to {}.

        Returns:
            snapshot (Snapshot): Newly created/updated VM Disk Snapshot
        """
        creation_data = CreationData(create_option=create_option, source_resource_id=vm_disk.id)
        snapshot = Snapshot(
            location=location.value,
            tags=tags,
            os_type=os_type,
            hyper_v_generation=hyper_v_generation,
            creation_data=creation_data,
            disk_size_gb=disk_size_gb,
            network_access_policy=network_access_policy,
        )
        snapshot: Snapshot = self.compute_client.snapshots.begin_create_or_update(
            resource_group_name=resource_group_name, snapshot_name=snapshot_name, snapshot=snapshot
        ).result()
        logger.info(f"Created VM Disk Snapshot {snapshot_name} ({snapshot.id})")
        return snapshot

    def delete_vm_disk_snapshot(self, resource_group_name: str, snapshot_name: str) -> None:
        """Delete VM Disk Snapshot

        Args:
            resource_group_name (str): Name of Resource Group
            snapshot_name (str): Name of Snapshot
        """
        self.compute_client.snapshots.begin_delete(
            resource_group_name=resource_group_name, snapshot_name=snapshot_name
        ).result()
        logger.info(f"Deleted VM Disk Snapshot {snapshot_name}")

    def get_vm_disk_snapshot(self, resource_group_name: str, snapshot_name: str) -> Snapshot:
        """Get VM Disk Snapshot
        Args:
            resource_group_name (str): Name of Resource Group
            snapshot_name (str): Name of Snapshot
        Returns:
            snapshot (Snapshot): Snapshot object obtained
        """
        snapshot = self.compute_client.snapshots.get(
            resource_group_name=resource_group_name, snapshot_name=snapshot_name
        )
        print(f"Obtained Snapshot {snapshot.id}")
        return snapshot

    def add_tags_to_vm_disk_snapshot(
        self,
        resource_group_name: str,
        snapshot_name: str,
        tags: dict[str, str],
    ) -> Snapshot:
        """Add Tags to VM Disk Snapshot

        Args:
            resource_group_name (str): Name for Resource Group
            snapshot_name (str): Name of Snapshot
            tags (dict[str, str]): Tags to add to Snapshot

        Returns:
            updated_snapshot (Snapshot): Updated Snapshot object
        """
        snapshot: Snapshot = self.get_vm_disk_snapshot(
            resource_group_name=resource_group_name, snapshot_name=snapshot_name
        )
        logger.info(f"Appending {tags} to existing Snapshot Tags {snapshot.tags}")
        snapshot.tags = {**snapshot.tags, **tags}

        logger.info(f"Setting tags {tags} to Snapshot {snapshot_name}")
        updated_snapshot: Snapshot = self.compute_client.snapshots.begin_update(
            resource_group_name=resource_group_name, snapshot_name=snapshot_name, snapshot=snapshot
        ).result()
        logger.info(f"Updated Snapshot {snapshot_name} to have the following tags {updated_snapshot.tags}")
        return updated_snapshot

    def remove_tags_from_vm_disk_snapshot(
        self, resource_group_name: str, snapshot_name: str, tag_keys: list[str]
    ) -> Snapshot:
        """Remove Tags from VM Disk Snapshot

        Args:
            resource_group_name (str): Name of Resource Group
            snapshot_name (str): Name of Snapshot
            tag_keys (list[str]): List of Tag Keys to remove from Snapshot

        Returns:
            updated_snapshot (Snapshot): Updated Snapshot object
        """
        snapshot: Snapshot = self.get_vm_disk_snapshot(
            resource_group_name=resource_group_name, snapshot_name=snapshot_name
        )
        for tag_key in tag_keys:
            if tag_key in snapshot.tags.keys():
                del snapshot.tags[tag_key]

        logger.info(f"Removing tags {tag_keys} from VM Disk Snapshot {snapshot_name}")
        updated_snapshot: Snapshot = self.compute_client.snapshots.begin_update(
            resource_group_name=resource_group_name, snapshot_name=snapshot_name, snapshot=snapshot
        ).result()
        logger.info(f"Updated Snapshot {snapshot_name} to now have the following tags {updated_snapshot.tags}")
        return updated_snapshot
