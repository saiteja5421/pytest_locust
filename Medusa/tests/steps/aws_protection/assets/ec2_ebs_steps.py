"""
This module contains functions related to AWS API operations for EC2 Instances and EBS Volumes
"""
import logging
import random
import string
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Any, Union

from lib.common.enums.aws_availability_zone import AWSAvailabilityZone
from lib.common.enums.ebs_volume_type import EBSVolumeType

from lib.dscc.backup_recovery.aws_protection.common.models.asset_set_dto import AwsAssetsDto

from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.address import Address
from lib.platform.aws_boto3.models.instance import Instance, Tag

from tests.e2e.aws_protection.context import Context

import tests.steps.aws_protection.inventory_manager_steps as InvMgrSteps

logger = logging.getLogger()


def ec2_detach_multiple_ebs(aws: AWS, ec2_instance: Instance, ebs_count: int = 1) -> int:
    """ec2_detach_multiple_ebs method will detach and delete ebs volume(s) from ec2_instance as per ebs_count

    Args:
        aws (AWS): AWS object
        ec2_instance (Instance): EC2 instance from which EBS are to be detached
        ebs_count (int, optional): EBS volume count to be detached from the EC2 instance. Defaults to 1.

    Raises:
        ValueError: Error raised if ebs_count is greater than then number of attached volumes on ec2_instance

    Returns:
        int: Number of volumes removed from ec2_instance.
    """
    attached_volumes = aws.ebs.get_volumes_attached_to_instances([ec2_instance.id])
    # Getting list of volumes from volume collection object
    attached_volumes = [volume for volume in attached_volumes]
    if len(attached_volumes) < ebs_count:
        raise ValueError(
            f"EC2 instance has only {len(attached_volumes)} volumes, can't remove {ebs_count} volumes from it"
        )
    count = 0
    for volume in attached_volumes:
        device_name = aws.ebs.get_ec2_instance_attached_volume_device_name(volume.id, ec2_instance.id)
        # Don't detach & delete root volume
        # it will be automatically deleted while terminating EC2 instance
        if ec2_instance.root_device_name != device_name:
            aws.ebs.detach_volume_from_instance(volume_id=volume.id, device=device_name, instance_id=ec2_instance.id)
            aws.ebs.delete_volume(volume_id=volume.id)
            count += 1
            if count == ebs_count:
                return count


def cleanup_ebs_volumes_by_id(aws: AWS, ebs_volume_ids: list[str]):
    """Cleanup AWS EBS Volumes by ID.

    Args:
        aws (AWS): AWS Account
        ebs_volume_ids (list[str]): A list of AWS EBS Volume IDs
    """
    for volume_id in ebs_volume_ids:
        aws.ebs.delete_volume(volume_id=volume_id)


def cleanup_ec2_instances_by_id(
    aws: AWS, ec2_instance_ids: list[str], terminate: bool = True, delete_attached_volumes: bool = False
):
    """Cleanup AWS EC2 Instances by ID.

    Args:
        aws (AWS): AWS account
        ec2_instance_ids (list[str]): A list of AWS EC2 Instance IDs
        terminate (bool, optional): If True, EC2 Instances will be terminated after they are stopped. Defaults to True.
        delete_attached_volumes (bool, optional): If True, attached EBS Volumes will be deleted. Defaults to False.
    """
    ec2_instances = []
    for instance_id in ec2_instance_ids:
        ec2_instances.append(aws.ec2.get_ec2_instance_by_id(ec2_instance_id=instance_id))

    if delete_attached_volumes:
        delete_attached_volumes_from_instances(aws=aws, ec2_instances=ec2_instances)

    # always stop instances, terminate if instructed
    aws.ec2.stop_ec2_instances(ec2_instances)

    if terminate:
        aws.ec2.terminate_ec2_instances(ec2_instances)


