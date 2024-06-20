"""
Documentation
https://learn.microsoft.com/en-us/python/api/azure-mgmt-compute/azure.mgmt.compute.v2022_08_01.operations.virtualmachinesoperations?view=azure-python
"""

import logging
import os
import uuid
from typing import Union, List

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (
    VirtualMachine,
    VirtualMachineInstanceView,
    OSDisk,
    GalleryImageVersion,
    DataDisk,
    ManagedDiskParameters,
    DiskCreateOptionTypes,
    OperatingSystemTypes,
    HardwareProfile,
    NetworkProfile,
    OSProfile,
    StorageProfile,
    Image,
    ImageReference,
    VirtualMachineSizeTypes,
    VirtualMachineImageResource,
    NetworkInterfaceReference,
    DeleteOptions,
    DiskDeleteOptionTypes,
    SshPublicKeyResource,
    LinuxConfiguration,
    SshConfiguration,
    SshPublicKeyGenerateKeyPairResult,
    SshPublicKey,
    SecurityProfile,
    SecurityTypes,
    RunCommandInput,
    RunCommandInputParameter,
    RunCommandResult,
)
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkInterfaceIPConfiguration, Subnet, PublicIPAddress, NetworkInterface
from waiting import wait

from lib.common.enums.az_regions import AZRegion, AZZone
from lib.common.enums.az_vm_image import AZVMImage
from lib.common.enums.command_type import AZCommandType
from lib.common.enums.cvsa import CloudProvider, CloudRegions
from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_dataclasses import CloudInstance, CloudDisk, CloudImage, CloudInstanceState
from lib.platform.cloud.cloud_dataclasses import CloudSubnet
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from utils.common_helpers import generate_random_string

logger = logging.getLogger()


def generate_random_password() -> str:
    pwd = generate_random_string(20)
    # Ensure that the password satisfies all Azure rules.
    # 1) Contains an uppercase character
    pwd += "A"
    # 2) Contains a lowercase character
    pwd += "a"
    # 3) Contains a numeric digit
    pwd += "0"
    # 4) Contains a special character
    pwd += "@"
    return pwd


