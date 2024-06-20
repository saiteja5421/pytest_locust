import random
from lib.common.enums.az_regions import AZRegion
from lib.common.enums.az_vm_image import AZVMImage
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import CSPVolumeModel
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import CSPMachineInstanceModel

from lib.dscc.backup_recovery.azure_protection.common.models.asset_set_azure import AssetSetAzure

from lib.platform.azure.azure_factory import Azure
from tests.e2e.aws_protection.context import Context
from tests.e2e.azure_protection.azure_context import AzureContext, AzureSanityContext
from azure.mgmt.compute.models import Disk, VirtualMachine
import logging

from tests.steps.aws_protection.cloud_account_manager_steps import get_csp_account_by_csp_name
from tests.steps.aws_protection.common_steps import (
    azure_write_and_validate_data_dm_core,
    refresh_inventory_with_retry,
)
from tests.steps.aws_protection.inventory_manager_steps import (
    get_csp_instances_by_tag,
    get_csp_volumes_by_tag,
    get_protection_group_by_name_and_validate,
)

logger = logging.getLogger()


def create_az_standard_assets(
    azure_context: AzureContext,
    azure: Azure,
    az_region: AZRegion,
    resource_group_name: str,
    csp_account_name: str,
    asset_set: AssetSetAzure,
    tag_key: str = "standard",
    tag_value: str = "az_sanity_tests",
    key_name: str = "key-sanity-test",
    vm_name: str = "vm-sanity-test",
    username: str = "sanity-test",
    security_group_name: str = "sg-sanity-test",
    public_ip_address_name: str = "public-ip-sanity-test",
    virtual_network_name: str = "vnet-sanity-test",
    subnet_name: str = "subnet-sanity-test",
    network_interface_name: str = "nic-sanity-test",
    vm_disk_name_1: str = "disk-1-sanity-test",
    vm_disk_name_2: str = "disk-2-sanity-test",
    standalone_disk_name_1: str = "standalone-disk-1-sanity-test",
    standalone_disk_name_2: str = "standalone-disk-2-sanity-test",
    write_data: bool = True,
) -> tuple[CSPMachineInstanceModel, list[CSPVolumeModel]]:
    """Creates the following assets in the provided Azure account
    1 X VM with 2 disks attached
    2 X Disks

    Args:
        azure_context (AzureContext): AzureContext object
        azure (Azure): Azure Factory object
        az_region (AZRegion): AZRegion under which resources should be created
        resource_group_name (str): Name of the resource group under which resources should be created
        csp_account_name (str): Name of the CSP account
        asset_set (AssetSetAzure): The AssetSetAzure to populate with created assets.
        tag_key (str, optional): Tag Key to be assigned to the assets. Defaults to "standard".
        tag_value (str, optional):  Tag Value to be assigned to the assets. Defaults to "az_sanity_tests".
        key_name (str, optional): _description_. Defaults to "key-sanity-test".
        vm_name (str, optional): Name of the VM. Defaults to "vm-sanity-test".
        username (str, optional): Username for the VM. Defaults to "sanity-test".
        security_group_name (str, optional): Name for VM Security Group. Defaults to "sg-sanity-test".
        public_ip_address_name (str, optional): Name for VM Public IP. Defaults to "public-ip-sanity-test".
        virtual_network_name (str, optional): Name for VM VNet. Defaults to "vnet-sanity-test".
        subnet_name (str, optional): Name for VM Subnet. Defaults to "subnet-sanity-test".
        network_interface_name (str, optional): Name for VM NIC. Defaults to "nic-sanity-test".
        vm_disk_name_1 (str, optional): Name for VM disk 1. Defaults to "disk-1-sanity-test".
        vm_disk_name_2 (str, optional): Name for VM disk 2. Defaults to "disk-2-sanity-test".
        standalone_disk_name_1 (str, optional): Name for standalone disk 1. Defaults to "standalone-disk-1-sanity-test".
        standalone_disk_name_2 (str, optional): Name for standalone disk 2. Defaults to "standalone-disk-2-sanity-test".
        write_data (bool, optional): Writes data to the VM disks if set to 'True'. Defaults to True.

    Returns:
        tuple[CSPMachineInstanceModel, list[CSPVolumeModel]]: Created assets CSPMachineInstance and a list CSPVolumes
    """
    delete_az_standard_assets(
        azure=azure,
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        key_name=key_name,
        security_group_name=security_group_name,
        vnet_name=virtual_network_name,
        public_ip_address_name=public_ip_address_name,
        standalone_disk_name_1=standalone_disk_name_1,
        standalone_disk_name_2=standalone_disk_name_2,
    )

    vm = create_vm_with_disks(
        azure_context=azure_context,
        azure=azure,
        az_region=az_region,
        resource_group_name=resource_group_name,
        key_name=key_name,
        vm_name=vm_name,
        username=username,
        tag_key=tag_key,
        tag_value=tag_value,
        security_group_name=security_group_name,
        public_ip_address_name=public_ip_address_name,
        virtual_network_name=virtual_network_name,
        subnet_name=subnet_name,
        network_interface_name=network_interface_name,
        vm_disk_name_1=vm_disk_name_1,
        vm_disk_name_2=vm_disk_name_2,
        write_data=write_data,
    )
    logger.info(f"VM created {vm}")

    standalone_disks = create_standalone_disks(
        azure=azure,
        resource_group_name=resource_group_name,
        tag_key=tag_key,
        tag_value=tag_value,
        standalone_disk_name_1=standalone_disk_name_1,
        standalone_disk_name_2=standalone_disk_name_2,
        location=az_region,
    )
    logger.info(f"Standalone disks created {standalone_disks}")

    csp_machine_instances, csp_volumes = get_standard_assets(
        context=azure_context,
        csp_account_name=csp_account_name,
        asset_set=asset_set,
        tag_key=tag_key,
        tag_value=tag_value,
    )

    return csp_machine_instances[0], csp_volumes