def delete_attached_volumes_from_instances(aws: AWS, ec2_instances: list):
    """Delete all attached non-root volumes from EC2 Instances

    Args:
        aws (AWS): AWS account
        ec2_instances (list): A list of AWS EC2 Instance objects
    """
    for ec2_instance in ec2_instances:
        attached_volumes = aws.ebs.get_volumes_attached_to_instances([ec2_instance.id])
        for volume in attached_volumes:
            device_name = aws.ebs.get_ec2_instance_attached_volume_device_name(volume.id, ec2_instance.id)
            # Don't detach & delete root volume
            # it will be automatically deleted while terminating EC2 instance
            if ec2_instance.root_device_name != device_name:
                detach_and_delete_volume(
                    aws,
                    volume_id=volume.id,
                    device=device_name,
                    instance_id=ec2_instance.id,
                    force=True,
                )


def create_ec2_instances_with_custom_config(
    aws: AWS,
    key_name: str,
    image_id: str,
    ec2_count: int,
    ec2_instance_name_prefix: str,
    subnet_id: str,
    security_groups: list[str],
    availability_zone: str = "",
    volume_count: int = 1,
    volume_size: int = 50,
    volume_type: list[str] = [EBSVolumeType.GP2.value],
    random_flag: bool = False,
    tags: list[Tag] = [],
    create_ebs_and_attach: bool = True,
) -> tuple[list, list]:
    """Create a number of EC2 Instances

    Args:
        aws (AWS): The AWS Account object
        key_name (str): The Key Pair name for the EC2 Instances
        image_id (str): The AWS AMI to use for the EC2
        ec2_count (int): The number of EC2 Instances desired
        ec2_instance_name_prefix (str): A string prefix for the EC2 Name Tag
        subnet_id (str): The Subnet ID to use for the EC2 Instances
        security_groups (list[str]): A list of Security Groups to which to add the EC2 Instances
        availability_zone (str, optional): The desired Availability Zone. Defaults to "".
        volume_count (int, optional): The number of EBS Volumes to create for each EC2 Instance. Defaults to 1.
        volume_size (int, optional): The desired size of the EBS Volumes. Defaults to 50.
        volume_type (list[str], optional): A list of EBS Volume types from which to choose. Defaults to [EBSVolumeType.GP2.value].
        random_flag (bool, optional): If True, a random "volume_type" will be used to create EBS Volumes. Defaults to False.
        tags (list[Tag], optional): A list of Tag values to add to the EC2 and EBS objects. Defaults to [].
        create_ebs_and_attach (bool, optional): If False, no EBS Volumes will be created or attached. Defaults to True.

    Returns:
        tuple[list, list]: A list of AWS EC2 Instances and a list of AWS EBS Volumes
    """
    ec2_instances = aws.ec2.create_custom_config_ec2_instances(
        key_name=key_name,
        image_id=image_id,
        availability_zone=availability_zone,
        subnet_id=subnet_id,
        tags=tags,
        security_groups=security_groups,
        max_count=ec2_count,
    )

    ec2_instance_list = []
    for ec2_instance in ec2_instances:
        ec2_instance_name = ec2_instance_name_prefix + "_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        new_tags = [Tag(Key="Name", Value=ec2_instance_name), *tags]
        aws.ec2.create_tags_for_ec2_instance(ec2_instance=ec2_instance, tags_list=new_tags)

        if not availability_zone:
            availability_zone = ec2_instance.placement["AvailabilityZone"]

        # TODO: This function will only return the last batch of "volumes" created, since the "volumes" variable is overwritten for each EC2 Instance.
        # NOTE: Currently, all callers of this function pass in "ec2_count" as 1, so no issue has yet been encountered.
        volumes = []
        if create_ebs_and_attach:
            volumes = create_ebs_volumes(
                aws=aws,
                availability_zone=availability_zone,
                volume_count=volume_count,
                volume_size=volume_size,
                volume_type_list=volume_type,
                random_flag=random_flag,
                tags=tags,
            )
            attach_volumes_to_ec2_instance(aws=aws, ec2_instance_id=ec2_instance.id, volumes=volumes)

        ec2_instance_object = aws.ec2.get_ec2_instance_by_id(ec2_instance.id)
        ec2_instance_list.append(ec2_instance_object)

    return ec2_instance_list, volumes


