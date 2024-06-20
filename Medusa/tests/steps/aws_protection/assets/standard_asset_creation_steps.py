"""
This module contains functions related to the creation and deletion of Standard EC2 and EBS Assets used for tests
"""

import json
import os
import logging
import random
import uuid

from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.ebs_volume_type import EBSVolumeType
from lib.common.enums.os import OS

from lib.dscc.backup_recovery.aws_protection.common.models.asset_set import AssetSet
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import CSPVolumeModel

from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag

from tests.e2e.aws_protection.context import Context, SanityContext

import tests.steps.aws_protection.assets.ec2_ebs_steps as EC2EBSSteps
import tests.steps.aws_protection.inventory_manager_steps as IMS
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps
import tests.steps.aws_protection.common_steps as CommonSteps

logger = logging.getLogger()

ami_filters = {
    OS.REDHAT: {"Name": "RHEL-*HVM-2*", "Desc": "Provided by Red Hat, Inc."},
    OS.UBUNTU: {"Name": "ubuntu/images/hvm-ssd/ubuntu-jammy-*server-2*", "Desc": "*Ubuntu, * LTS, amd64 jammy*"},
    OS.DEBIAN: {"Name": "debian-12*", "Desc": "Debian 12*"},
    OS.SUSE: {
        "Name": "suse-sles-15-*-hvm-ssd*",
        "Desc": "SUSE Linux Enterprise Server 15 SP5 (HVM, 64-bit, SSD-Backed)",
    },
    OS.AMAZON: {"Name": "al2*-ami-2*-kernel-*", "Desc": "Amazon Linux 2* AMI 2* x86_64 HVM kernel-*"},
    OS.WINDOWS: {
        "Name": "Windows_Server-2*-English-Full-Base-*",
        "Desc": "Microsoft Windows Server * Full Locale English AMI provided by Amazon",
    },
}