def get_standard_assets(
    context: Context,
    csp_account_name: str,
    asset_set: AssetSetAzure,
    tag_key: str = "standard",
    tag_value: str = "az_sanity_tests",
    include_protection_groups: bool = False,
) -> tuple[list[CSPMachineInstanceModel], list[CSPVolumeModel]]:
    """Finds assets by tag and returns them

    Args:
        context (Context): Context object
        csp_account_name (str): CSP Account Name
        asset_set (AssetSetAzure): The AssetSetAzure to populate with discovered assets
        tag_key (str, optional): Key of the Tag. Defaults to 'standard'
        tag_value (str, optional): Value of the tag. Defaults to 'az_sanity_tests'
        include_protection_groups(bool, optional): Retrieves AzureSanity PGs and adds it to the `asset_set`
                                                   Defaults to 'False'

    Returns:
        tuple[list[CSPMachineInstanceModel], list[CSPVolumeModel]]: List of created Instances and Volumes
    """
    logger.info(f"Retrieving CSP Account {csp_account_name}")
    csp_account = get_csp_account_by_csp_name(context=context, account_name=csp_account_name)

    logger.info(f"Refreshing inventory for {csp_account.name}")
    refresh_inventory_with_retry(context=context, account_id=csp_account.id)

    tag = CSPTag(key=tag_key, value=tag_value)
    filter = f"accountInfo/id eq {csp_account.id} and state ne 'DELETED'"

    csp_machine_instances = get_csp_instances_by_tag(context=context, tag=tag, filter=filter)
    assert len(csp_machine_instances) == 1, f"Expected 1 but found {len(csp_machine_instances)} instances"

    # add to AssetSetAzure
    asset_set.virtual_machine_1_id = csp_machine_instances[0].cspId
    asset_set.csp_machine_instance_1_id = csp_machine_instances[0].id

    csp_volumes = get_csp_volumes_by_tag(context=context, tag=tag, filter=filter)

    # If a VM has a tag, Azure propagates it to its attached disks
    csp_volumes = [csp_volume for csp_volume in csp_volumes if len(csp_volume.machineInstanceAttachmentInfo) == 0]
    assert len(csp_volumes) == 2, f"Expected 2 but found {len(csp_volumes)} volumes"

    # add to AssetSetAzure
    asset_set.disk_1_id = csp_volumes[0].cspId
    asset_set.disk_2_id = csp_volumes[1].cspId
    asset_set.csp_volume_1_id = csp_volumes[0].id
    asset_set.csp_volume_2_id = csp_volumes[1].id

    if isinstance(context, AzureSanityContext) and include_protection_groups:
        vm_automatic_pg_name = f"{context.sanity_pg_dynamic_instance}_{context.az_sanity_account_name}"
        logger.info(f"Trying to find PG {vm_automatic_pg_name}")
        vm_automation_protection_group = get_protection_group_by_name_and_validate(
            context=context,
            pg_name=vm_automatic_pg_name,
            validate_pg_found=False,
        )
        if vm_automation_protection_group:
            asset_set.csp_machine_automatic_pg_id = vm_automation_protection_group.id

        volume_automatic_pg_name = f"{context.sanity_pg_dynamic_volume}_{context.az_sanity_account_name}"
        logger.info(f"Trying to find PG {volume_automatic_pg_name}")
        volume_automation_protection_group = get_protection_group_by_name_and_validate(
            context=context,
            pg_name=volume_automatic_pg_name,
            validate_pg_found=False,
        )
        if volume_automation_protection_group:
            asset_set.csp_volume_automatic_pg_id = volume_automation_protection_group.id

        vm_custom_pg_name = f"{context.sanity_pg_custom_instance}_{context.az_sanity_account_name}"
        logger.info(f"Trying to find PG {vm_custom_pg_name}")
        vm_custom_protection_group = get_protection_group_by_name_and_validate(
            context=context,
            pg_name=vm_custom_pg_name,
            validate_pg_found=False,
        )
        if vm_custom_protection_group:
            asset_set.csp_machine_custom_pg_id = vm_custom_protection_group.id

        volume_custom_pg_name = f"{context.sanity_pg_custom_volume}_{context.az_sanity_account_name}"
        logger.info(f"Trying to find PG {volume_custom_pg_name}")
        volume_custom_protection_group = get_protection_group_by_name_and_validate(
            context=context,
            pg_name=volume_custom_pg_name,
            validate_pg_found=False,
        )
        if volume_custom_protection_group:
            asset_set.csp_volume_custom_pg_id = volume_custom_protection_group.id

        volume_tag_mgmt_automatic_pg_name = (
            f"{context.sanity_pg_tag_mgmt_dynamic_volume}_{context.az_sanity_account_name}"
        )
        logger.info(f"Trying to find PG {volume_tag_mgmt_automatic_pg_name}")
        volume_tag_management_protection_group = get_protection_group_by_name_and_validate(
            context=context,
            pg_name=volume_tag_mgmt_automatic_pg_name,
            validate_pg_found=False,
        )
        if volume_custom_protection_group:
            asset_set.csp_tag_management_pg_id = volume_tag_management_protection_group.id

    return csp_machine_instances, csp_volumes