def create_ebs_volumes_with_custom_config(
    aws: AWS,
    availability_zone: str,
    ebs_volume_name_prefix: str,
    volume_count: int,
    volume_size: int,
    volume_type: list[str],
    random_flag: bool = False,
    tags: list[Tag] = [],
) -> list:
    """Create a number of EBS Volumes with the provided "ebs_volume_name_prefix"

    Args:
        aws (AWS): The AWS Account object
        availability_zone (str): The desired Availability Zone
        ebs_volume_name_prefix (str): A string prefix for the EBS Name Tag
        volume_count (int): The number of EBS Volumes to create
        volume_size (int): The desired size of the EBS Volumes
        volume_type (list[str]): A list of EBS Volume types from which to choose
        random_flag (bool, optional): If True, a random "volume_type" will be used to create EBS Volumes. Defaults to False.
        tags (list[Tag], optional): A list of Tag values to add to the EC2 and EBS objects. Defaults to [].

    Returns:
        list: A list of AWS EBS Volume objects
    """
    volumes = create_ebs_volumes(
        aws=aws,
        availability_zone=availability_zone,
        volume_count=volume_count,
        volume_size=volume_size,
        volume_type_list=volume_type,
        random_flag=random_flag,
        tags=tags,
    )
    ebs_volumes_list = []
    for volume in volumes:
        volume = aws.ebs.get_ebs_volume_by_id(volume_id=volume.id)
        ebs_volume_name = ebs_volume_name_prefix + "_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        tags_vol = [Tag(Key="Name", Value=ebs_volume_name), *tags]
        aws.ebs.create_ebs_volume_tags(volume, tags_vol)
        ebs_volumes_list.append(volume)
    return ebs_volumes_list


def create_ebs_volumes(
    aws: AWS,
    availability_zone: str,
    volume_count: int,
    volume_size: int,
    volume_type_list: list[str],
    random_flag: bool = False,
    tags: list[Tag] = [],
) -> list:
    """Create a number of EBS Volumes

    Args:
        aws (AWS): The AWS Account object
        availability_zone (str): The desired Availability Zone
        volume_count (int): The desired number of EBS Volumes to create
        volume_size (int): The desired size of the EBS Volumes
        volume_type_list (list[str]): A list of EBS Volume types from which to choose
        random_flag (bool, optional): If True, a random "volume_type" will be used to create EBS Volumes. Defaults to False.
        tags (list[Tag], optional): A list of Tag values to add to the EC2 and EBS objects. Defaults to [].

    Returns:
        list: A list of AWS EBS Volume objects
    """
    volumes = []
    for index in range(volume_count):
        if random_flag:
            # choose random volume type from the volume type list
            volume_type = random.choice(volume_type_list)
        else:
            # take volume type from the volume type list in the order for each ebs volume
            # For ex: take first volume type from the list for the first volume
            # In this case, number of volume types in the list should be match with num of volumes created
            volume_type = volume_type_list[index]
        ebs_volume = aws.ebs.create_ebs_volume(
            availability_zone=availability_zone,
            size=volume_size,
            volume_type=volume_type,
            tags=tags,
        )
        volumes.append(ebs_volume)
    return volumes


def attach_volumes_to_ec2_instance(aws: AWS, ec2_instance_id: str, volumes: list):
    """Attach the provided list of EBS Volumes to the EC2 Instance

    Args:
        aws (AWS): The AWS Account object
        ec2_instance_id (str): The EC2 Instance ID to which to attach the list of Volumes
        volumes (list): The list of AWS EBS Volumes to attach to the EC2 Instance
    """
    for volume in volumes:
        ec2_instance = aws.ec2.get_ec2_instance_by_id(ec2_instance_id)
        device = get_free_device_name(ec2_instance)
        aws.ebs.attach_volume_to_ec2_instance(volume.id, device, ec2_instance_id)


