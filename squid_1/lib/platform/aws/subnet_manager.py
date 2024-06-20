import logging
from typing import Callable

import boto3

from lib.platform.aws.models.instance import Tag
from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class SubnetManager:
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

    # region Subnet

    def create_subnet(self, availability_zone: str, cidr_block: str, vpc_id: str):
        subnet = self.ec2_resource.create_subnet(AvailabilityZone=availability_zone, CidrBlock=cidr_block, VpcId=vpc_id)
        return subnet

    def get_subnet_by_id(self, subnet_id: str):
        return self.ec2_resource.Subnet(subnet_id)

    """
    Use the Tag object from aws_model to created 'tags' and pass to this method.
    """

    def create_subnet_tags(self, subnet_id: str, tags: list[Tag]):
        subnet = self.get_subnet_by_id(subnet_id)
        tags_dict = [dict(tag) for tag in tags]
        subnet.create_tags(Tags=tags_dict)

    """Delete / Remove Subnet Tags:

    Refer to -> aws.ec2.remove_tags_from_different_aws_resources_by_id()

    delete_subnet_tags()
    """

    def get_all_subnets(self):
        subnets = self.ec2_resource.subnets.all()
        return [subnet for subnet in subnets]

    """
    subnet_ids = list of [subnet_ids]
    """

    def get_all_subnets_by_ids(self, subnet_ids: list[str]):
        return self.ec2_resource.subnets.filter(SubnetIds=subnet_ids)

    """
    tag_values = list of [tag_values]
    """

    def get_subnets_by_tags(self, tag_name: str, tag_values: list[str]):
        return self.ec2_resource.subnets.filter(Filters=[{"Name": f"tag:{tag_name}", "Values": tag_values}])

    def delete_subnet(self, subnet_id: str) -> None:
        subnet = self.get_subnet_by_id(subnet_id)

        logger.info(f" ------ Deleting Subnet {subnet_id} ----- ")

        subnet.delete()

        logger.info(f" ------ Deleted Subnet {subnet_id} ----- ")

    def get_subnets_in_vpc(self, vpc_id):
        subnets = self.ec2_resource.Vpc(vpc_id).subnets.all()
        return subnets

    def enable_public_ip_for_a_subnet(self, subnet_id: str):
        """Method enables auto assignment of a public ip for a subnet

        Args:
            subnet_id (str): subnet id of the subnet to enable auto public ip assignment.
        """
        self.ec2_client.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True})

    def delete_all_subnets_in_vpc(self, vpc_id):
        """Delete all subnets in VPC and check if resources are deleted

        Args:
            vpc_id (str): VPC ID from which subnets are deleted
        """
        logger.info(f"Deleting all subnets in vpc: {vpc_id}")
        subnets = self.get_subnets_in_vpc(vpc_id)
        for subnet in subnets:
            logger.info(f"Deleting subnet {subnet}")
            subnet.delete()
        subnets_after_deletion_list = [sbn for sbn in self.get_subnets_in_vpc(vpc_id)]
        assert (
            not subnets_after_deletion_list
        ), f"Some subnets last after deletion. Subnets {subnets_after_deletion_list}"


# endregion
