import logging as logger
from typing import Callable

import boto3
from botocore.exceptions import ClientError

from lib.platform.aws_boto3.client_config import ClientConfig


class NetworkInterfaceManager:
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

    def get_all_network_interfaces_in_vpc(self, vpc_id):
        network_interfaces = self.ec2_resource.Vpc(vpc_id).network_interfaces.all()
        return network_interfaces

    def detach_network_interface(
        self, network_interface_id: str, network_interface_attachment_id: str, dry_run: bool = False, force: bool = True
    ):
        logger.info(f"Detaching network interface with attachment id: {network_interface_attachment_id}")
        self.ec2_client.detach_network_interface(
            AttachmentId=network_interface_attachment_id, DryRun=dry_run, Force=force
        )
        self.wait_for_interface_detach(network_interface_id)

    def delete_network_interface(self, network_interface_id: str, dry_run: bool = False):
        logger.info(f"Deleting: {network_interface_id}")
        self.ec2_client.delete_network_interface(NetworkInterfaceId=network_interface_id, DryRun=dry_run)
        logger.info(f"Network interface with id: {network_interface_id} deleted.")

    def detach_and_delete_all_network_interfaces_in_vpc(self, vpc_id):
        """Detach and delete all network interfaces in provided VPC and verify if resources are deleted

        Args:
            vpc_id (str): VPC ID from which network interfaces are deleted
        """
        network_interfaces = self.get_all_network_interfaces_in_vpc(vpc_id)
        logger.info("Detaching and Removing network interfaces")
        for network_interface in network_interfaces:
            if network_interface.attachment:
                self.detach_network_interface(network_interface.id, network_interface.attachment["AttachmentId"])
            try:
                self.delete_network_interface(network_interface.id)
            except ClientError as error:
                if "InvalidNetworkInterfaceID.NotFound" in str(error):
                    logger.warning(str(error))
                else:
                    raise error
        network_interfaces_after_deletion = self.get_all_network_interfaces_in_vpc(vpc_id)
        network_interfaces_after_deletion_list = [nic for nic in network_interfaces_after_deletion]
        assert (
            not network_interfaces_after_deletion_list
        ), f"Some network interfaces last after deletion. NICs {network_interfaces_after_deletion_list}"

    def wait_for_interface_detach(self, network_interface_id):
        try:
            self.ec2_client.get_waiter("network_interface_available").wait(NetworkInterfaceIds=[network_interface_id])
            logger.info(f"Network interface with ID {network_interface_id} has beed detached.")
        except Exception as error:
            logger.warning(
                f"Error during network interface detachment. Network interface ID: {network_interface_id}, error message: {error}"
            )