# From "ec2-api.pdf": https://docs.aws.amazon.com/AWSEC2/latest/APIReference
# Volume.attachmentSet        : Information about the volume attachments.
#   Type: Array of VolumeAttachment objects
# VolumeAttachment.instanceId : The ID of the instance. Type: String
# VolumeAttachment.device     : The device name.        Type: String
# VolumeAttachment.volumeId   : The ID of the volume.   Type: String
def detach_and_delete_ebs_volumes(aws: AWS, ebs_volume_ids: list[str]):
    """Detach and Delete EBS Volumes from AWS

    Args:
        aws (AWS): The AWS Account object
        ebs_volume_ids (list[str]): A list of AWS EBS Volume IDs
    """
    for volume_id in ebs_volume_ids:
        ebs_volume = aws.ebs.get_ebs_volume_by_id(volume_id=volume_id)

        for volume_attachment in ebs_volume.attachments:
            aws.ebs.detach_volume_from_instance(
                volume_id=volume_attachment["VolumeId"],
                device=volume_attachment["Device"],
                instance_id=volume_attachment["InstanceId"],
            )
        aws.ebs.delete_volume(volume_id=volume_id)


def get_free_device_name(instance: Instance) -> str:
    """Get the next available device name from the EC2 Instance

    Args:
        instance (Instance): An AWS EC2 Instance object

    Returns:
        str: The next available device name from the AWS EC2 Instance
    """
    all_device_names = ["/dev/xvd%s" % (x) for x in string.ascii_lowercase]
    device_list = instance.block_device_mappings
    used_device_names = set()
    for device in device_list:
        used_device_names.add(device["DeviceName"])
    return random.choice(list(set(all_device_names) - used_device_names))


def create_aws_assets_for_account(
    aws: AWS,
    availability_zone: AWSAvailabilityZone,
    ami_image_id: str,
    num_ec2: int,
    num_ebs: int,
    num_vpc: int,
    num_subnet: int,
    key_name: str,
) -> AwsAssetsDto:
    """Create AWS assets in the given AWS Account and return in AwsAssetsDto object.

    Args:
        aws (AWS): The AWS Account in which to create assets
        availability_zone (AWSAvailabilityZone): The AWS Availability Zone to use
        ami_image_id: The AMI Image to use
        num_ec2 (int): Number of EC2 Instances desired
        num_ebs (int): Number of EBS Volumes desired
        num_vpc (int): Number of VPCs desired
        num_subnet (int): Number of Subnets desired
        key_name (str): The key_name to use for EC2 Instances

    Returns:
        AwsAssetsDto: Object contains lists of all AWS assets created
    """

    # EC2 key pair
    aws.ec2.create_ec2_key_pair(key_name=key_name)

    # EC2 instances
    ec2_instances = aws.ec2.create_ec2_instance(
        key_name=key_name,
        image_id=ami_image_id,
        availability_zone=availability_zone.value,
        min_count=num_ec2,
        max_count=num_ec2,
    )
    assert len(ec2_instances) == num_ec2, f"Failed to create the required number of EC2 Instances {num_ec2}"

    # EBS volumes
    ebs_volumes = []

    for index in range(num_ebs):
        ebs_volume = aws.ebs.create_ebs_volume(
            availability_zone=availability_zone.value, volume_type=EBSVolumeType.GP2.value, size=100
        )
        assert ebs_volume is not None, f"Failed to create EBS Volume {index} of {num_ebs}"
        ebs_volumes.append(ebs_volume)

    # VPC
    vpcs = list(aws.vpc.get_all_vpcs())
    vpc_present_count = len(vpcs)

    # Have 5 VPCs max in the region, using any present VPCs
    for index in range(num_vpc - vpc_present_count):
        vpc = aws.vpc.create_vpc(cidr_block="10.0.0.0/16")
        assert vpc is not None, f"Failed to create VPC {index} of {num_vpc}"
        vpcs.append(vpc)

    # Subnet
    # - attach to first VPC created
    vpc = [vpc for vpc in vpcs if not vpc.is_default][0]
    vpc_id = vpc.id
    vpc_range = ".".join(vpc.cidr_block.split(".")[0:2])
    subnets = aws.subnet.get_all_subnets()
    subnets = [
        subnet for subnet in subnets if subnet.vpc_id == vpc_id and subnet.availability_zone == availability_zone.value
    ]
    subnets_count = len(subnets)

    for index in range(num_subnet - subnets_count):
        cidr_block = f"{vpc_range}.{str(index)}.0/24"
        try:
            subnet = aws.subnet.create_subnet(
                availability_zone=availability_zone.value, cidr_block=cidr_block, vpc_id=vpc_id
            )
        except ClientError as e:
            error_msg = f"The CIDR '{cidr_block}' conflicts with another subnet"
            if error_msg == e.response["Error"]["Message"]:
                subnet = list([subnet for subnet in subnets if subnet.cidr_block == cidr_block])[0]
                logger.info(f"subnet {subnet.id} create failed because it exists {e}")
            else:
                raise e

        assert subnet is not None, f"Failed to create Subnet {index} of {num_subnet}"
        subnets.append(subnet)

    # return data
    return AwsAssetsDto(ec2_instances=ec2_instances, ebs_volumes=ebs_volumes, vpcs=vpcs, subnets=subnets)


