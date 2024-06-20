import logging
from typing import Callable

import boto3
import botocore

from lib.platform.aws.models.instance import Tag
from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class VPCManager:
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

    # region VPC

    def create_vpc(self, cidr_block: str, instance_tenancy="default"):
        vpc = self.ec2_resource.create_vpc(CidrBlock=cidr_block, InstanceTenancy=instance_tenancy)
        logger.info(f" ----- VPC Creating {vpc} ----- ")
        waiter = self.ec2_client.get_waiter("vpc_available")
        waiter.wait(VpcIds=[vpc.id])  # vpc.wait_until_available()
        logger.info(f" ----- VPC Created {vpc} ----- ")
        return vpc

    def get_vpc_by_id(self, vpc_id: str):
        return self.ec2_resource.Vpc(vpc_id)

    def create_vpc_tags(self, vpc_id: str, tags: list[Tag]):
        """
        Use the Tag object from aws_model to created 'tags' and pass to this method.
        """
        vpc = self.get_vpc_by_id(vpc_id)

        # converting list[Tag] to list[{Tag}]
        tags_list = [dict(tag) for tag in tags]
        vpc.create_tags(Tags=tags_list)

    """Delete / Remove VPC Tags:

    Refer to -> aws.ec2.remove_tags_from_different_aws_resources_by_id()

    Old function: delete_vpc_tags()
    """

    def delete_vpc(self, vpc_id: str) -> None:
        """Delete VPC and check if it's deleted

        Args:
            vpc_id (str): ID of VPC we want to delete
        """
        vpc = self.get_vpc_by_id(vpc_id)
        logger.info(f" ----- Deleting VPC with {vpc_id} ----- ")
        try:
            vpc.delete()
        except botocore.exceptions.ClientError as err:
            if err.response["Error"]["Code"] == "InvalidVpcID.NotFound":
                logger.debug(f"VPC {vpc_id} cannot be deleted because it doesn't exists anymore. Error thrown: {err}")
            else:
                raise err
        logger.info(f" ----- Deleted VPC with {vpc_id} ----- ")
        all_vpcs = self.get_all_vpcs()
        vpc_after_deletion = [vpc.id for vpc in all_vpcs if vpc.id == vpc_id]
        assert not vpc_after_deletion, f"VPC is still not deleted. VPC {vpc_after_deletion}"

    def get_all_vpcs(self):
        return self.ec2_resource.vpcs.all()

    def get_vpc(self, public_dns_support: bool = True):
        vpcs = self.get_all_vpcs()
        if public_dns_support:
            vpc = [vpc for vpc in vpcs if self.get_public_dns_support(vpc.id)][0]
        else:
            vpc = [vpc for vpc in vpcs][0]
        logger.info(f"Fetched VPC {vpc.id}")
        return vpc

    def get_all_subnets(self, vpc):
        return list(vpc.subnets.all())

    def get_all_vpcs_by_ids(self, vpc_ids: str):
        """
        vpc_ids = list of [vpc_ids]
        """
        return self.ec2_resource.vpcs.filter(VpcIds=vpc_ids)

    def get_all_vpcs_by_tags(self, tag_name: str, tag_values: str):
        """
        tag_values = list of [tag_values]
        """
        return self.ec2_resource.vpcs.filter(Filters=[{"Name": f"tag:{tag_name}", "Values": tag_values}])

    def get_public_dns_support(self, vpc_id: str):
        dns_support = self.ec2_client.describe_vpc_attribute(Attribute="enableDnsSupport", VpcId=vpc_id, DryRun=False)
        dns_hostname = self.ec2_client.describe_vpc_attribute(
            Attribute="enableDnsHostnames", VpcId=vpc_id, DryRun=False
        )
        return dns_support["EnableDnsSupport"]["Value"] and dns_hostname["EnableDnsHostnames"]["Value"]


# endregion
