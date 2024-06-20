"""
This module contains functions related to the creation and deletion of Standard EC2 and EBS Assets used for tests
"""

import json
import os
import logging
import random
from common.enums.os import OS
from lib.platform.aws.aws_factory import AWS

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

        # logger.info(f"Random choice from 10 newest amis: {amis_sorted}")
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