def cleanup_aws_assets_from_account(aws: AWS, aws_assets: AwsAssetsDto):
    """Cleanup assets from the given AWS Account

    Args:
        aws (AWS): The AWS Account in which to cleanup assets
        aws_assets (AwsAssetsDto): The AWS Assets to cleanup from the AWS Account
    """
    # in case the AWS Assets were never created
    if not aws_assets:
        return

    # EC2 Instance
    instance_id_list = [ec2_instance.id for ec2_instance in aws_assets.ec2_instances]
    try:
        aws.ec2.ec2_client.terminate_instances(InstanceIds=instance_id_list)
    except Exception as e:
        logger.warn(f"Issue terminating Instances: {e}")

    # EBS volumes
    for ebs_volume in aws_assets.ebs_volumes:
        try:
            aws.ebs.delete_volume(ebs_volume.id)
        except Exception as e:
            logger.warn(f"Issue terminating Volume {ebs_volume.id}: {e}")

    # Subnet
    for subnet in aws_assets.subnets:
        if not subnet.default_for_az:
            try:
                aws.subnet.delete_subnet(subnet_id=subnet.id)
            except Exception as e:
                logger.warn(f"Issue deleting Subnet {subnet.id}: {e}")

    # VPC
    for vpc in aws_assets.vpcs:
        if not vpc.is_default:
            try:
                aws.vpc.delete_vpc(vpc_id=vpc.id)
            except Exception as e:
                logger.warn(f"Issue deleting VPC {vpc.id}: {e}")


def attach_ebs_volumes_to_ec2_instances(
    aws: AWS, aws_assets: AwsAssetsDto, num_to_attach: int, ebs_volume_device: str = "/dev/sdh"
) -> bool:
    """Attach the provided number of EBS Volumes to EC2 Instances from AWS Assets

    Args:
        aws (AWS): AWS Account to perform EBS Attachments
        aws_assets (AwsAssetsDto): AWS Assets present in AWS Account
        num_to_attach (int): The number of EBS to EC2 attachments to perform
        ebs_volume_device (str, optional): The volume device name. Defaults to "/dev/sdh"

    Returns:
        bool: Returns False if the requested number to attach cannot be fulfilled
          using the provided AWS Assets, True otherwise
    """
    # ensure we have sufficient assets for the request
    if len(aws_assets.ec2_instances) < num_to_attach or len(aws_assets.ebs_volumes) < num_to_attach:
        return False

    for index in range(num_to_attach):
        ec2 = aws_assets.ec2_instances[index]
        ebs = aws_assets.ebs_volumes[index]

        aws.ebs.attach_volume_to_ec2_instance(volume_id=ebs.id, device=ebs_volume_device, instance_id=ec2.id)

        aws_assets.attached_ec2_ebs.append([ec2, ebs])

    return True


def detach_ebs_volumes_from_ec2_instances(aws: AWS, aws_assets: AwsAssetsDto, ebs_volume_device: str = "/dev/sdh"):
    """Detach EBS Volumes attached to EC2 Instances from the provided aws_assets object

    Args:
        aws (AWS): AWS Account
        aws_assets (AwsAssetsDto): AWS Assets
        ebs_volume_device (str, optional): The volume device name. Defaults to "/dev/sdh"
    """
    for ec2, ebs in aws_assets.attached_ec2_ebs:
        aws.ebs.detach_volume_from_instance(volume_id=ebs.id, device=ebs_volume_device, instance_id=ec2.id)

    aws_assets.attached_ec2_ebs.clear()


