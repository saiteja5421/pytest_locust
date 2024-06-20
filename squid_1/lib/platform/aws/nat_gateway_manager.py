import logging
from typing import Callable

from lib.platform.aws.client_config import ClientConfig

import boto3

logger = logging.getLogger()


class NatGatewayManager:
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

    def delete_nat_gateway(self, nat_gateway_id: str):
        logger.info(f"Deleting NAT Gateway with ID: {nat_gateway_id}")
        self.ec2_client.delete_nat_gateway(NatGatewayId=nat_gateway_id)
        waiter = self.ec2_client.get_waiter("nat_gateway_deleted")
        waiter.wait(NatGatewayIds=[nat_gateway_id], WaiterConfig={"Delay": 10, "MaxAttempts": 30})
        logger.info("Delete NAT Gateway completed.")

    def delete_all_nat_gateways_in_vpc(self, vpc_id):
        """Delete all NAT gateways from provided VPC and verify if all resources are deleted

        Args:
            vpc_id (str): VPC ID to delete NAT gateways from
        """
        logger.info(f"Getting all NAT Gateways from VPC {vpc_id}")
        vpc_nat_gateways = self.ec2_client.describe_nat_gateways(
            Filters=[
                {
                    "Name": "vpc-id",
                    "Values": [
                        vpc_id,
                    ],
                },
            ]
        )
        logger.info(f"Deleting all NAT Gateways from VPC {vpc_id}")
        for nat_gateway in vpc_nat_gateways["NatGateways"]:
            nat_gateway_id = nat_gateway["NatGatewayId"]
            self.delete_nat_gateway(nat_gateway_id)
        vpc_nat_gateways_after_deletion = self.ec2_client.describe_nat_gateways(
            Filters=[
                {
                    "Name": "vpc-id",
                    "Values": [
                        vpc_id,
                    ],
                },
            ]
        )["NatGateways"]
        assert all(
            nat["State"] == "deleted" for nat in vpc_nat_gateways_after_deletion
        ), f"Found some VPC NAT Gateways not in deleted state. NAT Gateways found: {vpc_nat_gateways_after_deletion}"
