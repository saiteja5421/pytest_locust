import logging as logger
from typing import Callable

import boto3

from lib.platform.aws.client_config import ClientConfig


class NetworkAccessListManager:
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

    def get_all_access_lists_in_vpc(self, vpc_id):
        nacls = self.ec2_resource.Vpc(vpc_id).network_acls.all()
        return nacls

    def delete_all_access_lists_in_vpc(self, vpc_id):
        """Delete all NACLs (network access list) from provided VPC and verify if resources are deleted

        Args:
            vpc_id (str): VPC ID to delete NACLs from
        """
        nacls = self.get_all_access_lists_in_vpc(vpc_id)
        for nacl in nacls:
            if nacl.is_default:
                logger.info(f"Skipping deletion for default NACL with id: {nacl.id}")
                continue
            logger.info(f"Deleting NACL with id {nacl.id}")
            self.ec2_client.delete_network_acl(NetworkAclId=nacl.id)
        nacls_after_deletion = self.get_all_access_lists_in_vpc(vpc_id)
        assert all(
            [nacl.is_default for nacl in nacls_after_deletion]
        ), f"NACLs not deleted properly. There are some NACLs on the list that are not default. NACLs {nacls_after_deletion}"