ami = {
    "us-west-1": [
        ("ami-054965c6cd7c6e462", "Redhat 8", OS.REDHAT),
        ("ami-02ea247e531eb3ce6", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-024527629f55e9322", "Debian 11", OS.DEBIAN),
        ("ami-032d5ecad210ed6c8", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0d9858aa3c6322f73", "Amazon Linux 5.10", OS.AMAZON),
        # PAID ("ami-0581444235c0e70a2", "Fedora 34-1.2"),
        # PAID ("ami-0dee0f906cf114191", "CentOS 7"),
    ],
    "us-west-2": [
        ("ami-0b28dfc7adc325ef4", "Redhat 8", OS.REDHAT),
        ("ami-017fecd1353bcc96e", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-071e6cafc48327ca2", "Debian 11", OS.DEBIAN),
        ("ami-019d533b7b2201eff", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-098e42ae54c764c35", "Amazon Linux 5.10", OS.AMAZON),
        # PAID ("ami-0cf4b19956167cf16", "Fedora 34-1.2"),
        # PAID ("ami-08c191625cfb7ee61", "CentOS 7"),
    ],
    "us-east-1": [
        ("ami-0b0af3577fe5e3532", "Redhat 8", OS.REDHAT),
        ("ami-08c40ec9ead489470", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-09a41e26df464c548", "Debian 11", OS.DEBIAN),
        ("ami-08e167817c87ed7fd", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0cff7528ff583bf9a", "Amazon Linux 5.10", OS.AMAZON),
        # PAID ("ami-0883f2d26628ad0cf", "Fedora 34-1.2"),
        # PAID ("ami-002070d43b0a4f171", "CentOS 7"),
    ],
    "us-east-2": [
        ("ami-0ba62214afa52bec7", "Redhat 8", OS.REDHAT),
        ("ami-097a2df4ac947655f", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-0c7c4e3c6b4941f0f", "Debian 11", OS.DEBIAN),
        ("ami-0535d9b70179f9734", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-02d1e544b84bf7502", "Amazon Linux 5.10", OS.AMAZON),
        # PAID ("ami-086c1d77a774201ee", "Fedora 34-1.2"),
        # PAID ("ami-05a36e1502605b4aa", "CentOS 7"),
    ],
    # New regions added as part of worldwide support feature
    "ap-south-1": [
        ("ami-06a0b4e3b7eb7a300", "Redhat 8", OS.REDHAT),
        ("ami-062df10d14676e201", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-02a0cf8818da94f25", "Debian 11", OS.DEBIAN),
        ("ami-08ec390ae500191e6", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-08df646e18b182346", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "ap-northeast-1": [
        ("ami-0cf31bd68732fb0e2", "Redhat 8", OS.REDHAT),
        ("ami-03f4fa076d2981b45", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-073770dc3242b2a06", "Debian 11", OS.DEBIAN),
        ("ami-083ce3c8d8d74b88c", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0b7546e839d7ace12", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "ap-northeast-2": [
        ("ami-0bb1758bf5a69ca5c", "Redhat 8", OS.REDHAT),
        ("ami-0e9bfdb247cc8de84", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-0cba8d11ab79b2e45", "Debian 11", OS.DEBIAN),
        ("ami-0b8951725398f7575", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0fd0765afb77bcca7", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "ap-northeast-3": [
        ("ami-08daa4649f61b8684", "Redhat 8", OS.REDHAT),
        ("ami-08c2ee02329b72f26", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-0e44d929367d23d2a", "Debian 11", OS.DEBIAN),
        ("ami-044bb1b8d85d630a7", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0c66c8e259df7ec04", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "ap-southeast-1": [
        ("ami-0d6ba217f554f6137", "Redhat 8", OS.REDHAT),
        ("ami-07651f0c4c315a529", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-0024cc9cb42261ace", "Debian 11", OS.DEBIAN),
        ("ami-01ae98b95555d6f5d", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0c802847a7dd848c0", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "ap-southeast-2": [
        ("ami-016461ac55b16fd05", "Redhat 8", OS.REDHAT),
        ("ami-09a5c873bc79530d9", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-061cac5292ca5403c", "Debian 11", OS.DEBIAN),
        ("ami-00189b0cfffba54bb", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-07620139298af599e", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "ca-central-1": [
        ("ami-0277fbe7afa8a33a6", "Redhat 8", OS.REDHAT),
        ("ami-0a7154091c5c6623e", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-08365316d1f9fdec3", "Debian 11", OS.DEBIAN),
        ("ami-0cdd9ddd1a4a73cee", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-00f881f027a6d74a0", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "eu-central-1": [
        ("ami-06ec8443c2a35b0ba", "Redhat 8", OS.REDHAT),
        ("ami-0caef02b518350c8b", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-0a5b5c0ea66ec560d", "Debian 11", OS.DEBIAN),
        ("ami-001a77181c22a52ba", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0a1ee2fb28fe05df3", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "eu-west-1": [
        ("ami-0ec23856b3bad62d3", "Redhat 8", OS.REDHAT),
        ("ami-096800910c1b781ba", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-0f98479f8cd5b63f6", "Debian 11", OS.DEBIAN),
        ("ami-0be8fad2a3296a74f", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0d71ea30463e0ff8d", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "eu-west-2": [
        ("ami-0ad8ecac8af5fc52b", "Redhat 8", OS.REDHAT),
        ("ami-0f540e9f488cfa27d", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-048df70cfbd1df3a9", "Debian 11", OS.DEBIAN),
        ("ami-0f7ae4d56aee106f1", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-078a289ddf4b09ae0", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "eu-west-3": [
        ("ami-0a65f5e7f3e0a10d7", "Redhat 8", OS.REDHAT),
        ("ami-0493936afbe820b28", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-002ff2c881c910aa8", "Debian 11", OS.DEBIAN),
        ("ami-05c58114a34dbae09", "SUSE SLES 15 SP4", OS.SUSE),
        ("ami-0f5094faf16f004eb", "Amazon Linux 5.10", OS.AMAZON),
    ],
    "eu-north-1": [
        ("ami-0baa9e2e64f3c00db", "Redhat 8", OS.REDHAT),
        ("ami-0989fb15ce71ba39e", "Ubuntu 22.04 LTS", OS.UBUNTU),
        ("ami-00189fd46154b0f9d", "Debian 11", OS.DEBIAN),
        ("ami-0fed65287a5aed2cf", "SUSE SLES 15 SP5", OS.SUSE),
        ("ami-0917076ab9780844d", "Amazon Linux 5.10", OS.AMAZON),
    ],
}


WINDOWS_AMI_DESCRIPTION: str = "Microsoft Windows Server 2022 Full Locale English AMI provided by Amazon"

windows_ami = {
    "us-east-1": "ami-04132f301c3e4f138",  # N. Virgina
    "us-east-2": "ami-0d2f97c8735a48a15",  # Ohio
    "us-west-1": "ami-0b0de58bd9519cc54",  # N. California
    "us-west-2": "ami-05cc83e573412838f",  # Oregon
    "ap-south-1": "ami-071288aec7feafa11",  # Mumbai
    "ap-southeast-1": "ami-0de4e14ede8812678",  # Singapore
    "ap-southeast-2": "ami-0d737c54c2d417954",  # Sydney
    "ap-northeast-1": "ami-0d862f7ba344bc551",  # Tokyo
    "ap-northeast-2": "ami-0b91e8198d6d99ee1",  # Seoul
    "ap-northeast-3": "ami-08677a231b8d68410",  # Osaka
    "ca-central-1": "ami-03fc7135bffa2b818",  # Central
    "eu-central-1": "ami-00b95ae25143f8b10",  # Frankfurt
    "eu-west-1": "ami-09367cb512d8a2ee4",  # Ireland
    "eu-west-2": "ami-0ff61b5c37564aecb",  # London
    "eu-west-3": "ami-0ec294f49d26f821e",  # Paris
    "eu-north-1": "ami-09d460305982fdfcf",  # Stockholm
}


def get_latest_ami_image_filters(aws: AWS, operating_system: OS) -> str:
    logger.info(f"Find OS: {operating_system} AMI in region {aws.region_name}")
    image_id = ""

    if aws.ec2.verify_free_instance_types():
        filters = [
            {"Name": "architecture", "Values": ["x86_64"]},
            {"Name": "owner-alias", "Values": ["amazon"]},
            {"Name": "image-type", "Values": ["machine"]},
            {"Name": "root-device-type", "Values": ["ebs"]},
            {"Name": "virtualization-type", "Values": ["hvm"]},
            {
                "Name": "block-device-mapping.volume-size",
                "Values": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "30"],
            },
            {"Name": "block-device-mapping.volume-type", "Values": ["gp2", "gp3"]},
            {"Name": "state", "Values": ["available"]},
            {"Name": "name", "Values": [ami_filters[operating_system]["Name"]]},
            {"Name": "description", "Values": [ami_filters[operating_system]["Desc"]]},
        ]
        owners = ["amazon"]
        amis = aws.ec2.get_all_amis(owners=owners, filters=filters)
        amis_sorted = sorted(amis["Images"], key=lambda ami: ami["CreationDate"], reverse=True)

        logger.info(f"Random choice from 10 newest amis: {amis_sorted}")
        ami_chosen = random.choice(amis_sorted[0:10])
        image_id = ami_chosen["ImageId"]

    if not image_id:
        logger.info("Cant find ami with filters. Back to default ImageId")
        if operating_system == OS.WINDOWS:
            image_id = windows_ami.get(aws.region_name)
        else:
            region_images = ami.get(aws.region_name)
            image_id = [image[0] for image in region_images if operating_system in image[2]][0]

    assert image_id
    logger.info(f"AMI id: {image_id}")
    return image_id


def random_ami_chooser(aws: AWS, image_name: OS = OS.RANDOM) -> str:
    """Randomly choose an AWS AMI from the provided "region"

    Args:
        aws (AWS): AWS account object that will be used to find AMI within specific region

    Returns:
        str: The AWS AMI name
    """
    logger.info(f"Region for AMI chooser: {aws.region_name}")
    ami_used_dict = {}
    ami_used_file_name = "ami_used_register.json"

    # load data from ami used register
    file_exists = os.path.exists(ami_used_file_name)
    if file_exists:
        retries = 5
        for i in range(retries):
            try:
                with open(ami_used_file_name) as json_file:
                    ami_used_dict = json.load(json_file)
                    break
            except json.decoder.JSONDecodeError as e:
                logger.warn(f"Error reading file {ami_used_file_name}, retry: {i} \n {e=}")

    if not ami_used_dict:
        ami_used_dict = {"ami_used": [], "loop_count": 0}

    # check not used amis
    images = ami.get(aws.region_name)
    if image_name == OS.RANDOM:
        available_images = [image for image in images if list(image[0:2]) not in ami_used_dict["ami_used"]]
        if not available_images:
            os.remove(ami_used_file_name)
            ami_used_dict["ami_used"] = []
            ami_used_dict["loop_count"] += 1
            available_images = images

        # choose image from region
        image = random.choice(available_images)
        ami_used_dict["ami_used"].append(image[0:2])

        # write chosen ami to register
        with open(ami_used_file_name, "w") as outfile:
            json.dump(ami_used_dict, outfile)
    else:
        image = next(img for img in images if image_name == img[2])

    ami_image = get_latest_ami_image_filters(aws, image[2])

    if ami_image == image[0]:
        logger.info(f"Default AMI used: {image[0]} - {image[1]}, - {image[2]}")
    else:
        logger.info(f"Newest AMI used: {ami_image} - {image[2]}")

    return ami_image


def create_standard_assets(
    context: Context,
    aws: AWS,
    csp_account_name: str,
    asset_set: AssetSet,
    region: str,
    key_pair: str,
    tag_value: str = "api",
    prefix: str = "standard",
    aws_assets_only: bool = False,
    use_static_key_pair: bool = False,
    force_delete: bool = False,
) -> AssetSet:
    """Function create standard assets with the following specifications:
        1 X EC2 instance with 2 EBS volume (1 gp2 and 1 gp3)
        2 x EBS volumes (1 gp2 and 1 gp3)
        1 x EC2 automatic protection group
        1 x EC2 custom protection group
        1 x EBS automatic protection group
        1 x EBS custom protection group

    Args:
        context (Context): atlantia context class
        aws (AWS): AWS factory object
        csp_account_name (str): name of the CSP account registered in the DSCC B&R application
        asset_set (AssetSet): Asset set initialized in the context.
        region (str): region same as the asset set
        key_pair (str): key pair name from the context
        tag_value (str, optional): Defaults to "api".
        prefix (str, optional): asset name tag prefix string. Defaults to "standard".
        aws_assets_only (bool, optional): To skip protection group creation. Defaults to False.
        use_static_key_pair (bool, optional): If True, the "key_name" is assumed to exist and will not be created. Defaults to False.
        force_delete (bool,optional): If True, delete all discovered assets

    Returns:
        AssetSet: The AssetSet object with the asset details populated.
    """
    # check if standard assets exists
    discovered_asset_set = discover_standard_assets(
        context, aws, region, asset_set, csp_account_name, tag_value, aws_assets_only, force_delete
    )
    # if we have an asset_set returned, we found our standard assets
    if discovered_asset_set:
        logger.info(f"We found the standard assets: {tag_value}")
        return discovered_asset_set

    logger.info(f"We did not find the standard assets: {tag_value}")

    availability_zones = [
        zone["ZoneName"] for zone in aws.ec2.ec2_client.describe_availability_zones()["AvailabilityZones"]
    ]
    availability_zone = availability_zones[0]
    subnets = [subnet for subnet in aws.subnet.get_all_subnets() if subnet.availability_zone == availability_zone]
    subnet = subnets[0]
    security_groups = [
        security_group
        for security_group in aws.security_group.get_all_security_groups()
        if security_group.vpc_id == subnet.vpc_id
    ]
    security_group = security_groups[-1]

    aws.security_group.update_security_group_ingress_allow_all(security_group)

    if not use_static_key_pair:
        generate_key_pair(aws, key_pair)

    ec2_instances, attached_ebs_volumes = deploy_ec2(
        aws, region, key_pair, tag_value, prefix, availability_zone, subnet, security_group
    )

    ec2_instance_id = ec2_instances[-1].id
    asset_set.ec2_instance_id = ec2_instance_id

    ebs_volumes = deploy_ebs(aws, tag_value, prefix, availability_zone)
    ebs_volume_ids = [ebs_volume.id for ebs_volume in ebs_volumes]
    (
        asset_set.ebs_volume_1_id,
        asset_set.ebs_volume_2_id,
    ) = ebs_volume_ids
    asset_set.update_id_lists()
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name=csp_account_name)
    CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account.id)
    # SCINT has multiple EC2 and EBS with the same cspInfo.id.  We'll provide an "Account ID" as well to filter on
    asset_set.csp_machine_instance_id_list = [
        IMS.get_csp_instance_by_ec2_instance_id(
            context=context, ec2_instance_id=ec2_instance_id, account_id=csp_account.id
        ).id
        for ec2_instance_id in asset_set.ec2_instance_id_list
    ]
    asset_set.csp_volume_id_list = [
        IMS.get_csp_volume_by_ebs_volume_id(context=context, ebs_volume_id=ebs_volume_id, account_id=csp_account.id).id
        for ebs_volume_id in asset_set.ebs_volume_id_list
    ]

    asset_set.attached_ebs_volume_id_list = [volume.id for volume in attached_ebs_volumes]
    asset_set.csp_attached_ebs_volume_id_list = [
        IMS.get_csp_volume_by_ebs_volume_id(
            context=context, ebs_volume_id=ebs_volume_id.id, account_id=csp_account.id
        ).id
        for ebs_volume_id in attached_ebs_volumes
    ]

    if aws_assets_only:
        return asset_set

    asset_set = create_standard_assets_pgs(context, region, tag_value, asset_set, csp_account_name)
    return asset_set


def create_standard_assets_pgs(
    context: Context, region: str, tag_value: str, asset_set: AssetSet, csp_account_name: str
) -> AssetSet:
    """Create the standard assets Protection Groups

    Args:
        context (Context): The test Context object
        region (str): Region same as the asset set
        tag_value (str): Name tag prefix value
        asset_set (AssetSet): The AssetSet to which to add the Protection Groups
        csp_account_name (str): The name of the CSP account registered in the DSCC B&R application

    Returns:
        AssetSet: The AssetSet object with standard asset protection groups created
    """
    if isinstance(context, SanityContext):
        ec2_automatic_pg_name = f"{context.sanity_pg_dynamic_instance}_{csp_account_name}"
        ec2_custom_pg_name = f"{context.sanity_pg_custom_instance}_{csp_account_name}"
        ebs_automatic_pg_name = f"{context.sanity_pg_dynamic_volume}_{csp_account_name}"
        ebs_custom_pg_name = f"{context.sanity_pg_custom_volume}_{csp_account_name}"
    else:
        ec2_automatic_pg_name = f"ec2_auto_standard_{region}_{csp_account_name}"
        ec2_custom_pg_name = f"ec2_custom_standard_{region}_{csp_account_name}"
        ebs_automatic_pg_name = f"ebs_auto_standard_{region}_{csp_account_name}"
        ebs_custom_pg_name = f"ebs_custom_standard_{region}_{csp_account_name}"

    key_tag = []
    value_tag = []
    if isinstance(tag_value, list):
        for tag in tag_value:
            key_tag.append(tag.key)
            value_tag.append(tag.value)
    else:
        key_tag = ["standard"]
        value_tag = [tag_value]

    # Automatic protection group
    ec2_auto_pg_id = IMS.create_automatic_aws_protection_group(
        context=context,
        name=ec2_automatic_pg_name,
        type=AssetType.CSP_MACHINE_INSTANCE,
        key_list=key_tag,
        value_list=value_tag,
        region=region,
        csp_account_name=csp_account_name,
    )
    ebs_auto_pg_id = IMS.create_automatic_aws_protection_group(
        context=context,
        name=ebs_automatic_pg_name,
        type=AssetType.CSP_VOLUME,
        key_list=key_tag,
        value_list=value_tag,
        region=region,
        csp_account_name=csp_account_name,
    )

    csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name=csp_account_name)
    # Custom protection group
    csp_machine_instance_id_list = [
        IMS.get_csp_instance_by_ec2_instance_id(
            context=context, ec2_instance_id=ec2_instance_id, account_id=csp_account.id
        ).id
        for ec2_instance_id in asset_set.ec2_instance_id_list
    ]

    ec2_custom_pg_id = IMS.create_custom_aws_protection_group(
        context=context,
        name=ec2_custom_pg_name,
        type=AssetType.CSP_MACHINE_INSTANCE,
        asset_list=csp_machine_instance_id_list,
        region=region,
        csp_account_name=csp_account_name,
    )

    csp_volume_id_list = [
        IMS.get_csp_volume_by_ebs_volume_id(context=context, ebs_volume_id=ebs_volume_id, account_id=csp_account.id).id
        for ebs_volume_id in asset_set.ebs_volume_id_list
    ]

    ebs_custom_pg_id = IMS.create_custom_aws_protection_group(
        context=context,
        name=ebs_custom_pg_name,
        type=AssetType.CSP_VOLUME,
        asset_list=csp_volume_id_list,
        region=region,
        csp_account_name=csp_account_name,
    )

    asset_set.ec2_automatic_pg_id, asset_set.ec2_custom_pg_id = ec2_auto_pg_id, ec2_custom_pg_id
    asset_set.ebs_automatic_pg_id, asset_set.ebs_custom_pg_id = ebs_auto_pg_id, ebs_custom_pg_id
    asset_set.update_id_lists()

    return asset_set


def deploy_ebs(aws: AWS, tag_value: str, prefix: str, availability_zone: str) -> list:
    """Deploy ebs volumes in the given AWS factory initialized region

    Args:
        aws (AWS): AWS factory object
        tag_value (str): Tag value
        prefix (str): Prefix for name tag
        availability_zone (str): Availability zone for the EBS Volume

    Returns:
       list: list of AWS EBS Volume objects
    """
    ebs_volumes = EC2EBSSteps.create_ebs_volumes_with_custom_config(
        aws=aws,
        availability_zone=availability_zone,
        ebs_volume_name_prefix=prefix,
        volume_count=2,
        volume_size=10,
        volume_type=["gp2", "gp3"],
        tags=[Tag(Key="standard", Value=tag_value)],
    )

    return ebs_volumes


def generate_key_pair(aws: AWS, key_pair: str):
    """Generate a Key Pair file.  If the Key Pair file already exists, it will be deleted and a new Key Pair will be generated.

    Args:
        aws (AWS): AWS factory object
        key_pair (str): Key Pair name
    """
    # Check if key_pair is present (later distinguish key_pair_region)
    all_key_pairs = aws.ec2.get_all_ec2_key_pair()
    logger.info(f"All key pairs: {all_key_pairs}")
    key_pair_present = aws.ec2.get_key_pair(key_name=key_pair)
    logger.info(f"Key pair present: {key_pair_present}")
    if key_pair_present:
        aws.ec2.delete_key_pair(key_name=key_pair)
        logger.info("Key pair deleted")
    key_pair_file = f"{key_pair}.pem"
    file_exists = os.path.exists(key_pair_file)
    if file_exists:
        logger.info(f"Removing {key_pair_file} from drive")
        os.remove(key_pair_file)
    file_exists = os.path.exists(key_pair_file)
    logger.info(f"File exists: {file_exists}")
    assert not file_exists, "Private key file still exists"

    key_generated = aws.ec2.create_ec2_key_pair(key_name=key_pair)
    logger.info(f"Key pair generated: {key_generated}")
    private_key_file = open(key_pair_file, "w")
    private_key_file.write(key_generated.key_material)
    private_key_file.close()
    logger.info(f"File saved: {key_pair_file}")
    with open(key_pair_file) as f:
        contents = f.read()
        logger.info(f"File content: {contents}")


def deploy_ec2(
    aws: AWS,
    region: str,
    key_pair: str,
    tag_value: str,
    prefix: str,
    availability_zone: str,
    subnet: str,
    security_group: str,
) -> tuple[list, list]:
    """Deploy EC2 instance using the AWS factory object client

    Args:
        aws (AWS): AWS factory object
        region (str): Region to deploy the EC2 instance
        key_pair (str): Key Pair used to login to EC2 instance
        tag_value (str): Name tag value
        prefix (str): Name tag prefix value
        availability_zone (str): Availability zone to create EC2 instance
        subnet (str): Subnet to use for EC2 creation
        security_group (str): Security Group to attach to EC2 instance

    Returns:
        tuple[list, list]: A list of AWS EC2 Instances and a list of AWS EBS Volumes
    """
    ec2_instances, attached_ebs_volumes = EC2EBSSteps.create_ec2_instances_with_custom_config(
        aws=aws,
        availability_zone=availability_zone,
        key_name=key_pair,
        image_id=random_ami_chooser(aws),
        ec2_count=1,
        ec2_instance_name_prefix=prefix,
        volume_count=2,
        volume_size=10,
        volume_type=["gp2", "gp3"],
        subnet_id=subnet.id,
        security_groups=[security_group.id],
        tags=[Tag(Key="standard", Value=tag_value)],
    )

    return ec2_instances, attached_ebs_volumes


def delete_standard_assets(
    context: Context,
    aws: AWS,
    asset_set: AssetSet,
    aws_assets_only: bool = False,
):
    """Deletes standard assets pupulated in the AssetSet object.

    Args:
        context (Context): atlantia context object
        aws (AWS): AWS factory object
        asset_set (AssetSet): context asset set attribute
        aws_assets_only (bool, optional): If True, the standard asset Protection Groups will not be deleted. Defaults to False.
    """
    if not aws_assets_only:
        IMS.delete_protection_groups(context=context, protection_group_ids=asset_set.standard_pg_id_list)
    for ec2_instance_id in asset_set.ec2_instance_id_list:
        if ec2_instance_id:
            aws.ec2.terminate_ec2_instance(ec2_instance_id=ec2_instance_id)
    for ebs_volume_id in asset_set.ebs_volume_id_list + asset_set.attached_ebs_volume_id_list:
        if ebs_volume_id:
            aws.ebs.delete_volume(volume_id=ebs_volume_id)


def update_standard_asset_details(
    context: Context,
    region: str,
    asset_set: AssetSet,
    aws_account_name: str,
    tag_value: str = "api",
    aws_assets_only: bool = False,
) -> AssetSet:
    """Function updates the details of the existing standard asset to AssetSet context attribute.

    Args:
        context (Context): Atlantia context object
        region (str): context region attribute
        asset_set (AssetSet): context asset set attribute
        aws_account_name (str): AWS CSP Account Name
        tag_value (str, optional): Tag value. Defaults to "api"
        aws_assets_only (bool, optional): If True, the standard asset Protection Groups will not be updated. Defaults to False.

    Returns:
        AssetSet: return AssetSet object with the asset details populated.
    """
    if isinstance(context, SanityContext):
        ec2_automatic_pg_name = f"{context.sanity_pg_dynamic_instance}_{aws_account_name}"
        ec2_custom_pg_name = f"{context.sanity_pg_custom_instance}_{aws_account_name}"
        ebs_automatic_pg_name = f"{context.sanity_pg_dynamic_volume}_{aws_account_name}"
        ebs_custom_pg_name = f"{context.sanity_pg_custom_volume}_{aws_account_name}"
    else:
        ec2_automatic_pg_name = f"ec2_auto_standard_{region}_{aws_account_name}"
        ec2_custom_pg_name = f"ec2_custom_standard_{region}_{aws_account_name}"
        ebs_automatic_pg_name = f"ebs_auto_standard_{region}_{aws_account_name}"
        ebs_custom_pg_name = f"ebs_custom_standard_{region}_{aws_account_name}"

    tag: CSPTag = CSPTag(key="standard", value=tag_value)
    logger.info(f"sanity Tag: {tag}")
    # Get standard asset CSP Instance
    csp_instances = IMS.get_csp_instances_by_tag(context=context, tag=tag)
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name=aws_account_name)
    asset_set.attached_ebs_volume_id_list = []
    asset_set.ec2_instance_id = None
    asset_set.csp_machine_instance_id_list = [None]
    asset_set.attached_ebs_root_id = None
    for instance in csp_instances:
        if (
            csp_account
            and instance.state != "DELETED"
            and instance.accountInfo.id == csp_account.id
            and instance.cspInfo.cspRegion == region
        ):
            root_device = instance.cspInfo.rootDevice
            asset_set.ec2_instance_id = instance.cspId
            asset_set.csp_machine_instance_id_list = [instance.id]
            # Get EBS Volumes attached to standard asset CSP Instance
            for info in instance.volumeAttachmentInfo:
                if info.device == root_device:
                    asset_set.attached_ebs_root_id = info.attachedTo.name
                    continue
                asset_set.attached_ebs_volume_id_list.append(info.attachedTo.name)

    asset_set.csp_attached_ebs_volume_id_list = [
        IMS.get_csp_volume_by_ebs_volume_id(context=context, ebs_volume_id=ebs_volume_id, account_id=csp_account.id).id
        for ebs_volume_id in asset_set.attached_ebs_volume_id_list
    ]

    # Get standard asset CSP Volumes
    csp_volumes_list = IMS.get_csp_volumes_by_tag(context=context, tag=tag)
    csp_volumes: list[CSPVolumeModel] = []
    asset_set.ebs_volume_id_list = []
    asset_set.csp_volume_id_list = [None, None]
    asset_set.ebs_volume_1_id = None
    asset_set.ebs_volume_2_id = None
    for volume in csp_volumes_list:
        # ensure volume is not an attached volume to the EC2 instance
        if (
            csp_account
            and volume.accountInfo.id == csp_account.id
            and volume.cspId not in asset_set.attached_ebs_volume_id_list
            and volume.state != "DELETED"
            and volume.cspInfo.cspRegion == region
        ):
            csp_volumes.append(volume)
            asset_set.ebs_volume_id_list.append(volume.cspId)
            if len(csp_volumes) == 2:
                csp_volume_ids = [csp_volume.id for csp_volume in csp_volumes]
                asset_set.csp_volume_id_list = csp_volume_ids
                ec2_volume_ids = [csp_volume.cspId for csp_volume in csp_volumes]

                (
                    asset_set.ebs_volume_1_id,
                    asset_set.ebs_volume_2_id,
                ) = ec2_volume_ids
                break

    asset_set.ec2_automatic_pg_id = None
    asset_set.ec2_custom_pg_id = None
    asset_set.ebs_automatic_pg_id = None
    asset_set.ebs_custom_pg_id = None
    if not aws_assets_only:
        pg_list = context.inventory_manager.get_protection_groups(filter=f"name eq '{ec2_automatic_pg_name}'")
        if pg_list.total > 0:
            asset_set.ec2_automatic_pg_id = pg_list.items[0].id

        pg_list = context.inventory_manager.get_protection_groups(filter=f"name eq '{ec2_custom_pg_name}'")
        if pg_list.total > 0:
            asset_set.ec2_custom_pg_id = pg_list.items[0].id

        pg_list = context.inventory_manager.get_protection_groups(filter=f"name eq '{ebs_automatic_pg_name}'")
        if pg_list.total > 0:
            asset_set.ebs_automatic_pg_id = pg_list.items[0].id

        pg_list = context.inventory_manager.get_protection_groups(filter=f"name eq '{ebs_custom_pg_name}'")
        if pg_list.total > 0:
            asset_set.ebs_custom_pg_id = pg_list.items[0].id

    asset_set.update_id_lists()
    return asset_set


def discover_standard_assets(
    context: Context,
    aws: AWS,
    region: str,
    asset_set: AssetSet,
    csp_account_name: str,
    tag_value: str,
    aws_assets_only: bool,
    force_delete: bool = False,
) -> AssetSet:
    """Discover and update standard assets

    Args:
        context (Context): The test Context object
        aws (AWS): AWS factory object
        region (str): The Region to look for standard assets
        asset_set (AssetSet): The AssetSet to populate with discovered standard assets
        csp_account_name (str): The CSP Account Name
        tag_value (str): Tag Value to match on standard assets
        aws_assets_only (bool): If True, the standard asset Protection Groups will not be discovered
        force_delete (bool,optional): If True, delete all discovered assets

    Returns:
        AssetSet: The updated AssetSet with the standard assets populated
    """
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name=csp_account_name)
    CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account.id)
    asset_set = update_standard_asset_details(
        context,
        region,
        asset_set,
        csp_account_name,
        tag_value=tag_value,
        aws_assets_only=aws_assets_only,
    )

    # Force delete whatever was discovered.
    # This should be trigger especially in beginning of sanity suite.
    # Otherwise pem file will be missing.
    if force_delete:
        delete_standard_assets(context, aws, asset_set)
        return None

    # If there are no "None" - then all assets are accounted for
    if None not in asset_set.get_standard_assets()[0]:
        return asset_set

    # If we do have "None", check if it is Protection Group related
    if None not in asset_set.csp_machine_instance_id_list and None not in asset_set.csp_volume_id_list:
        # if we have the EC2 and EBS and it's "not aws_assets_only", then create the Protection Groups
        if not aws_assets_only:
            asset_set = create_standard_assets_pgs(context, region, tag_value, asset_set, csp_account_name)
    else:
        # otherwise, delete what we can and we'll start over
        delete_standard_assets(context, aws, asset_set)
        asset_set = None

    return asset_set


def create_ec2_and_ebs(
    aws: AWS, ec2_count: int = 0, ebs_count: int = 0, key_pair_name: str = ""
) -> tuple[list, list, str]:
    """Create a number of EC2 Instances and/or EBS Volumes

    Args:
        aws (AWS): AWS Account object
        ec2_count (int, optional): The number of EC2 Instances to create. Defaults to 0.
        ebs_count (int, optional): The number of EBS Volumes to create. Defaults to 0.
        key_pair_name (str, optional): A key pair name for the EC2 Instances. Defaults to "".

    Returns:
        tuple[list, list, str]: A list each of the AWS EC2 Instances and EBS Volumes created, and the key pair name used
    """
    ec2_list = []
    ebs_list = []

    if ebs_count:
        logger.info(f"Creating {ebs_count} EBS Volumes in {aws.region_name}")

        for _ in range(ebs_count):
            aws_ebs = aws.ebs.create_ebs_volume(
                availability_zone=aws.ec2.get_availability_zone(),
                size=1,
                volume_type=EBSVolumeType.GP2.value,
            )
            logger.info(f"Created EBS volume {aws_ebs.id}")
            ebs_list.append(aws_ebs)
        logger.info(f"Created {ebs_count} EBS Volumes {ebs_list}")

    if ec2_count:
        logger.info(f"Creating {ec2_count} EC2 Instances in {aws.region_name}")

        key_pair_name = key_pair_name if key_pair_name else f"key_pair_{str(uuid.uuid4())}"
        logger.info(f"Creating Key Pair {key_pair_name}")

        # generate key_pair on the AWS account, if necessary
        created_key_pair = CommonSteps.validate_key_pair(
            aws=aws,
            key_pair_name=key_pair_name,
        )
        logger.info(f"key_pair created: {created_key_pair}")

        ec2_list = aws.ec2.create_ec2_instance(
            key_name=key_pair_name,
            image_id=random_ami_chooser(aws),
            availability_zone=aws.ec2.get_availability_zone(),
            max_count=ec2_count,
        )
        logger.info(f"EC2 instances created {ec2_list}")

    return ec2_list, ebs_list, key_pair_name


def validate_ami_image(aws: AWS, ami_id: str, ami_description: str) -> str:
    """This function will check the AWS provided for the AMI ID availability.  If found, the AMI ID is returned.
    If not found, then the AMI Image Description is used to find all AMIs by that description.
    The AMI Image with the most recent "CreationDate" will have its AMI ID returned.

    A logger.warning() will be output to note an update is required.  Likely "windows_ami".

    Args:
        context (Context): The test context object
        ami_id (str): The AMI ID
        ami_description (str): The full case-sensitive AMI Image Description

    Returns:
        str: AMI ID available from AWS
    """
    logger.info(f"Looking for AMI ID: {ami_id}")
    # if the AMI ID is found, we're good
    if aws.ec2.check_ami_exists(ami_id=ami_id):
        logger.info(f"AMI ID: {ami_id} found")
        return ami_id

    # otherwise, look for a viable AMI ID using description
    logger.warning(f"AMI ID: {ami_id} was not available in AWS.  Searching for updated: {ami_description}")
    new_ami_id = aws.ec2.get_ami_by_description(ami_description=ami_description)
    logger.warning(f"!! Updated AMI ID: {new_ami_id} for Region: {aws.region_name} !!")
    return new_ami_id