class AZVMManager(CloudVmManager):
    def __init__(
        self,
        credential: Union[DefaultAzureCredential, ClientSecretCredential],
        subscription_id: str,
        resource_group_name: str,
    ) -> None:
        self.compute_client = ComputeManagementClient(credential, subscription_id)
        self.network_client = NetworkManagementClient(credential, subscription_id)
        self.resource_group_name = resource_group_name

    def name(self) -> CloudProvider:
        return CloudProvider.AZURE

    def _get_disk_dataclass(self, data_disk: Union[DataDisk, OSDisk], vm_name: str = None) -> CloudDisk:
        disk = self.compute_client.disks.get(resource_group_name=self.resource_group_name, disk_name=data_disk.name)
        tags = self.get_tags(disk.tags)
        return CloudDisk(
            disk_size_bytes=disk.disk_size_bytes,
            name=disk.name,
            instance_id=vm_name,
            tags=tags,
            state=disk.disk_state,
            device="OSVolume" if isinstance(data_disk, OSDisk) else "DataVolume",
        )

    def _get_image_dataclass(
        self, image: Union[Image, GalleryImageVersion] = None, image_ref: ImageReference = None
    ) -> CloudImage:
        if image:
            image_id = image.id
        elif image_ref:
            image_id = image_ref.id
            image = self.get_image_from_image_reference(image_ref_id=image_id)
        else:
            logging.error("No parameters provided for _get_image_dataclass")
            return CloudImage(id="", name="")
        tags = [Tag(Key=k, Value=v) for k, v in image.tags.items()]
        full_name = next((tag.Value for tag in tags if tag.Key == "FullName"), None)
        return CloudImage(id=image_id, name=full_name, tags=tags)

    def get_image_from_image_reference(self, image_ref_id: str) -> GalleryImageVersion:
        image = next((img for img in self.get_all_images_in_resource_group() if image_ref_id == img.id), None)
        assert image, f"Image with given image ref id is not found: {image_ref_id}"
        return image

    def _get_subnet_dataclass(self, vm: VirtualMachine) -> List[CloudSubnet]:
        interfaces_list = []
        for interface in self.get_vm_net_interfaces(vm):
            interface_id = interface.id.split("/")[-1]
            tags = self.get_tags(self.get_network_interface(interface_id).tags)
            interfaces_list.append(CloudSubnet(id=interface_id, tags=tags))
        return interfaces_list

    def _get_instance_dataclass(self, vm: VirtualMachine) -> CloudInstance:
        data_disks = [
            self._get_disk_dataclass(data_disk=disk, vm_name=vm.name) for disk in vm.storage_profile.data_disks
        ]
        os_disk = self._get_disk_dataclass(data_disk=vm.storage_profile.os_disk, vm_name=vm.name)
        return CloudInstance(
            id=vm.name,
            instance_type=vm.hardware_profile.vm_size,
            location=vm.location,
            data_disks=data_disks,
            os_disk=os_disk,
            state=self.get_vm_state(vm),
            tags=self.get_tags(vm.tags),
            launch_time=vm.time_created,
            image=self._get_image_dataclass(image_ref=vm.storage_profile.image_reference),
            public_ip=self.get_vm_public_ip(vm),
            private_ip=self.get_vm_private_ip(vm),
            subnets=self._get_subnet_dataclass(vm),
            cloud_provider=CloudProvider.AZURE,
        )

    def get_instance(self, vm_name: str) -> CloudInstance:
        vm: VirtualMachine = self.get_vm_by_name(vm_name=vm_name, resource_group_name=self.resource_group_name)
        return self._get_instance_dataclass(vm)

    def list_instances(
        self, states: List[CloudInstanceState] = None, tags: List[Tag] | None = None, location: str = None
    ) -> List[CloudInstance]:
        """list instances by tags, state or location"""
        if tags:
            vms = self.get_all_vms_by_tags(tags=tags)
        else:
            vms = self.get_all_vms_by_resource_group_name(resource_group_name=self.resource_group_name)
        if states:
            vms = [vm for vm in vms if self.get_vm_state(vm) in [state for state in states]]
        if location:
            vms = [vm for vm in vms if vm.location == location]
        instances = [self._get_instance_dataclass(vm) for vm in vms]
        if not instances:
            logging.info("No instances found with given parameters")
            instances = []
        return instances

    def list_images(self) -> List[CloudImage]:
        """Returning all available images in resource_group"""
        images_list = [self._get_image_dataclass(image=image) for image in self.get_all_images_in_resource_group()]
        return images_list

    def get_all_images_in_resource_group(self) -> list[GalleryImageVersion]:
        # TODO: List the gallery names in the Resource Group.
        # gallery_names is currently hardcoded to the cVSA Manager infrastructure.
        gallery_names = ["sig" + self.resource_group_name.replace("-", "")]

        gallery_images = []
        for gallery_name in gallery_names:
            for image in self.compute_client.gallery_images.list_by_gallery(self.resource_group_name, gallery_name):
                for version in self.compute_client.gallery_image_versions.list_by_gallery_image(
                    resource_group_name=self.resource_group_name,
                    gallery_name=gallery_name,
                    gallery_image_name=image.name,
                ):
                    gallery_images.append(version)

        return gallery_images

    def get_disk(self, disk_id: str) -> CloudDisk | None:
        try:
            disk = self.compute_client.disks.get(resource_group_name=self.resource_group_name, disk_name=disk_id)
            return self._get_disk_dataclass(data_disk=disk)
        except ResourceNotFoundError:
            logger.info(f"Volume {disk_id} not found")
            return None

    def start_instance(self, vm_name: str):
        self.power_on_vm(self.resource_group_name, vm_name)

    def stop_instance(self, vm_name: str):
        self.deallocate_vm(self.resource_group_name, vm_name)

    def terminate_instance(self, vm_name: str):
        self.delete_vm(self.resource_group_name, vm_name)

    def create_nic(self, tags: list[Tag], location: CloudRegions) -> NetworkProfile:
        subnet = next(
            self.network_client.subnets.list(self.resource_group_name, virtual_network_name=f"vn-{location.value}")
        )
        ip_config = NetworkInterfaceIPConfiguration(name=f"vn-{location.value}", subnet=Subnet(id=subnet.id))
        tags = {tag.Key: tag.Value for tag in tags}
        nic = self.network_client.network_interfaces.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            parameters=NetworkInterface(location=location.value, tags=tags, ip_configurations=[ip_config]),
            network_interface_name=f"nic-{str(uuid.uuid4())}",
        ).result()
        network_profile = {
            "network_interfaces": [
                {
                    "id": nic.id,
                    "primary": nic.primary,
                    "network_security_group": nic.network_security_group.id if nic.network_security_group else None,
                    "ip_configurations": [
                        {"name": ip_config.name, "private_ip_address": ip_config.private_ip_address}
                        for ip_config in nic.ip_configurations
                    ],
                }
            ]
        }
        return NetworkProfile.from_dict(network_profile)

    def create_instance(
        self,
        image_id: str,
        tags: list[Tag],
        subnet_tag: Tag = None,
        instance_type: str = CloudInstanceDetails.Standard_E2S_v5.value.instance_type,
        location: CloudRegions = None,
    ) -> CloudInstance:
        nic_tags = tags.copy() if tags else []
        if subnet_tag:
            nic_tags.append(subnet_tag)
        vm, password = self.create_vm(
            self.resource_group_name,
            vm_name=f"i-{str(uuid.uuid4())}",
            location=location,
            image_reference=ImageReference(id=image_id),
            network_profile=self.create_nic(nic_tags, location),
            tags={tag.Key: tag.Value for tag in tags},
            vm_size=instance_type,
            security_type=None,
        )
        return self._get_instance_dataclass(vm)

    def wait_cloud_instance_status_ok(self, vm_name: str):
        def _wait_running(_vm_name: str):
            vm_instance_view = self.get_vm_instance_view(resource_group_name=self.resource_group_name, vm_name=_vm_name)
            statuses = [status.display_status for status in vm_instance_view.statuses]
            return "VM running" in statuses

        wait(
            lambda: _wait_running(vm_name),
            timeout_seconds=120,
            sleep_seconds=10,
        )

    def get_vm_state(self, vm: VirtualMachine) -> CloudInstanceState:
        logging.info(f"Checking display status of VM with name: {vm.name}")
        if vm.instance_view is not None:
            instance_view = vm.instance_view
        else:
            _vm = self.get_vm_by_name(vm_name=vm.name, resource_group_name=self.resource_group_name)
            instance_view = _vm.instance_view
        if not instance_view.statuses:
            logging.error(f"VM with name: {vm.name} does not contain status with instance_view: {instance_view}")
            return CloudInstanceState("unknown")
        display_status = instance_view.statuses[1].display_status.removeprefix("VM ")
        logging.info(f"Instance state for vm: {vm.name} is: {display_status}")
        return CloudInstanceState(display_status)

    def get_tags(self, tags: dict) -> list[Tag]:
        if tags:
            tag_objects = [Tag(Key=k, Value=v) for k, v in tags.items()]
        else:
            tag_objects = []
        return tag_objects

    def get_vm_net_interfaces(
        self,
        vm: VirtualMachine,
    ) -> list[NetworkInterfaceReference]:
        return [network_interface for network_interface in vm.network_profile.network_interfaces]

    def get_network_interface(self, nic_id: str, resource_group_name: str = "") -> NetworkInterface | None:
        """Returns NetworkInterface object found by its ID

        Args:
            nic_id (str): NIC ID
            resource_group_name (str, optional): Name of the resource group. Defaults to "".

        Returns:
            NetworkInterface | None: NetworkInterface object if found, else None
        """
        resource_group_name = self.resource_group_name if not resource_group_name else resource_group_name

        try:
            return self.network_client.network_interfaces.get(resource_group_name, nic_id)
        except ResourceNotFoundError:
            logging.error(f"Network interface with {nic_id} does not exists")
            return None

    def get_nic_public_ip_id(self, nic_id: str, resource_group_name: str = "") -> str | None:
        """Get Public IP Address ID by NIC ID

        Args:
            nic_id (str): NIC ID
            resource_group_name (str, optional): Name of the resource group. Defaults to "".

        Returns:
            str | None: PublicIPAddress ID if found, else None
        """
        ip_configurations = self.get_network_interface(nic_id, resource_group_name).ip_configurations
        if ip_configurations is not None:
            public_ip_object: PublicIPAddress = ip_configurations[0].public_ip_address
            if public_ip_object is not None:
                return public_ip_object.id.split("/")[-1]
        else:
            return None

    def get_public_ip_address(self, public_ip_id: str, resource_group_name: str = "") -> PublicIPAddress:
        """Returns PublicIPAddress object found by its public_ip_id

        Args:
            public_ip_id (str): ID of the Public IP Address object
            resource_group_name (str, optional): Name of the resource group. Defaults to "".

        Returns:
            PublicIPAddress: PublicIPAddress object
        """
        resource_group_name = self.resource_group_name if not resource_group_name else resource_group_name
        public_ip_address = self.network_client.public_ip_addresses.get(resource_group_name, public_ip_id)
        return public_ip_address

    def list_all_ip_objects(self, resource_group_name: str = "") -> list[PublicIPAddress]:
        """Lists all IP addresses under a resource group

        Args:
            resource_group_name (str, optional): Name of the resource group. Defaults to "".

        Returns:
            list[PublicIPAddress]: List of PublicIPAddress object
        """
        resource_group_name = self.resource_group_name if not resource_group_name else resource_group_name
        return [ip for ip in self.network_client.public_ip_addresses.list(resource_group_name)]

    def get_vm_public_ip(self, vm: VirtualMachine, resource_group_name: str = "") -> str | None:
        """Returns VM's Public IP Address

        Args:
            vm (VirtualMachine): VirtualMachine object
            resource_group_name (str, optional): Name of the resource group. Defaults to "".

        Returns:
            str | None: VM's Public IP Address if found, else None
        """
        network_interfaces = vm.network_profile.network_interfaces
        if network_interfaces is not None:
            nic_id = network_interfaces[0].id.split("/")[-1]
            public_nic_ip_id: str = self.get_nic_public_ip_id(nic_id, resource_group_name)
            if public_nic_ip_id is not None:
                public_ip: PublicIPAddress = self.get_public_ip_address(
                    public_nic_ip_id,
                    resource_group_name=resource_group_name,
                )
                return public_ip.ip_address
        else:
            return None

    def get_vm_private_ip(self, vm: VirtualMachine, resource_group_name: str = "") -> str:
        """Returns Private IP Address of the VM

        Args:
            vm (VirtualMachine): VirtualMachine object
            resource_group_name (str, optional): Name of the resource group. Defaults to "".

        Returns:
            str: VM's Private IP Address
        """
        nic_id = vm.network_profile.network_interfaces[0].id.split("/")[-1]
        private_ip = self.get_network_interface(nic_id, resource_group_name).ip_configurations[0].private_ip_address
        return private_ip

    def get_all_vms_in_subscription(self) -> list[VirtualMachine]:
        """Fetches all the Virtual Machines in the provided account subscription (top level)

        Returns:
            list[VirtualMachine]: list of Virtual Machines
        """
        all_vms = self.compute_client.virtual_machines.list_all()
        vms: list[VirtualMachine] = [vm for vm in all_vms]
        logger.info(f"VMs retrieved {vms}")
        return vms

    def get_all_vms_by_resource_group_name(self, resource_group_name: str) -> list[VirtualMachine]:
        """Fetches all the Virtual Machines under the provided resource group

        Args:
            resource_group_name (str): Name of the resource group under which the VMs should be found

        Returns:
            list[VirtualMachine]: list of Virtual Machines
        """
        all_vms = self.compute_client.virtual_machines.list(resource_group_name=resource_group_name)
        vms: list[VirtualMachine] = [vm for vm in all_vms]
        logger.info(f"VMs under resource group {resource_group_name} are {vms}")
        return vms

    def get_all_vms_by_location(self, location: AZRegion) -> list[VirtualMachine]:
        """Fetches all the Virtual Machines under the provided location

        Args:
            location (AZRegion): Location (region) of the VM, eastus2, westus, etc.

        Returns:
            list[VirtualMachine]: list of Virtual Machines
        """
        all_vms = self.compute_client.virtual_machines.list_by_location(location=location.value)
        vms: list[VirtualMachine] = [vm for vm in all_vms]
        logger.info(f"VMs under location {location} are {vms}")
        return vms

    def get_all_vms_by_tags(self, tags: list[Tag], resource_group_name: str = "") -> list[VirtualMachine]:
        """Fetches all the Virtual Machines under the provided location
        NOTE: Azure does not have a tag model class.
        It expects a dict[str, str], that's why reusing Tag class from AWS

        Args:
            tags (Tag): Tag of the VMs

        Returns:
            list[VirtualMachine]: list of Virtual Machines
        """
        resource_group_name = self.resource_group_name if not resource_group_name else resource_group_name
        all_vms = self.get_all_vms_by_resource_group_name(resource_group_name=resource_group_name)
        vms: list[VirtualMachine] = []
        for tag in tags:
            [
                vms.append(vm)
                for vm in all_vms
                if vm.tags and tag.Key in vm.tags.keys() and vm.tags.get(tag.Key) == tag.Value
            ]
        logger.info(f"VMs with tag {tags} are {vms}")
        return vms

    def get_all_vms_in_resource_group_by_tag(self, resource_group_name: str, tag: Tag) -> list[VirtualMachine]:
        """Fetches all the Virtual Machines under the provided location
        NOTE: Azure does not have a tag model class.
        It expects a dict[str, str], that's why reusing Tag class from AWS

        Args:
            resource_group_name (str): Resource Group name
            tag (Tag): Tag of the VMs

        Returns:
            list[VirtualMachine]: list of Virtual Machines
        """
        all_vms = self.get_all_vms_by_resource_group_name(resource_group_name=resource_group_name)
        vms: list[VirtualMachine] = [
            vm for vm in all_vms if vm.tags and tag.Key in vm.tags.keys() and vm.tags.get(tag.Key) == tag.Value
        ]
        logger.info(f"VMs with tag {tag} in resource group {resource_group_name} are {vms}")
        return vms

    def get_vm_name_from_vm_id(self, vm_id: str) -> str:
        """Takes VM ID which is typically in format:
        /subscriptions/{subscription_id}/resourceGroups/{rg_name}/providers/Microsoft.Compute/virtualMachines/{vm_name}
        and returns the VM name

        Args:
            vm_id (str): ID of the VM

        Returns:
            str: Name of the VM
        """
        vm_name: str = vm_id.split("/")[-1]
        logger.info(f"VM Name is {vm_name}")
        return vm_name

    def get_vm_by_name(self, resource_group_name: str, vm_name: str, expand: str = "instanceView") -> VirtualMachine:
        """Retrieves information about the model view or the instance view of a virtual machine

        Args:
            resource_group_name (str): Name of the resource group under which the VM should be found
            vm_name (str): name of the VM
            expand (str, optional): The expand expression to apply on the operation.
                                    Known values are "instanceView" and None. Default value is "instanceView".

        Returns:
            VirtualMachine: VirtualMachine object
        """
        vm: VirtualMachine = self.compute_client.virtual_machines.get(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            expand=expand,
        )
        logger.info(f"VM in resource group {resource_group_name}, with name {vm_name} is {vm}")
        return vm

    def get_vm_instance_view(self, resource_group_name: str, vm_name: str) -> VirtualMachineInstanceView:
        """Returns the instance view of a VM which contains more details about VM's running status, etc.

        Args:
            resource_group_name (str): Name of the resource group
            vm_name (str): Name of the VM

        Returns:
            VirtualMachineInstanceView: VirtualMachineInstanceView object
        """
        vm_instance_view: VirtualMachineInstanceView = self.compute_client.virtual_machines.instance_view(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        )
        logger.info(f"VM Instance View in RG {resource_group_name}, with name {vm_name} is {vm_instance_view}")
        return vm_instance_view

    def get_vm_images(
        self,
        location: AZRegion = AZRegion.UK_SOUTH,
        publisher_name: str = "MicrosoftWindowsServer",
        offer: str = "WindowsServer",
        skus: str = "2022-Datacenter",
    ) -> list[VirtualMachineImageResource]:
        """Returns a list of images for the specified arguments

        Args:
            location (AZRegion, optional): Location of the Image. Defaults to AZRegion.UK_SOUTH.
            publisher_name (str, optional): Image Publisher Name. Defaults to "MicrosoftWindowsServer".
            offer (str, optional): Image Offer. Defaults to "WindowsServer".
            skus (str, optional): Image SKUs. Defaults to "2022-Datacenter".

        Returns:
            list[VirtualMachineImageResource]: VirtualMachineImageResource object
        """
        vm_images = self.compute_client.virtual_machine_images.list(
            location=location.value,
            publisher_name=publisher_name,
            offer=offer,
            skus=skus,
        )
        vm_images = [vm_image for vm_image in vm_images]
        logger.info(f"VM images found are {vm_images}")
        return vm_images

    def create_ssh_key(self, resource_group_name: str, key_name: str, location: AZRegion) -> SshPublicKeyResource:
        """Creates an SSH Key

        Args:
            resource_group_name (str): Name of the resource group
            key_name (str): Name of the SSH key
            location (AZRegion): Location of the SSH Key

        Returns:
            SshPublicKeyResource: SshPublicKeyResource
            NOTE: Use generate_ssh_key() function to create a VM and other operations
        """
        ssh_key: SshPublicKeyResource = self.compute_client.ssh_public_keys.create(
            resource_group_name=resource_group_name,
            ssh_public_key_name=key_name,
            parameters=SshPublicKeyResource(location=location.value),
        )

        logger.info(f"Created SSH Key is {ssh_key}")
        return ssh_key

    def generate_ssh_key_pair(
        self,
        resource_group_name: str,
        key_name: str,
        create_key_file: bool = False,
    ) -> SshPublicKeyGenerateKeyPairResult:
        """Creates an SSH Public-Private Key Pair

        Args:
            resource_group_name (str): Name of the resource group
            key_name (str): Name of the SSH key
            create_key_file (bool, optional): Creates a key_name.pem file in the current directory. Defaults to 'False'

        Returns:
            SshPublicKeyGenerateKeyPairResult: SshPublicKeyGenerateKeyPairResult object
            NOTE: Use SshPublicKeyGenerateKeyPairResult.public_key property to create a VM and other operations
        """
        ssh_public_key_pair: SshPublicKeyGenerateKeyPairResult = self.compute_client.ssh_public_keys.generate_key_pair(
            resource_group_name=resource_group_name,
            ssh_public_key_name=key_name,
        )

        logger.info(ssh_public_key_pair.public_key)

        if create_key_file:
            key_pair_file = f"{key_name}.pem"

            if os.path.exists(key_pair_file):
                logger.info(f"Removing {key_pair_file} from drive")
                os.remove(key_pair_file)

            with open(f"{key_name}.pem", "w") as file:
                file.write(ssh_public_key_pair.private_key)

        return ssh_public_key_pair

    def get_ssh_key(self, resource_group_name: str, key_name: str) -> SshPublicKeyResource:
        """Retrieves an SSH Key

        Args:
            resource_group_name (str): Name of the resource group
            key_name (str): Name of the SSH key

        Returns:
            SshPublicKeyResource: SshPublicKeyResource
        """
        ssh_public_key_pair: SshPublicKeyResource = self.compute_client.ssh_public_keys.get(
            resource_group_name=resource_group_name,
            ssh_public_key_name=key_name,
        )

        logger.info(ssh_public_key_pair.public_key)
        return ssh_public_key_pair

    def create_and_generate_key_pair(
        self,
        resource_group_name: str,
        key_name: str,
        location: AZRegion,
        create_key_file: bool = False,
    ) -> SshPublicKeyResource:
        """Creates an SSH Key and Generates Public and Private Key Pair for it

        Args:
            resource_group_name (str): Name of the resource group
            key_name (str): Name of the SSH key
            location (AZRegion): Location of the SSH Key
            create_key_file (bool, optional): Creates a key_name.pem file in the current directory. Defaults to 'False'

        Returns:
            SshPublicKeyResource: SshPublicKeyResource object
        """
        key_present: bool = True
        try:
            self.get_ssh_key(resource_group_name=resource_group_name, key_name=key_name)
        except Exception as e:
            logger.info(f"Key {key_name} was not found. Error {e}")
            key_present = False

        if key_present:
            self.delete_ssh_key(resource_group_name=resource_group_name, key_name=key_name)

        self.create_ssh_key(
            resource_group_name=resource_group_name,
            key_name=key_name,
            location=location,
        )

        ssh_public_key_pair: SshPublicKeyResource = self.generate_ssh_key_pair(
            resource_group_name=resource_group_name,
            key_name=key_name,
            create_key_file=create_key_file,
        )
        logger.info(f"Generated public key = {ssh_public_key_pair.public_key}")

        ssh_key: SshPublicKeyResource = self.get_ssh_key(resource_group_name=resource_group_name, key_name=key_name)
        logger.info(f"Created Key is {ssh_key}")
        return ssh_key

    def delete_ssh_key(
        self,
        resource_group_name: str,
        key_name: str,
    ):
        """Deletes a SSH key

        Args:
            resource_group_name (str): Resource Group Name
            key_name (str): Key Name
        """
        key_present: bool = True
        try:
            self.get_ssh_key(resource_group_name=resource_group_name, key_name=key_name)
        except Exception as e:
            logger.info(f"Key {key_name} was not found. Error {e}")
            key_present = False

        if key_present:
            logger.info(f"Deleting SSH Key {key_name} from RG: {resource_group_name}")
            self.compute_client.ssh_public_keys.delete(
                resource_group_name=resource_group_name,
                ssh_public_key_name=key_name,
            )

    def create_vm(
        self,
        resource_group_name: str,
        vm_name: str,
        location: AZRegion,
        network_interface_id: str = None,
        key_name: str = None,
        az_zones: list[AZZone] = [AZZone.ZONE_1],
        tags: dict[str, str] = {},
        image_reference: ImageReference = AZVMImage.CENT_OS.value,
        vm_size: str = VirtualMachineSizeTypes.STANDARD_B1_S.value,
        username: str = "automation-user",
        password: str = generate_random_password(),
        network_profile: NetworkProfile = None,
        security_type: SecurityTypes | None = SecurityTypes.TRUSTED_LAUNCH,
    ) -> tuple[VirtualMachine, str]:
        """Creates a VM with the provided parameters

        Args:
            resource_group_name (str): Name of the resource group
            vm_name (str): Name of the VM
            Azure resource names cannot contain special characters \\/""[]:|<>+=;,?*@&, whitespace,
            or begin with '_' or end with '.' or '-'
            Linux VM names may only contain letters, numbers, '.', and '-'.
            Windows computer name cannot be more than 15 characters long, be entirely numeric,
            or contain the following characters: ` ~ ! @ # $ % ^ & * ( ) = + _ [ ] { } \ | ; : . ' " , < > / ?.

            location (AZRegion): Region in which VM needs to be created
            network_interface_id (str): NIC ID. Defaults to None
            key_name (str, optional): Name of the SSH Public Key. Defaults to None as it is not required for Windows
            az_zones (list[AZZone], optional): Availability Zone. Defaults to [AZZone.ZONE_1].
            tags (dict[str, str], optional): Tags to assign a VM. Defaults to {}.
            image_reference (AZVMImage, optional): OS Image for VM creation. Defaults to AZVMImage.CENT_OS.
            vm_size (VirtualMachineSizeTypes, optional): VM Size. Defaults to VirtualMachineSizeTypes.STANDARD_B1_S.
            username (str, optional): Username. Defaults to "automation-user".
            Disallowed values: "administrator", "admin", "user", "user1", "test", "user2", "test1", "user3", "admin1",
            "1", "123", "a", "actuser", "adm", "admin2", "aspnet", "backup", "console", "david", "guest", "john",
            "owner", "root", "server", "sql", "support", "support_388945a0", "sys", "test2", "test3", "user4", "user5".
            Minimum-length (Linux): 1 character
            Max-length (Linux): 64 characters
            Max-length (Windows): 20 characters.

            password (str, optional): Password. Defaults to "<random string>".

        Returns:
            VirtualMachine: VirtualMachine object
        """
        # VirtualMachineSizeTypes.STANDARD_B1_S is the cheapest option

        # if "key_name" is optional, check it before running this code.
        # if it is None, then the get_ssh_key() call fails with: "ValueError: No value for given attribute"
        ssh_key: SshPublicKeyResource = None
        if key_name:
            ssh_key = self.get_ssh_key(
                resource_group_name=resource_group_name,
                key_name=key_name,
            )

        hardware_profile = HardwareProfile(vm_size=vm_size)

        if network_interface_id:
            network_profile = NetworkProfile(network_interfaces=[NetworkInterfaceReference(id=network_interface_id)])

            # Deletes NIC after VM is deleted
            for network_interface in network_profile.network_interfaces:
                network_interface.delete_option = DeleteOptions.DELETE

        os_profile = OSProfile(
            computer_name=vm_name,
            admin_username=username,
            admin_password=password,
        )

        # SSH Public Key is only valid for Linux Configuration - only perform if we were given a "key_name"
        if image_reference != AZVMImage.WINDOWS_SERVER.value and ssh_key:
            linux_configuration = LinuxConfiguration(
                ssh=SshConfiguration(
                    public_keys=[
                        SshPublicKey(
                            path=f"/home/{username}/.ssh/authorized_keys",
                            key_data=ssh_key.public_key,
                        )
                    ],
                )
            )
            os_profile.linux_configuration = linux_configuration

        # Setting OS disk options
        os_type: OperatingSystemTypes = (
            OperatingSystemTypes.LINUX
            if image_reference != AZVMImage.WINDOWS_SERVER.value
            else OperatingSystemTypes.WINDOWS
        )

        # This will delete the OS disk on VM termination
        os_disk = OSDisk(
            create_option=DiskCreateOptionTypes.FROM_IMAGE,
            os_type=os_type,
            delete_option=DiskDeleteOptionTypes.DELETE,
        )
        storage_profile = StorageProfile(image_reference=image_reference, os_disk=os_disk)

        # Deletes the attached disk when VM is terminated
        # It will not be useful here because we are not attaching extra disks which is deleted with VM
        # Adding as an example
        if storage_profile.data_disks:
            for data_disk in storage_profile.data_disks:
                data_disk.delete_option = DiskDeleteOptionTypes.DELETE

        # CentOS doesn't support Trusted Launch: https://learn.microsoft.com/en-us/azure/virtual-machines/trusted-launch#operating-systems-supported
        security_type = None if image_reference == AZVMImage.CENT_OS.value else security_type
        security_profile = SecurityProfile(security_type=security_type)

        zones = [zone.value for zone in az_zones]
        virtual_machine = VirtualMachine(
            location=location.value,
            zones=zones,
            tags=tags,
            hardware_profile=hardware_profile,
            network_profile=network_profile,
            os_profile=os_profile,
            storage_profile=storage_profile,
            security_profile=security_profile,
        )

        operation_poller = self.compute_client.virtual_machines.begin_create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            parameters=virtual_machine,
        )

        vm_result = operation_poller.result()
        logger.info(vm_result)
        assert vm_result.provisioning_state == "Succeeded"

        vm = self.get_vm_by_name(resource_group_name=resource_group_name, vm_name=vm_name)
        logger.info(f"Created VM is {vm}")
        return vm, password

    def deallocate_vm(
        self,
        resource_group_name: str,
        vm_name: str,
    ):
        """Deallocates a VM

        Args:
            resource_group_name (str): Name of the Resource Group
            vm_name (str): Name of the VM
        """
        logger.info(f"Deallocation VM {vm_name} and waiting")
        vm_result = self.compute_client.virtual_machines.begin_deallocate(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        ).result()

        logger.info(vm_result)

        vm_instance_view = self.get_vm_instance_view(resource_group_name=resource_group_name, vm_name=vm_name)
        statuses = [status.display_status for status in vm_instance_view.statuses]
        assert "VM deallocated" in statuses
        logger.info(f"VM deallocated {vm_instance_view}")

    def power_off_vm(
        self,
        resource_group_name: str,
        vm_name: str,
    ):
        """Powers Off a VM

        Args:
            resource_group_name (str): Name of the Resource Group
            vm_name (str): Name of the VM
        """
        logger.info(f"Powering Off VM {vm_name} and waiting")
        vm_result = self.compute_client.virtual_machines.begin_power_off(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        ).result()

        logger.info(vm_result)

        vm_instance_view = self.get_vm_instance_view(resource_group_name=resource_group_name, vm_name=vm_name)
        statuses = [status.display_status for status in vm_instance_view.statuses]
        assert "VM stopped" in statuses
        logger.info(f"VM Powered Off {vm_instance_view}")

    def power_on_vm(
        self,
        resource_group_name: str,
        vm_name: str,
    ):
        """Powers On a VM

        Args:
            resource_group_name (str): Name of the Resource Group
            vm_name (str): Name of the VM
        """
        logger.info(f"Powering On VM {vm_name} and waiting")
        vm_result = self.compute_client.virtual_machines.begin_start(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        ).result()

        logger.info(vm_result)

        vm_instance_view = self.get_vm_instance_view(resource_group_name=resource_group_name, vm_name=vm_name)
        statuses = [status.display_status for status in vm_instance_view.statuses]
        assert "VM running" in statuses
        logger.info(f"VM Powered On {vm_instance_view}")

    def restart_vm(
        self,
        resource_group_name: str,
        vm_name: str,
    ):
        """Restarts a VM

        Args:
            resource_group_name (str): Name of the Resource Group
            vm_name (str): Name of the VM
        """
        logger.info(f"Restarting VM {vm_name} and waiting")
        vm_result = self.compute_client.virtual_machines.begin_start(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        ).result()

        logger.info(vm_result)

        vm_instance_view = self.get_vm_instance_view(resource_group_name=resource_group_name, vm_name=vm_name)
        statuses = [status.display_status for status in vm_instance_view.statuses]
        assert "VM running" in statuses
        logger.info(f"VM Restarted {vm_instance_view}")

    def delete_vm(
        self,
        resource_group_name: str,
        vm_name: str,
    ):
        """Deletes a VM

        Args:
            resource_group_name (str): Name of the Resource Group
            vm_name (str): Name of the VM
        """
        logger.info(f"Deleting VM {vm_name} and waiting")
        vm_result = self.compute_client.virtual_machines.begin_delete(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        ).result()

        logger.info(vm_result)
        logger.info(f"VM Delete {vm_name}")

    def generalize_vm(
        self,
        resource_group_name: str,
        vm_name: str,
    ):
        """Generalizes a VM

        Args:
            resource_group_name (str): Name of resource group
            vm_name (str): Name of the VM
        """
        logger.info(f"Generalizing VM {vm_name}")
        vm_result = self.compute_client.virtual_machines.generalize(
            resource_group_name=resource_group_name, vm_name=vm_name
        )
        logger.info(vm_result)

    def add_tags_to_vm(self, resource_group_name: str, vm_name: str, tags: dict[str, str]):
        """Adds the provided tags to the VM

        Args:
            resource_group_name (str): Resource Group Name
            vm_name (str): VM Name
            tags (dict[str, str]): Tags
        """
        vm = self.get_vm_by_name(resource_group_name=resource_group_name, vm_name=vm_name)

        logger.info(f"Appending {tags} to existing VM tags {vm.tags}")
        vm.tags = {**vm.tags, **tags}

        logger.info(f"Setting tags {tags} to VM {vm_name}")
        vm: VirtualMachine = self.compute_client.virtual_machines.begin_create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            parameters=vm,
        ).result()

        logger.info(f"Tags for VM {vm_name} are {vm.tags}")

    def remove_tags_from_vm(self, resource_group_name: str, vm_name: str, tag_keys: list[str]):
        """Adds the provided tags to the VM

        Args:
            resource_group_name (str): Resource Group Name
            vm_name (str): VM Name
            tag_keys (list[str]): Tag Keys
        """
        vm = self.get_vm_by_name(resource_group_name=resource_group_name, vm_name=vm_name)

        for tag_key in tag_keys:
            if tag_key in vm.tags.keys():
                del vm.tags[tag_key]

        logger.info(f"Removing tags {tag_keys} to VM {vm_name}")
        vm: VirtualMachine = self.compute_client.virtual_machines.begin_create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            parameters=vm,
        ).result()

        logger.info(f"Tags for VM {vm_name} are {vm.tags}")

    def attach_disk_to_vm(
        self,
        resource_group_name: str,
        vm_name: str,
        disk_id: str,
        lun: int = 0,
        delete_disk_on_vm_termination: bool = True,
    ) -> VirtualMachine:
        """Attaches the provided disk to the specified VM

        Args:
            resource_group_name (str): Resource Group name
            vm_name (str): VM Name
            disk_id (str): Disk ID. Should be in the following format:
            /subscriptions/{subscription_id}/resourceGroups/{rg_name}/providers/Microsoft.Compute/disks/{disk_name}
            lun (int, optional): Logical Unit Number of the disk. Defaults to 0
            delete_disk_on_vm_termination (bool, optional): Deletes the attached disk on VM termination.
            Defaults to 'True'
            NOTE: It is recommended to set the `delete_disk_on_vm_termination` to `True`
            to save code on cleanup to delete the disk separately

        Returns:
            VirtualMachine : VirtualMachine object
        """
        disk_name = disk_id.split("/")[-1]
        data_disk = DataDisk(
            lun=lun,
            create_option=DiskCreateOptionTypes.ATTACH,
            name=disk_name,
            managed_disk=ManagedDiskParameters(id=disk_id),
        )

        if delete_disk_on_vm_termination:
            data_disk.delete_option = DiskDeleteOptionTypes.DELETE

        logger.info(f"Data Disk parameters {data_disk}")

        vm_parameters: VirtualMachine = self.get_vm_by_name(resource_group_name=resource_group_name, vm_name=vm_name)
        vm_parameters.storage_profile.data_disks.append(data_disk)

        logger.info(f"Detaching disk {disk_name} from VM {vm_name}")
        vm_parameters: VirtualMachine = self.compute_client.virtual_machines.begin_create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            parameters=vm_parameters,
        ).result()

        return vm_parameters

    def detach_disk_from_vm(
        self,
        resource_group_name: str,
        vm_name: str,
        disk_name: str,
    ) -> Union[VirtualMachine, bool]:
        """Detaches the provided disk from the specified VM

        Args:
            resource_group_name (str): Resource Group name
            vm_name (str): VM name
            disk_name (str): Disk name

        Returns:
            Union[VirtualMachine, bool] : VirtualMachine object if the disk is found and detached, else returns False
        """
        vm_parameters: VirtualMachine = self.get_vm_by_name(resource_group_name=resource_group_name, vm_name=vm_name)

        if vm_parameters.storage_profile.data_disks:
            for data_disk in vm_parameters.storage_profile.data_disks:
                if data_disk.name == disk_name:
                    data_disk.to_be_detached = True
                    data_disk.delete_option = DiskDeleteOptionTypes.DETACH
                else:
                    logger.warning(f"Disk {disk_name} not found attached to VM {vm_name}")
                    return False
        else:
            logger.warning(f"Disk {disk_name} not found attached to VM {vm_name}")
            return False

        logger.info(f"Detaching disk {disk_name} from VM {vm_name}")
        vm_parameters: VirtualMachine = self.compute_client.virtual_machines.begin_create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            parameters=vm_parameters,
        ).result()

        return vm_parameters

    def run_command_on_vm(
        self,
        resource_group_name: str,
        vm_name: str,
        script: list[str],
        run_command_input_parameters: list[RunCommandInputParameter] = None,
        command_id: AZCommandType = AZCommandType.SHELL,
        content_type: str = "application/json",
    ) -> RunCommandResult:
        """Runs specified commands using the script parameter on the specified VM

        Args:
            resource_group_name (str): Resource Group name
            vm_name (str): name of the VM
            script (list[str]): List of commands to be run on the VM
            run_command_input_parameters (list[RunCommandInputParameter], optional): Run command parameters.
            Make sure to add parameters to if required for the script to execute
            command_id (AZCommandType, optional): Type of command. Defaults to AZCommandType.SHELL.
            content_type (str, optional): Content-Type. Defaults to "application/json".

        Returns:
            RunCommandResult: output of the command(s)
        """
        run_command_input = RunCommandInput(
            command_id=command_id.value,
            script=script,
            parameters=run_command_input_parameters,
        )

        result: RunCommandResult = self.compute_client.virtual_machines.begin_run_command(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            parameters=run_command_input,
            content_type=content_type,
        ).result()

        return result

    def get_ntp_server_address(self) -> str:
        return "time.windows.com"

    def set_instance_tag(self, instance_id: str, key: str, value: str):
        raise NotImplementedError("set_instance_tag(..) not implemented")