def detach_and_delete_volume(aws: AWS, volume_id: str, device: str, instance_id: str, force: bool = False):
    """This method will detach the volume from the ec2 instance and then delete the volume.

    Args:
        aws (AWS): AWS Account object
        volume_id (str): The AWS EBS Volume ID
        device (str): The volume device name
        instance_id (str): The AWS EC2 Instance ID
        force (bool, optional): If True, the detachment of the EBS Volume is performed regardless of any failures. Defaults to False.
    """
    aws.ebs.detach_volume_from_instance(volume_id=volume_id, device=device, instance_id=instance_id, force=force)
    aws.ebs.delete_volume(volume_id=volume_id)


def create_ec2_with_ebs_attached(
    aws: AWS,
    ec2_image_id: str,
    tags: list[Tag],
    volume_size: int,
    volume_device: str,
    volume_type: str = EBSVolumeType.GP2.value,
    ec2_key_name: str = "",
    security_groups: list[str] = ["default"],
    ebs_encrypt: bool = False,
    subnet_id: str = "",
    security_group_ids: list[str] = [],
    availability_zone: str = "",
) -> tuple[list, Any]:
    """Create AWS EC2 Instance with 1 EBS Volume attached

    Args:
        aws (AWS): AWS Account object
        ec2_image_id (str): The AWS EC2 Image ID
        tags (list[Tag]): A list of Tag objects to add to the EC2 Instance
        volume_size (int): Desired EBS Volume size in GB
        volume_device (str): Volume device name, eg: "/dev/sdh"
        volume_type (str, optional): The EBSVolumeType. Defaults to EBSVolumeType.GP2.value.
        ec2_key_name (str, optional): EC2 key pair name. Defaults to "".
        security_groups (list[str], optional): A list of security groups for the EC2 Instance. Defaults to ["default"].
        ebs_encrypt (bool, optional): If True, the EBS Volume will be encrypted. Defaults to False.
        subnet_id (str, optional): The subnet ID for the EC2 Instance. If provided, "security_groups" is ignored and "security_group_ids" is used. Defaults to "".
        security_group_ids (list[str], optional): A list of security group IDs. The parameter is only used if "subnet_id" is provided, otherwise "security_groups" is used. Defaults to [].
        availability_zone (str, optional): The availability zone for the EC2 Instance. Defaults to "".

    Returns:
        tuple[list, Any]: A 1 element array containing the created EC2 Instance, and the attached EBS Volume
    """
    logger.info(
        f"Create ec2 with ebs attached security groups: {security_groups}, ec2_image_id: {ec2_image_id}, \
        availability_zone: {availability_zone}, ec2_key_name: {ec2_key_name}"
    )
    ec2_instances = aws.ec2.create_ec2_instance(
        key_name=ec2_key_name,
        image_id=ec2_image_id,
        availability_zone=availability_zone,
        tags=tags,
        security_groups=security_groups,
        subnet_id=subnet_id,
        security_group_ids=security_group_ids,
    )
    ec2_instance_id = ec2_instances[0].id

    # Creating EBS Volume
    if not availability_zone:
        availability_zone = ec2_instances[0].placement["AvailabilityZone"]
    ebs_volume = aws.ebs.create_ebs_volume(
        availability_zone=availability_zone, size=volume_size, volume_type=volume_type, tags=tags, encrypted=ebs_encrypt
    )

    # Attaching EBS volume to the EC2 instance
    aws.ebs.attach_volume_to_ec2_instance(volume_id=ebs_volume.id, device=volume_device, instance_id=ec2_instance_id)

    return ec2_instances, ebs_volume


