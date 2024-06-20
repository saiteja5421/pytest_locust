import logging
import os
from typing import Any, List, Callable

import boto3
import botocore.exceptions as BotoException
import requests
from botocore.exceptions import ClientError
from waiting import wait, TimeoutExpired

from lib.common.enums.cvsa import CloudProvider, CloudRegions
from lib.common.enums.ec2_type import Ec2Type
from lib.platform.aws_boto3.client_config import ClientConfig
from lib.platform.aws_boto3.models.address import Address
from lib.platform.aws_boto3.models.instance import Tag, Instance
from lib.platform.aws_boto3.models.security_group import SecurityGroup
from lib.platform.cloud.cloud_dataclasses import CloudInstance, CloudDisk, CloudImage, CloudInstanceState, CloudSubnet
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from utils.size_conversion import gib_to_bytes
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


class EC2Manager(CloudVmManager):
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def ec2_resource(self):
        return self.get_session().resource("ec2", endpoint_url=self.endpoint_url, config=self.client_config)

    @property
    def ec2_client(self):
        return self.get_session().client("ec2", endpoint_url=self.endpoint_url, config=self.client_config)

    def name(self) -> CloudProvider:
        return CloudProvider.AWS

    def _get_disk_dataclass(self, ec2_volume: "ec2.Volume") -> CloudDisk:
        cloud_disk = CloudDisk(
            name=ec2_volume.volume_id, disk_size_bytes=gib_to_bytes(ec2_volume.size), tags=ec2_volume.tags
        )
        if ec2_volume.attachments:
            attachment = ec2_volume.attachments[0]
            cloud_disk.instance_id = attachment.get("InstanceId")
            cloud_disk.device = attachment.get("Device")
            cloud_disk.state = attachment.get("State")
        return cloud_disk

    def _get_image_dataclass(self, instance_image=None, ami: dict = None) -> CloudImage:
        if ami:
            instance_image = self.get_ami_by_id(ami["ImageId"])
        return CloudImage(
            id=instance_image.id,
            tags=[] if not hasattr(instance_image, "tags") else instance_image.tags,
            name="" if not hasattr(instance_image, "name") else instance_image.name,
        )

    def _get_subnet_dataclass(self, instance_id: str) -> list[CloudSubnet]:
        subnets = self.get_instance_subnets(instance_id)
        subnets_list = [CloudSubnet(tags=subnet.tags, id=subnet.id) for subnet in subnets]
        return subnets_list

    def get_os_disk(self, ec2_disks: list["ec2.Volume"]) -> CloudDisk:
        os_disk = next(filter(lambda volume: volume.attachments[0]["Device"] == "/dev/sda1", ec2_disks), None)
        return self._get_disk_dataclass(os_disk) if os_disk else None

    def get_data_disks(self, ec2_disks: list["ec2.Volume"]) -> list[CloudDisk]:
        data_disks = [volume for volume in ec2_disks if volume.attachments[0]["Device"] != "/dev/sda1"]
        return [self._get_disk_dataclass(disk) for disk in data_disks]

    def _get_instance_dataclass(self, ec2_instance: "ec2.Instance") -> CloudInstance:
        disks = self.get_ebs_volumes_attached_to_instance(ec2_instance.id)
        return CloudInstance(
            id=ec2_instance.id,
            instance_type=ec2_instance.instance_type,
            location=ec2_instance.placement["AvailabilityZone"][:-1],
            state=CloudInstanceState(ec2_instance.state["Name"]),
            tags=self.get_instance_tags(ec2_instance.id),
            launch_time=ec2_instance.launch_time,
            image=self._get_image_dataclass(instance_image=ec2_instance.image),
            public_ip=ec2_instance.public_ip_address,
            private_ip=ec2_instance.private_ip_address,
            subnets=self._get_subnet_dataclass(ec2_instance.id),
            cloud_provider=CloudProvider.AWS,
            data_disks=self.get_data_disks(disks),
            os_disk=self.get_os_disk(disks),
        )

    def get_instance(self, instance_id: str) -> CloudInstance:
        instance = self.get_ec2_instance_by_id(ec2_instance_id=instance_id)
        cloud_object = self._get_instance_dataclass(instance)
        return cloud_object

    def list_instances(
        self, states: List[CloudInstanceState] = None, tags: List[Tag] = None, location: str = None
    ) -> List[CloudInstance]:
        """list instances by tags or state"""
        if tags:
            instances = self.list_instances_by_tags(tags)
        else:
            instances = self.ec2_resource.instances.all()
        instances = [self._get_instance_dataclass(instance) for instance in instances]
        if states:
            instances = [instance for instance in instances if instance.state in states]
        if location:
            instances = [instance for instance in instances if instance.location == location]
        if not instances:
            logging.info("No instances found with given parameters")
            instances = []
        return instances

    def list_images(self) -> List[CloudImage]:
        amis = self.get_all_amis()["Images"]
        images_list = []
        for ami in amis:
            images_list.append(self._get_image_dataclass(ami=ami))
        return images_list

    def get_disk(self, disk_id: str) -> CloudDisk | None:
        try:
            ec2_volume = self.ec2_resource.Volume(disk_id)
            return self._get_disk_dataclass(ec2_volume=ec2_volume)
        except ClientError as error:
            if "InvalidVolume.NotFound" in str(error):
                logger.info(f"Volume {disk_id} not found")
                return None
            else:
                raise error

    def create_instance(
        self,
        image_id: str,
        tags: list[Tag],
        subnet_tag: Tag = "",
        instance_type: str = "t2.micro",
        location: CloudRegions = None,
    ) -> CloudInstance:
        logger.info(f"Create ec2 with ec2_image_id: {image_id}")
        subnet_id = self.get_subnets_ids_by_tag(tag=subnet_tag)[0]
        tag_spec = []
        if tags:
            tags = [dict(tag) for tag in tags]
            tag_spec = [
                {"ResourceType": "instance", "Tags": tags},
                {"ResourceType": "volume", "Tags": tags},
            ]
        instance_type = self.choose_next_available_instance_type(ec2_instance_type=Ec2Type(instance_type))
        instance = self.ec2_resource.create_instances(
            ImageId=image_id,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            Placement={},
            SubnetId=subnet_id,
            TagSpecifications=tag_spec,
        )
        logger.info(f"Created instance is: {instance}")
        return self._get_instance_dataclass(ec2_instance=instance[0])

    def wait_cloud_instance_status_ok(self, instance_id: str):
        instance = self.ec2_resource.Instance(instance_id)
        self.wait_instance_status_ok(instance)

    def start_instance(self, ec2_instance_id: str) -> None:
        ec2_instance = self.get_ec2_instance_by_id(ec2_instance_id)
        ec2_instance.start()
        logger.info(f"----- Starting EC2 Instance {ec2_instance.instance_id} ------ ")
        ec2_instance.wait_until_running()
        logger.info(f"----- Started EC2 Instance {ec2_instance.instance_id} ------ ")

    def stop_instance(self, ec2_instance_id: str, wait: bool = True) -> None:
        ec2_instance = self.get_ec2_instance_by_id(ec2_instance_id)
        ec2_instance.stop()
        logger.info(f"----- Stopping EC2 Instance {ec2_instance.instance_id} ------ ")
        if wait:
            ec2_instance.wait_until_stopped()
            logger.info(f"----- Stopped EC2 Instance {ec2_instance.instance_id} ------ ")

    def terminate_instance(self, instance_id: str):
        self.terminate_ec2_instance(instance_id)

    def terminate_ec2_instance(self, ec2_instance_id: str, wait: bool = True) -> None:
        ec2_instance = self.get_ec2_instance_by_id(ec2_instance_id)
        ec2_instance.terminate()
        logger.info(f"----- Terminating EC2 Instance {ec2_instance.instance_id} ------ ")
        if wait:
            ec2_instance.wait_until_terminated()
            logger.info(f"----- Terminated EC2 Instance {ec2_instance.instance_id} ------ ")

    def wait_instance_status_ok(self, instance: "ec2.Instance"):
        instance.wait_until_running()
        waiter = self.ec2_client.get_waiter("instance_status_ok")
        logging.info(f"Waiting for {instance.id} to get ok status")
        waiter.wait(InstanceIds=[instance.id], WaiterConfig={"MaxAttempts": 100, "Delay": 30})
        logger.info(f'EC2 instance "{instance.id}" has been started.')

    def get_subnets_ids_by_tag(self, tag: Tag) -> list[str]:
        filters = [{"Name": f"tag:{tag.Key}", "Values": [tag.Value]}]
        subnets = self.ec2_client.describe_subnets(Filters=filters).get("Subnets", [])
        return [subnet["SubnetId"] for subnet in subnets]

    def get_all_instances(self) -> list[Instance]:
        instances = self.ec2_resource.instances.all()
        return [instance for instance in instances]

    def get_availability_zone(self):
        responses = self.ec2_client.describe_availability_zones()
        return list([az for az in responses["AvailabilityZones"] if az["State"] == "available"])[0]["ZoneName"]

    def get_instances_by_tag(self, tag: Tag) -> list[Instance]:
        instances = self.ec2_resource.instances.all()
        return [instance for instance in instances if instance.tags and dict(tag) in instance.tags]

    def get_all_network_interfaces_from_vpc(self, vpc_id):
        logger.info(f"Getting all network interfaces from VPC {vpc_id}")
        return self.ec2_client.describe_network_interfaces(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
            "NetworkInterfaces"
        ]

    def delete_network_interface(self, network_interface_id):
        response = self.ec2_client.delete_network_interface(NetworkInterfaceId=network_interface_id)
        assert (
            response["ResponseMetadata"]["HTTPStatusCode"] == requests.codes.ok
        ), f"Failed to delete network interface {network_interface_id}."

    def list_instances_by_tags(self, tags: list[Tag]) -> list["ec2.Instance"]:
        filters = [dict(tag) for tag in tags]
        matching_instances = []
        for instance in self.ec2_resource.instances.all():
            if all(tag in instance.tags for tag in filters):
                matching_instances.append(instance)
        logging.info(f"Instances with tags {filters} are: {matching_instances}")
        return matching_instances

    def get_running_ec2_instances_by_tag(self, tag: Tag) -> list:
        """It will get list of running instances by tag

        Returns:
            list: running instance list
        """
        instances = self.ec2_resource.instances.filter(
            Filters=[
                {"Name": f"tag:{tag.Key}", "Values": [tag.Value]},
                {"Name": "instance-state-name", "Values": ["running"]},
            ]
        )
        return instances

    def get_running_ec2_instances_contains_tag(self, tag_substring: str) -> list:
        """This function will filter the ec2 instances by searching input tag_substring using 'contains' on 'Key'
            of tagged running ec2 instances

        Args:
            tag_substring (str): substring which has to used in contains filter

        Returns:
            list: list of instance objects satisfying the 'contains' filter criteria
        """
        running_instances = self.ec2_resource.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        tagged_instances = [instance for instance in running_instances if instance.tags]
        instances = []
        for instance in tagged_instances:
            for tag in instance.tags:
                if tag_substring in tag["Key"]:
                    instances.append(instance)
        return instances

    def delete_running_ec2_instances_by_tag(self, tag):
        instances = self.get_running_ec2_instances_by_tag(tag)
        instance_id_list = [instance.id for instance in instances]
        if instance_id_list:
            logger.info(f"Instances to be deleted are {instance_id_list}")
            self.ec2_client.terminate_instances(InstanceIds=instance_id_list)
        else:
            logger.warning(f"Instance id list is empty {instance_id_list}. May be already they are deleted.")

    def delete_running_ec2_instances_contains_tag(self, tag_substring: str):
        """This function will delete the ec2 instances by below steps:
            1. Search input tag_substring using 'contains' on 'Key' on tags of running ec2 instances
            2. Delete ec2 instances returned by step 1.

        Args:
            tag_substring (str): substring which has to used in contains filter
        """
        instances = self.get_running_ec2_instances_contains_tag(tag_substring=tag_substring)
        instance_id_list = [instance.id for instance in instances]
        if instance_id_list:
            logger.debug(f"Instances to be deleted are {instance_id_list}")
            self.ec2_client.terminate_instances(InstanceIds=instance_id_list)
        else:
            logger.warning(f"Instance id list is empty {instance_id_list}. May be instances are already deleted.")

    def get_instance_ip_by_id(self, instance_id: str) -> str:
        instance = self.ec2_resource.Instance(instance_id)
        return instance.public_ip_address

    def get_instance_tags(self, instance_id: str) -> list[Tag]:
        instance_obj = self.ec2_resource.Instance(instance_id)
        return [Tag(**tag) for tag in instance_obj.tags]

    def set_instance_tag(self, instance_id: str, key: str, value: str):
        instance = self.ec2_resource.Instance(instance_id)
        self.create_tags_for_ec2_instance(
            instance,
            [
                Tag(
                    Key=key,
                    Value=value,
                )
            ],
        )

    def create_tags_for_ec2_instance(self, ec2_instance: Any, tags_list: list[Tag]):
        """Create AWS Tags for EC2 Instance
        Args:
            ec2_instance (Any): AWS EC2 Instance object
            tags_list (list[Tag]): List of AWS Tags
        Returns:
            list[Tag]: List of AWS Tags for the EC2 Instance
        """
        tags_dict = [dict(tag) for tag in tags_list]
        tags = ec2_instance.create_tags(Tags=tags_dict)
        logger.info(f" ------ {tags} ----- ")

    def create_tags_to_different_aws_resource_types_by_id(
        self, resource_ids_list: list[str], tags_list: list[Tag]
    ) -> list[Tag]:
        """Set AWS Tags to different AWS Resource Types by AWS Resource IDs
        Can refer to individual AWS type create_tags() if multiple types aren't necessary

        Args:
            resource_ids_list (list[str]): List of AWS Resource IDs, ex: EC2 Instance ID, EBS Volume ID, Subnet ID, VPC ID, etc
            tags_list (list[Tag]): List of AWS Tags
        Returns:
            tags (list[Tag]): List of AWS Tags
        """
        tags_dict = [dict(tag) for tag in tags_list]
        tags = self.ec2_resource.create_tags(Resources=resource_ids_list, Tags=tags_dict)
        logger.info(f" ------ {tags} ----- ")
        return tags

    def remove_tags_from_different_aws_resources_by_id(
        self, aws_resource_id_list: list[str], tags_list: list[Tag]
    ) -> None:
        """Remove Tags from different AWS Resources (including EC2 Instances, EBS Volumes, Subnets, VPCs, etc)
        All AWS Resources use the common AWS boto3 ec2_client.delete_tags()

        Args:
            aws_resource_id_list (list[str]): List of AWS Resource IDs to delete tags
            tags_list (list[Tag]): List of AWS Tags to be deleted
        """
        tags_dict = [dict(tag) for tag in tags_list]
        response = self.ec2_client.delete_tags(Resources=aws_resource_id_list, Tags=tags_dict)
        logger.info(f" ------ {response} ----- ")

    def get_instance_state(self, instance_id) -> str:
        instance = self.ec2_resource.Instance(instance_id)
        return instance.state["Name"]

    def get_ebs_volumes_attached_to_instance(self, instance_id) -> list["ec2.Volume"]:
        instance = self.ec2_resource.Instance(instance_id)
        return [volume for volume in instance.volumes.all()]

    def get_ebs_volumes_id_attached_to_instance(self, instance_id) -> list[str]:
        return [volume.id for volume in self.get_ebs_volumes_attached_to_instance(instance_id)]

    def get_instance_subnets(self, instance_id) -> list:
        instance = self.ec2_resource.Instance(instance_id)
        return [network_interface.subnet for network_interface in instance.network_interfaces]

    # Region EC2
    """
    A Keypair is required to create an EC2 instance
    """

    def create_ec2_key_pair(self, key_name: str) -> str:
        key_pair = self.ec2_resource.create_key_pair(KeyName=key_name)

        logger.info(f"Key Pair = {key_pair.key_material}\nKey ID = {key_pair.key_pair_id}")

        return key_pair

    def get_ec2_key_pair(self, key_name: str):
        key_pair = None
        try:
            key_pair_response = self.ec2_client.describe_key_pairs(KeyNames=[key_name])
            logger.info(f"response: {key_pair_response}")
            key_pair = key_pair_response["KeyPairs"][0]
        except BotoException.ClientError:
            logger.info(f"A key pair by name '{key_name}' does not exist")
        return key_pair

    def get_all_ec2_key_pair(self):
        key_pairs = self.ec2_resource.key_pairs.all()
        return key_pairs

    def get_key_pair(self, key_name: str):
        return self.ec2_resource.KeyPair(key_name)

    def delete_key_pair(self, key_name: str):
        key_pair = self.get_key_pair(key_name=key_name)
        key_pair.delete()

    def get_instance_type_offerings(self):
        """Returns all the instance types present in the active AWS region

        Returns:
            Any: instance type offerings
        """
        instance_types_offerings = self.ec2_client.describe_instance_type_offerings()
        logger.info(
            f"Instance Type Offerings in region {self.get_session().region_name} are {instance_types_offerings}"
        )
        return instance_types_offerings

    def is_instance_type_available(self, ec2_instance_type: Ec2Type) -> bool:
        """
        Checks if the specified instance type is present in the active AWS region.

        Args:
            ec2_instance_type (Ec2Type): instance type for an EC2 instance

        Returns:
            bool: True if the specified instance type is present else False
        """
        instance_types_offerings = self.get_instance_type_offerings()
        instance_types = instance_types_offerings["InstanceTypeOfferings"]

        logger.info(f"Checking if provided instance type {ec2_instance_type} is present or not")
        instance_type = next(
            (
                instance_type
                for instance_type in instance_types
                if instance_type["InstanceType"] == ec2_instance_type.value
            ),
            None,
        )

        logger.info(f"Instance Type = {instance_type}")

        return instance_type is not None

    def choose_next_available_instance_type(self, ec2_instance_type: Ec2Type) -> str:
        """
        Checks if the specified instance type is present in the active AWS region.
        Returns the next available instance type from a list of instance types for the specified AWS region
        if the specified instance is not present

        Args:
            ec2_instance_type (Ec2Type): instance type for an EC2 instance

        Returns:
            str: instance_type
        """
        instance_type: str = None

        if self.is_instance_type_available(ec2_instance_type=ec2_instance_type):
            logger.info(
                f"Instance Type available in region {self.get_session().region_name} is {ec2_instance_type.value}"
            )
            return ec2_instance_type.value
        else:
            # ascending order of free-tier, vCPUs and Mem (GiB)
            instance_type_list = [
                "t2.micro",  # free-tier
                "t3.micro",  # free-tier
                "t2.nano",
                "t2.small",
                "t3.nano",
                "t3.small",
                "t4g.nano",
                "t4g.micro",
                "t4g.small",
                "t4g.small",
                "m5a.large",
                "m6a.large",
                "m7g.medium",
                "a1.medium",
                "c5.large",
                "m6g.medium",
                "c6g.medium",
                "r6g.medium",
                "r7g.medium",
            ]

            for instance_type in instance_type_list:
                if self.is_instance_type_available(ec2_instance_type=Ec2Type(instance_type)):
                    logger.info(
                        f"Instance Type available in region {self.get_session().region_name} is {instance_type}"
                    )
                    return instance_type

        return instance_type

    """
    "ami-04505e74c0741db8d" Id for Ubuntu (Free) - US East Region
    security_groups is list of [security_groups]
    """

    def get_ssm_agent_user_data(self, image_id: str) -> str:
        ami = self.get_ami_by_id(ami_id=image_id)
        rpm_groups = {
            "rpm_group_one": ["Amazon 2023", "Amazon 2", "RHEL 7", "CentOS 7"],
            "rpm_group_two": ["RHEL 8.4", "RHEL 9", "CentOS 8"],
            "rpm_group_three": ["Amazon Linux", "CentOS 6"],
            "rpm_group_four": ["SUSE 15", "SUSE 12"],
            "deb_group_one": ["Ubuntu 22.04", "Ubuntu 16", "Debian 11", "Debian 8", "Debian 9"],
            "deb_group_two": ["Ubuntu 14"],
        }
        user_data_script: str = ""
        for group in rpm_groups.keys():
            for distro_name in rpm_groups.get(group):
                slice_1, slice_2 = distro_name.split()
                if ((slice_1 in ami.name) or (slice_1 in ami.description)) and (
                    (slice_2 in ami.name) or (slice_2 in ami.description)
                ):
                    # Reading user data from the shell script
                    if not os.getcwd().endswith("Medusa"):
                        script = os.path.join(os.getcwd(), f"Medusa/scripts/atlantia/bash/ssm_agents/{group}.sh")
                    else:
                        script = os.path.join(os.getcwd(), f"scripts/atlantia/bash/ssm_agents/{group}.sh")
                    with open(script, "r") as script_file:
                        user_data_script = script_file.read()
                        return user_data_script
        return user_data_script

    def create_ec2_instance(
        self,
        image_id: str,
        key_name: str = "",
        availability_zone: str = "",
        tags: list[Tag] = [],
        resource_type: str = "instance",
        security_groups: list[str] = ["default"],
        min_count: int = 1,
        max_count: int = 1,
        instance_type: str = "t2.micro",
        subnet_id: str = "",
        security_group_ids: list = [],
        user_data: str = "",
        iam_instance_profile: dict = {},
        use_ssm_quick_setup_iam_profile: bool = False,
    ):
        logger.info(
            f"Create ec2 with ebs attached security groups: {security_groups}, ec2_image_id: {image_id}, \
            availability_zone: {availability_zone}, ec2_key_name: {key_name}"
        )
        instances: Any

        local_stack: bool = True if os.getenv("LOCALSTACK_URL") else False

        if not user_data and not local_stack:
            user_data = self.get_ssm_agent_user_data(image_id=image_id)
        tag_spec = []
        if tags:
            tags_list = [dict(tag) for tag in tags]
            tag_spec = [
                {"ResourceType": resource_type, "Tags": tags_list},
                {"ResourceType": "volume", "Tags": tags_list},
            ]

        if subnet_id:
            security_groups = []
        else:
            security_group_ids = []

        placement = {"AvailabilityZone": availability_zone} if availability_zone else {}

        instance_type = self.choose_next_available_instance_type(ec2_instance_type=Ec2Type(instance_type))
        iam_instance_profile = (
            {"Name": "AmazonSSMRoleForInstancesQuickSetup"} if use_ssm_quick_setup_iam_profile else iam_instance_profile
        )
        instances = self.ec2_resource.create_instances(
            KeyName=key_name,
            ImageId=image_id,
            MinCount=min_count,
            MaxCount=max_count,
            InstanceType=instance_type,
            Placement=placement,
            SecurityGroups=security_groups,
            SecurityGroupIds=security_group_ids,
            SubnetId=subnet_id,
            TagSpecifications=tag_spec,
            UserData=user_data,
            IamInstanceProfile=iam_instance_profile,
        )

        logger.info(instances)

        for instance in instances:
            # waiting for instance to start running and pass status checks.
            self.wait_instance_status_ok(instance)

        return [instance for instance in instances]

    def create_custom_config_ec2_instances(
        self,
        key_name: str,
        image_id: str,
        subnet_id: str,
        availability_zone: str = "",
        tags: list[Tag] = [],
        resource_type: str = "instance",
        security_groups: list[str] = ["default"],
        min_count: int = 1,
        max_count: int = 1,
        instance_type: str = Ec2Type.T2_MICRO.value,
        device_index: int = 0,
        associate_public_ip_address: bool = True,
    ):
        instances: Any

        instance_type = self.choose_next_available_instance_type(ec2_instance_type=Ec2Type(instance_type))
        placement = {"AvailabilityZone": availability_zone} if availability_zone else {}

        if not tags:
            instances = self.ec2_resource.create_instances(
                KeyName=key_name,
                ImageId=image_id,
                MinCount=min_count,
                MaxCount=max_count,
                InstanceType=instance_type,
                Placement=placement,
                NetworkInterfaces=[
                    {
                        "SubnetId": subnet_id,
                        "DeviceIndex": device_index,
                        "AssociatePublicIpAddress": associate_public_ip_address,
                        "Groups": security_groups,
                    }
                ],
            )
        else:
            tags_list = [dict(tag) for tag in tags]
            instances = self.ec2_resource.create_instances(
                KeyName=key_name,
                ImageId=image_id,
                MinCount=min_count,
                MaxCount=max_count,
                InstanceType=instance_type,
                Placement=placement,
                NetworkInterfaces=[
                    {
                        "SubnetId": subnet_id,
                        "DeviceIndex": device_index,
                        "AssociatePublicIpAddress": associate_public_ip_address,
                        "Groups": security_groups,
                    }
                ],
                TagSpecifications=[{"ResourceType": resource_type, "Tags": tags_list}],
            )

        logger.info(instances)

        for instance in instances:
            # waiting for instance to start running and pass status checks.
            self.wait_instance_status_ok(instance)

        return [instance for instance in instances]

    def get_ec2_instance_by_id(self, ec2_instance_id: str):
        ec2_instance = self.ec2_resource.Instance(ec2_instance_id)
        return ec2_instance

    def get_instance_metadata_ec2_tags_enabled(self, ec2_instance_id: str) -> bool:
        instance_description = self.ec2_client.describe_instances(InstanceIds=[ec2_instance_id])
        metadata_options = instance_description["Reservations"][0]["Instances"][0]["MetadataOptions"]
        instance_meta_data_tags = metadata_options["InstanceMetadataTags"]
        enabled = True if instance_meta_data_tags == "enabled" else False
        return enabled

    def stop_and_terminate_ec2_instance(self, ec2_instance_id: str, wait: bool = True) -> None:
        self.stop_instance(ec2_instance_id, wait)
        self.terminate_ec2_instance(ec2_instance_id, wait)

    def stop_ec2_instances(self, ec2_instances: list):
        for ec2_instance in ec2_instances:
            self.stop_instance(ec2_instance_id=ec2_instance.id)

    def terminate_ec2_instances(self, ec2_instances: list):
        for ec2_instance in ec2_instances:
            self.terminate_ec2_instance(ec2_instance_id=ec2_instance.id)

    def reboot_ec2_instance(self, ec2_instance_id: str) -> None:
        """
        Method which will reboot ec2 instance and waits 30 times for 5 seconds until instance is in running state.
        args:
        ec2_instance_id - AWS ec2 id
        """
        ec2_instance = self.get_ec2_instance_by_id(ec2_instance_id)
        ec2_instance.reboot()
        logger.info(f"----- Rebooting EC2 Instance {ec2_instance.instance_id} ------ ")
        ec2_instance.wait_until_running()
        logger.info(f"----- Started EC2 Instance {ec2_instance.instance_id} ------ ")

    def get_instances_by_availability_zones(self, availability_zones: list[str]):
        instances = self.ec2_resource.instances.filter(
            Filters=[{"Name": "availability-zone", "Values": availability_zones}]
        )
        return instances

    def get_instance_vpc_id(self, instance_id: str) -> str:
        instance = self.get_ec2_instance_by_id(ec2_instance_id=instance_id)
        vpc_id = instance.vpc_id
        logger.info(f"VPC Id for Instance {instance_id} is {vpc_id}")
        return vpc_id

    def get_instance_security_groups(self, instance_id: str) -> list[SecurityGroup]:
        instance = self.get_ec2_instance_by_id(ec2_instance_id=instance_id)
        security_groups = instance.security_groups
        logger.info(f"Security Groups for Instance {instance_id} are {security_groups}")
        return [SecurityGroup(**sg) for sg in security_groups]

    def create_elastic_ip(self) -> Address:
        allocation = self.ec2_client.allocate_address(Domain="vpc")
        logger.info(f"Elastic IP = {allocation}")
        return Address(**allocation)

    def get_elastic_ips(self):
        filters = [{"Name": "domain", "Values": ["vpc"]}]
        response = self.ec2_client.describe_addresses(Filters=filters)
        logger.info(response)
        return response

    def get_all_allocation_address(self) -> list[Address]:
        allocations = self.get_elastic_ips()
        addresses = allocations["Addresses"]
        return [Address(**address) for address in addresses]

    def get_number_of_elastic_ips(self) -> int:
        addresses = self.get_all_allocation_address()
        return len(addresses)

    def associate_elastic_ip_to_instance(
        self, allocation_id: str, ec2_instance_id: str, allow_reassociation: bool = True
    ):
        response = self.ec2_client.associate_address(
            AllocationId=allocation_id,
            InstanceId=ec2_instance_id,
            AllowReassociation=allow_reassociation,
        )
        logger.info(response)

    """
    Only one of association_id and public_ip is required
    """

    def disassociate_elastic_ip(self, association_id: str, public_ip: str = ""):
        if association_id:
            logger.info(f"===== Disassociating Elastic IP ===== \n Association Id = {association_id}")
            return self.ec2_client.disassociate_address(AssociationId=association_id)
        else:
            logger.info(f"===== Disassociating Elastic IP ===== \n PublicIp = {public_ip}")
            return self.ec2_client.disassociate_address(PublicIp=public_ip)

    def release_elastic_ip(self, allocation_id):
        logger.info(f"Releasing IP with allocation ID: {allocation_id}")
        response = self.ec2_client.release_address(AllocationId=allocation_id)
        try:
            wait(
                lambda: self.ec2_client.describe_addresses(AllocationIds=[allocation_id]) is False,
                timeout_seconds=60,
                sleep_seconds=(0.1, 10),
            )
        except ClientError as error:
            if "InvalidAllocationID.NotFound" in str(error):
                logger.info("IP not found or released with success.")
            else:
                raise ClientError
        logger.info(response)

    def release_all_elastic_ips(self):
        """
        Release all elastic IPs and verify if all IPs are released
        """
        assigned_ips = self.ec2_client.describe_addresses()["Addresses"]
        for ip in assigned_ips:
            logger.info(f"Releasing IP {ip}")
            try:
                self.release_elastic_ip(ip["AllocationId"])
            except ClientError as error:
                if "InvalidAllocationID.NotFound" in str(error):
                    logger.warning(
                        f"IP with allocation ID {ip['AllocationId']} does not exist anymore. Skipping deletion..."
                    )
                else:
                    raise error
        assigned_ips_after_deletion = self.ec2_client.describe_addresses()["Addresses"]
        assert (
            not assigned_ips_after_deletion
        ), f"Some IPs are not released after release action. IP list {assigned_ips_after_deletion}"

    """
    Only one of association_id and public_ip is required
    """

    def disassociate_and_release_elastic_ip(self, association_id: str, allocation_id: str, public_ip: str = ""):
        self.disassociate_elastic_ip(association_id=association_id, public_ip=public_ip)
        self.release_elastic_ip(allocation_id=allocation_id)

    def get_all_amis(self, owners=["self"], filters=[]) -> dict:
        images = self.ec2_client.describe_images(Owners=owners, Filters=filters, IncludeDeprecated=False)
        return images

    def verify_free_instance_types(self, instance_types=[Ec2Type.T2_MICRO.value]):
        logger.info(f"Find ami {instance_types} in region")
        response = self.ec2_client.describe_instance_types(
            InstanceTypes=instance_types, Filters=[{"Name": "free-tier-eligible", "Values": ["true"]}]
        )
        try:
            assert response["InstanceTypes"][0]["InstanceType"]
            return True
        except Exception as e:
            logger.error(f"No Free Instance type {instance_types} found.\n{e}")
            return False

    def delete_ami(self, image_id):
        status = self.ec2_client.deregister_image(ImageId=image_id)
        assert status["ResponseMetadata"]["HTTPStatusCode"] == 200, f"AMI was not deleted {image_id}"

    def delete_all_amis(self):
        images = self.get_all_amis()
        for image in images["Images"]:
            self.delete_ami(image["ImageId"])

    def modify_ec2_security_groups(self, instance_id: str, security_groups: list):
        self.ec2_client.modify_instance_attribute(InstanceId=instance_id, Groups=security_groups)

    def get_ec2_password_data(self, ec2_instance_id):
        response = self.ec2_client.get_password_data(InstanceId=ec2_instance_id)
        return response["PasswordData"]

    def associate_iam_profile(self, aws_account_id: str, instance_id: str, arn: str, name: str):
        response = self.ec2_client.associate_iam_instance_profile(
            IamInstanceProfile={
                "Arn": f"arn:aws:iam::{aws_account_id}:instance-profile/{arn}",
                "Name": name,
            },
            InstanceId=instance_id,
        )
        logger.info(f"""Associated ["Arn": {arn}, "Name": {name}] to Instance {instance_id}""")
        logger.info(response)
        return response

    def get_ami_by_id(self, ami_id: str):
        ami = self.ec2_resource.Image(ami_id)
        logger.info(f"AMI with ID {ami_id} is {ami}")
        return ami

    def create_ec2_image(self, instance_id: str, image_name: str, no_reboot: bool = True):
        """Create an Image for the given EC2

        Args:
            instance_id (str): The Instance ID for which to take an image
            no_reboot (bool, optional): Reboot is required. Defaults to "True"
        Returns:
            new_image: The new image data: CreateImageResponse
        """
        logger.info(f"Taking image of instance_id: {instance_id}")
        new_image = self.ec2_client.create_image(
            InstanceId=instance_id,
            Description=f"Created from Source: {instance_id}",
            Name=image_name,
            NoReboot=no_reboot,
        )
        logger.info(f"Image creation started: {new_image}")
        # wait until image is in available state
        waiter = self.ec2_client.get_waiter("image_available")
        waiter.wait(ImageIds=[new_image["ImageId"]])
        return new_image

    def wait_for_public_dns(self, ec2_instance_id: str) -> str:
        try:
            public_dns = wait(
                lambda: self.get_ec2_instance_by_id(ec2_instance_id).public_dns_name,
                timeout_seconds=TimeoutManager.health_status_timeout,
                sleep_seconds=15,
            )
            logger.info(f"Ec2 {ec2_instance_id} has public dns: {public_dns}")
            return public_dns
        except TimeoutExpired as e:
            logger.error(f"Ec2 does not have assigned dns: {e}")
            raise e

    def get_ami_by_ami_name(self, ami_name: str):
        """Returns AMI object with given ami_name if found else returns None

        Args:
            ami_name (str): Name of the AMI
            # NOTE: AMI name is unique within a region

        Returns:
            _type_: AMI 'resource' object if found else None
        """
        amis = self.ec2_resource.images.filter(
            Owners=["self"],
            Filters=[
                {
                    "Name": "name",
                    "Values": [ami_name],
                },
            ],
        )
        logger.info(f"Images = {amis}")

        if list(amis):
            logger.info(f"AMI with name {ami_name} is {list(amis)[0]}")
            return list(amis)[0]
        else:
            logger.warning(f"AMI not found with name {ami_name}")
            return None

    def get_ami_by_name(self, name: str):
        """Returns AMI object with given name if found else returns None

        Args:
            name (str): Name given to the AMI (e.g. "my_ami")

        Returns:
            _type_: AMI 'resource' object if found else None
        """
        amis = self.ec2_resource.images.filter(
            Owners=["self"],
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": [name],
                },
            ],
        )
        logger.info(f"Images = {amis}")

        if list(amis):
            logger.info(f"AMI with name {name} is {list(amis)[0]}")
            return list(amis)[0]
        else:
            logger.warning(f"AMI not found with name {name}")
            return None

    def get_ami_by_tag(self, tag: Tag):
        """Returns AMI object with given tag if found else returns None
        Args:
            tag (Tag): Tag assigned to an AMI
        Returns:
            _type_: AMI 'resource' object if found else None
        """
        amis = self.ec2_resource.images.filter(
            Owners=["self"],
            Filters=[
                {
                    "Name": f"tag:{tag.Key}",
                    "Values": [tag.Value],
                },
            ],
        )
        logger.info(f"Images = {amis}")

        if amis:
            found_amis = [ami for ami in amis]
            logger.info(f"AMIs with Tag {tag} are {found_amis}")
            return found_amis
        else:
            logger.info(f"AMIs with Tag {tag} not found")
            return None

    def set_ami_tags(self, ami_id: str, tags_list: list[Tag]):
        ami = self.get_ami_by_id(ami_id=ami_id)
        logger.info(f"AMI = {ami}")

        tags_dict = [dict(tag) for tag in tags_list]
        tags = ami.create_tags(Tags=tags_dict)
        logger.info(f" ------ {tags} ----- ")

    def filter_ec2_images_by_tag(self, tag_name: str, tag_values: list[str]):
        images = self.ec2_resource.images.filter(Filters=[{"Name": f"tag:{tag_name}", "Values": tag_values}])
        logger.info(f'\namis with Tag "Name={tag_values}":')

        for image in images:
            logger.info(f"- AMI ID: {image.id}")

        return images

    def get_all_snapshots_from_account(self, account_id):
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=[account_id])["Snapshots"]
        return snapshots

    def delete_all_snapshots_from_account(self, account_id):
        """Deletes all snapshots from specified AWS account
        Args:
            account_id (str): AWS account ID
        """
        logger.info(f"Deleting all snapshots from account {account_id}")
        snapshots = self.get_all_snapshots_from_account(account_id)
        for snapshot in snapshots:
            logger.info(f"Deleting snapshot with ID: {snapshot['SnapshotId']}")
            self.ec2_client.delete_snapshot(SnapshotId=snapshot["SnapshotId"])
        snapshots_after_deletion = self.get_all_snapshots_from_account(account_id)
        assert not snapshots_after_deletion, f"Not all snapshots are deleted. Snapshots {snapshots_after_deletion}"

    def get_all_volumes(self, filter_name=None, filter_values=None):
        """Get all volumes from AWS

        Returns:
            list: List of volume objects
        """
        if filter_name and filter_values:
            volumes = self.ec2_client.describe_volumes(Filters=[{"Name": filter_name, "Values": filter_values}])[
                "Volumes"
            ]
        else:
            volumes = self.ec2_client.describe_volumes()["Volumes"]
        return volumes

    def delete_all_volumes(self):
        """Delete all volumes in available state and verify if there are any volumes after deletion"""
        logger.info("Deleting all volumes...")
        volumes = self.get_all_volumes(filter_name="status", filter_values=["available"])
        for volume in volumes:
            logger.info(f"Deleting volume with ID {volume['VolumeId']}")
            self.ec2_client.delete_volume(VolumeId=volume["VolumeId"])
        volumes_after_deletion = self.get_all_volumes(filter_name="status", filter_values=["available"])
        if volumes_after_deletion:
            assert all(
                [volume["State"] == "deleting" for volume in volumes_after_deletion]
            ), f"Found some volumes not in deleting state after volume cleanup: {volumes_after_deletion}"
        else:
            assert not volumes_after_deletion, f"Not all volumes are deleted. Volumes: {volumes_after_deletion}"

    def check_ami_exists(self, ami_id: str) -> bool:
        """Check if an AMI is available in AWS

        Args:
            ami_id (str): The AMI ID to validate

        Returns:
            bool: True if the AMI ID is found in AWS, False otherwise
        """
        try:
            response = self.ec2_client.describe_images(ImageIds=[ami_id])
            for image in response["Images"]:
                if ami_id == image["ImageId"]:
                    return True
            return False
        except ClientError as e:
            logger.info(f"AMI: {ami_id} does not exist")
            return False

    def get_ami_by_description(self, ami_description: str) -> str:
        """Get by "description" the most recent AMI by "CreationDate".
           AMI Image CreationDate is in the form: 2023-07-12T05:46:36.000Z

        Args:
            ami_description (str): The case-sensitive "Description" for the AMI to get

        Returns:
            str: The AMI ID of the most recent AMI Image, using "CreationDate"
        """
        response = self.ec2_client.describe_images(
            Filters=[
                {"Name": "description", "Values": [ami_description]},
            ]
        )
        # There will likely be more than 1 image returned.  We will take the largest value for "CreationDate".
        final_image = None
        for image in response["Images"]:
            if not final_image or (final_image and image["CreationDate"] > final_image["CreationDate"]):
                final_image = image

        # we should have a 'final_image'
        assert final_image, f"There were no AMIs returned using Description: {ami_description}"

        logger.info(f"Returning AMI image: {final_image}")
        return final_image["ImageId"]

    def get_ntp_server_address(self) -> str:
        return "169.254.169.123"
