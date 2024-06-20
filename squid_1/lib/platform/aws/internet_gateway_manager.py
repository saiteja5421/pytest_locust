import logging
from typing import Callable

import boto3
from tenacity import retry
from tenacity import stop_after_delay, wait_fixed

from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class InternetGatewayManager:
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

    def get_all_internet_gateways(self):
        internet_gateways = self.ec2_resource.internet_gateways.all()
        return [internet_gateway for internet_gateway in internet_gateways]

    def get_all_internet_gateways_in_vpc(self, vpc_id):
        internet_gateways = self.ec2_resource.Vpc(vpc_id).internet_gateways.all()
        return internet_gateways

    def create_internet_gateway(self):
        logger.info(f" ----- Creating Internet Gateway ----- ")
        internet_gateway = self.ec2_resource.create_internet_gateway()
        waiter = self.ec2_client.get_waiter("internet_gateway_exists")
        waiter.wait(InternetGatewayIds=[internet_gateway.id])  # internet_gateway.wait_until_available()
        logger.info(f" ----- Internet Gateway Created {internet_gateway} ----- ")
        return internet_gateway

    def delete_internet_gateway(self, internet_gateway_id: str, dry_run: bool = False):
        logger.info(f" ----- Deleting Internet Gateway {internet_gateway_id} ----- ")
        response = self.ec2_client.delete_internet_gateway(DryRun=dry_run, InternetGatewayId=internet_gateway_id)
        logger.info(f" ----- Internet Gateway Deleted {internet_gateway_id} ----- ")
        return response

    def attach_internet_gateway(self, internet_gateway_id: str, vpc_id: str, dry_run: bool = False):
        logger.info(f" ----- Attaching Internet Gateway {internet_gateway_id} to VPC {vpc_id} ----- ")
        response = self.ec2_client.attach_internet_gateway(
            DryRun=dry_run, InternetGatewayId=internet_gateway_id, VpcId=vpc_id
        )
        logger.info(f" ----- Internet Gateway attached {internet_gateway_id}, VPC {vpc_id} ----- ")
        return response

    def detach_internet_gateway(self, internet_gateway_id: str, vpc_id: str, dry_run: bool = False):
        logger.info(f" ----- Detaching Internet Gateway {internet_gateway_id} from VPC {vpc_id} ----- ")
        response = self.ec2_client.detach_internet_gateway(
            DryRun=dry_run, InternetGatewayId=internet_gateway_id, VpcId=vpc_id
        )
        logger.info(f" ----- Internet Gateway Detached {internet_gateway_id}, VPC {vpc_id} ----- ")
        return response

    @retry(reraise=True, stop=stop_after_delay(240), wait=wait_fixed(5))
    def detach_and_delete_all_igws_in_vpc(self, vpc_id):
        """Detach and delete all internet gateways associated with VPC and verify if there are any stale entries after deletion
        Args:
            vpc_id (str): VPC ID to delete internet gateways from
        """
        igws = self.get_all_internet_gateways_in_vpc(vpc_id)
        for internet_gateway in igws:
            logger.info(f"Detaching and Removing igw-id: {internet_gateway.id}")
            self.detach_internet_gateway(internet_gateway.id, vpc_id)
            self.delete_internet_gateway(internet_gateway.id)
        igws_after_delete = self.get_all_internet_gateways_in_vpc(vpc_id)
        igws_list_after_delete = [igw for igw in igws_after_delete]
        assert not igws_list_after_delete, f"Some internet gateways last after deletion. IGWS: {igws_after_delete}"