def get_csp_ec2_and_ebs(context: Context, ec2_list: list = [], ebs_list: list = []) -> tuple[list, list]:
    """Get the CSP Machine Instance and CSP Volume objects for the AWS EC2 and EBS ID lists provided

    Args:
        context (Context): The test Context
        ec2_list (list, optional): A list of AWS EC2 Instances. Defaults to [].
        ebs_list (list, optional): A list of AWS EBS Volumes. Defaults to [].

    Returns:
        tuple[list, list]: A list each of the CSP Machine Instances and EBS Volumes found
    """
    ec2_csp_list = []
    ebs_csp_list = []

    if ec2_list:
        logger.info(f"Fetching CSP EC2 for {ec2_list}")
        for aws_ec2 in ec2_list:
            ec2_csp_list.append(
                InvMgrSteps.get_csp_instance_by_ec2_instance_id(
                    context=context,
                    ec2_instance_id=aws_ec2.id,
                )
            )

    if ebs_list:
        logger.info(f"Fetching CSP EBS for {ebs_list}")
        for aws_ebs in ebs_list:
            ebs_csp_list.append(
                InvMgrSteps.get_csp_volume_by_ebs_volume_id(
                    context=context,
                    ebs_volume_id=aws_ebs.id,
                )
            )

    return ec2_csp_list, ebs_csp_list


def create_elastic_ip(aws: AWS) -> Union[Address, list[Address]]:
    """This method will create an Elastic IP only if there are less than 5 present in the account. 1 account has a limit of 5 Elastic IPs only.

    Args:
        aws (AWS): AWS Account object

    Returns:
        Union[Address, list[Address]]: If there are less than 5 Elastic IPs in the AWS Account, then a new Address is allocated and returned.
            Otherwise, a list of all allocated Addresses is returned.
    """
    elastic_ips = aws.ec2.get_number_of_elastic_ips()
    if elastic_ips < 5:
        allocation = aws.ec2.create_elastic_ip()
        return allocation
    else:
        return aws.ec2.get_all_allocation_address()


def determine_unassociated_elastic_ip(addresses: list[Address]) -> Address:
    """Returns the Elastic IP Address object which is not associated to any EC2 instance.

    Args:
        addresses (list[Address]): A list of Address objects to check

    Returns:
        Address: The first Address that does not contain an "AssociationId" value.
    """
    elastic_ip: Address = None

    for address in addresses:
        if not address.AssociationId:
            elastic_ip = address
            break

    return elastic_ip


def get_elastic_ips_updated_status(aws: AWS, current_elastic_ip: Address) -> Address:
    """This method will be useful when an Elastic IP is associated to an EC2 and need to get the updated AssociationId for the Elastic IP.

    Args:
        aws (AWS): AWS Account object
        current_elastic_ip (Address): Current Address object

    Returns:
        Address: An updated Address object from AWS with matching Public IP address
    """
    elastic_ips: list[Address] = aws.ec2.get_all_allocation_address()
    for elastic_ip in elastic_ips:
        if elastic_ip.PublicIp == current_elastic_ip.PublicIp:
            return elastic_ip


def create_elastic_ip_and_associate_to_ec2_instance(aws: AWS, ec2_instance_id: str) -> Address:
    """Create or reuse an Elastic IP and associate it to the provided EC2 Instance

    Args:
        aws (AWS): AWS Account object
        ec2_instance_id (str): The AWS EC2 Instance ID

    Returns:
        Address: The Elastic IP Address object used
    """
    elastic_ip_address: Address = None

    # returns a list if already 5 EIPs are present else returns the created one
    elastic_ip = create_elastic_ip(aws)
    if isinstance(elastic_ip, Address):
        elastic_ip_address = elastic_ip
    else:
        elastic_ip_address = determine_unassociated_elastic_ip(addresses=elastic_ip)

    # if the else block returns a null object,
    # the first one from the list of available EIPs will be selected.
    elastic_ip_address = elastic_ip_address if elastic_ip_address else elastic_ip[0]
    allocation_id = elastic_ip_address.AllocationId

    aws.ec2.associate_elastic_ip_to_instance(allocation_id=allocation_id, ec2_instance_id=ec2_instance_id)
    elastic_ip_address = get_elastic_ips_updated_status(aws=aws, current_elastic_ip=elastic_ip_address)
    return elastic_ip_address