def create_vm_with_disks(
    azure_context: AzureContext,
    azure: Azure,
    az_region: AZRegion,
    resource_group_name: str,
    key_name: str,
    vm_name: str,
    username: str,
    tag_key: str,
    tag_value: str,
    security_group_name: str,
    public_ip_address_name: str,
    virtual_network_name: str,
    subnet_name: str,
    network_interface_name: str,
    vm_disk_name_1: str,
    vm_disk_name_2: str,
    write_data: bool = True,
) -> VirtualMachine:
    """Creates a VM with 2 attached disks and writes data to the disks

    Args:
        azure_context (AzureContext): AzureContext object
        azure (Azure): Azure Factory object
        az_region (AZRegion): Azure Region under which the resources should be created
        resource_group_name (str): Resource Group under which the resources should be created
        key_name (str): Name of the SSH key for VM
        vm_name (str): Name of the VM
        username (str): Username for the VM
        tag_key (str): Tag Key for the assets
        tag_value (str): Tag Value for the assets
        security_group_name (str): Security Group name
        public_ip_address_name (str): Public IP Address name
        virtual_network_name (str): VNet name
        subnet_name (str): Subnet name
        network_interface_name (str): NIC name
        disk_name_1 (str): Disk 1 name
        disk_name_2 (str): Disk 2 name
        write_data (bool, optional): Writes data to the disks using DMCore if set to 'True'. Defaults to True.
    """
    logger.info(f"Creating SSH Key {key_name}")
    ssh_key = azure.az_vm_manager.create_and_generate_key_pair(
        resource_group_name=resource_group_name,
        key_name=key_name,
        location=az_region,
        create_key_file=True,
    )
    logger.info(f"SSH Public Key is {ssh_key.public_key}\n")

    logger.info(f"Creating security group {security_group_name}")
    sg = azure.az_network_manager.create_security_group(
        resource_group_name=resource_group_name,
        security_group_name=security_group_name,
        location=az_region,
    )
    logger.info(f"Security group id: {sg.id}")

    logger.info(f"Creating Public IP {public_ip_address_name}")
    public_ip_address = azure.az_network_manager.create_public_ip(
        resource_group_name=resource_group_name,
        public_ip_address_name=public_ip_address_name,
        location=az_region,
    )

    logger.info(f"Creating VNet {virtual_network_name}")
    vnet = azure.az_network_manager.create_virtual_network(
        resource_group_name=resource_group_name,
        virtual_network_name=virtual_network_name,
        location=az_region,
        subnet_name=subnet_name,
    )
    logger.info(f"VNet is {vnet}\n")
    subnet_id = vnet.subnets[0].id
    logger.info(f"Subnet ID is {subnet_id}\n")

    logger.info(f"Creating NIC {network_interface_name}")
    nic = azure.az_network_manager.create_network_interface(
        resource_group_name=resource_group_name,
        location=az_region,
        network_interface_name=network_interface_name,
        subnet_id=subnet_id,
        security_group_id=sg.id,
        public_ip_address=public_ip_address,
    )

    logger.info(f"NIC is {nic}\n")

    vm_linux_images = [image for image in list(AZVMImage) if image.name != "WINDOWS_SERVER"]
    vm_image = random.choice(vm_linux_images)
    logger.info(f"VM image is {vm_image}")

    logger.info(f"Creating VM {vm_name}")
    vm, _ = azure.az_vm_manager.create_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        username=username,
        location=az_region,
        image_reference=vm_image.value,
        network_interface_id=nic.id,
        key_name=ssh_key.name,
        tags={tag_key: tag_value},
    )
    logger.info(f"Created VM {vm}\n")

    logger.info(f"Creating disk 1: {vm_disk_name_1}")
    disk_1 = azure.az_disk_manager.create_disk(
        resource_group_name=resource_group_name,
        location=az_region,
        disk_name=vm_disk_name_1,
        disk_size_gb=10,
        disk_iops_read_only=500,
    )
    # TODO: wait for disk to be created
    logger.info(f"Attaching disk 1: {vm_disk_name_1} to VM '{vm_name}'\n")
    azure.az_vm_manager.attach_disk_to_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        disk_id=disk_1.id,
        lun=0,
    )

    logger.info(f"Creating disk 2: {vm_disk_name_2}")
    disk_2 = azure.az_disk_manager.create_disk(
        resource_group_name=resource_group_name,
        location=az_region,
        disk_name=vm_disk_name_2,
        disk_size_gb=10,
        disk_iops_read_only=500,
    )

    # TODO: wait for disk to be created
    logger.info(f"Attaching disk 2: {vm_disk_name_2} to VM '{vm_name}'\n")
    azure.az_vm_manager.attach_disk_to_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        disk_id=disk_2.id,
        lun=1,
    )

    if write_data:
        logger.info(f"Writing data using dmcore on VM {vm_name}")
        azure_write_and_validate_data_dm_core(
            context=azure_context,
            azure=azure,
            vm_name=vm_name,
            username=username,
            resource_group_name=resource_group_name,
            key_file=ssh_key.name,
            validation=False,
        )

    return vm


def create_standalone_disks(
    azure: Azure,
    resource_group_name: str,
    tag_key: str,
    tag_value: str,
    standalone_disk_name_1: str,
    standalone_disk_name_2: str,
    location: AZRegion = AZRegion.UK_SOUTH,
) -> list[Disk]:
    """Creates and returns 2 standalone disks

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Name of the Resource Group
        tag_key (str): Tag Key for the disks
        tag_value (str): Tag Values for the disks
        standalone_disk_name_1 (str): Name for disk 1
        standalone_disk_name_2 (str): Name for disk 2
        location (AZRegion): AZRegion under which resources should be created

    Returns:
        list[Disk]: List of created disks
    """
    logger.info(f"Creating standalone_disk_1: {standalone_disk_name_1}")
    standalone_disk_1 = azure.az_disk_manager.create_disk(
        resource_group_name=resource_group_name,
        disk_name=standalone_disk_name_1,
        disk_size_gb=10,
        disk_iops_read_only=500,
        tags={tag_key: tag_value},
        location=location,
    )
    logger.info(f"Created standalone_disk_1 {standalone_disk_1}")

    logger.info(f"Creating standalone_disk_2: {standalone_disk_name_2}")
    standalone_disk_2 = azure.az_disk_manager.create_disk(
        resource_group_name=resource_group_name,
        disk_name=standalone_disk_name_2,
        disk_size_gb=10,
        disk_iops_read_only=500,
        tags={tag_key: tag_value},
        location=location,
    )
    logger.info(f"Created standalone_disk_2 {standalone_disk_2}")

    return [standalone_disk_1, standalone_disk_2]


def delete_az_standard_assets(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
    key_name: str,
    security_group_name: str,
    vnet_name: str,
    public_ip_address_name: str,
    standalone_disk_name_1: str,
    standalone_disk_name_2: str,
):
    """Deletes all the created standard assets

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Name of the resource group
        vm_name (str): VM Name
        key_name (str): VM Key Name
        security_group_name (str): VM's security group name
        vnet_name (str): VM's VNet name
        public_ip_address_name (str): VM's public IP address name
        standalone_disk_name_1 (str): Standalone Disk 1 name
        standalone_disk_name_2 (str): Standalone Disk 2 name
    """
    logger.info(f"Deleting VM {vm_name}\n")
    vms = azure.az_vm_manager.get_all_vms_by_resource_group_name(resource_group_name=resource_group_name)
    vm = [vm for vm in vms if vm.name == vm_name]

    if vm:
        azure.az_vm_manager.delete_vm(resource_group_name=resource_group_name, vm_name=vm_name)

    logger.info(f"Deleting SSH Key {key_name}\n")
    azure.az_vm_manager.delete_ssh_key(resource_group_name=resource_group_name, key_name=key_name)

    logger.info(f"Deleting SG {security_group_name}\n")
    sgs = azure.az_network_manager.get_all_security_groups(resource_group_name=resource_group_name)
    security_group = [security_group for security_group in sgs if security_group.name == security_group_name]

    if security_group:
        azure.az_network_manager.delete_security_group(
            resource_group_name=resource_group_name,
            security_group_name=security_group_name,
        )

    logger.info(f"Deleting VNet {vnet_name}\n")
    vnets = azure.az_network_manager.get_all_virtual_networks(resource_group_name=resource_group_name)
    vnet = [vnet for vnet in vnets if vnet.name == vnet_name]

    if vnet:
        azure.az_network_manager.delete_virtual_network(
            resource_group_name=resource_group_name,
            virtual_network_name=vnet_name,
        )

    logger.info(f"Deleting Public IP Address {public_ip_address_name}")
    public_ips = azure.az_network_manager.get_all_public_ips(resource_group_name=resource_group_name)
    public_ip = [public_ip for public_ip in public_ips if public_ip.name == public_ip_address_name]

    if public_ip:
        azure.az_network_manager.delete_public_ip_address(
            resource_group_name=resource_group_name,
            public_ip_address_name=public_ip_address_name,
        )

    logger.info("Deleting standalone disks")
    standalone_disks = azure.az_disk_manager.get_all_disks_by_resource_group_name(
        resource_group_name=resource_group_name,
    )

    standalone_disk_1 = [disk for disk in standalone_disks if disk.name == standalone_disk_name_1]
    if standalone_disk_1:
        logger.info(f"Deleting standalone disk {standalone_disk_name_1}")
        azure.az_disk_manager.delete_disk(
            resource_group_name=resource_group_name,
            disk_name=standalone_disk_1,
        )

    standalone_disk_2 = [disk for disk in standalone_disks if disk.name == standalone_disk_name_2]
    if standalone_disk_2:
        logger.info(f"Deleting standalone disk {standalone_disk_name_1}")
        azure.az_disk_manager.delete_disk(
            resource_group_name=resource_group_name,
            disk_name=standalone_disk_2,
        )
