import logging as logger
from typing import Callable

import boto3

from lib.platform.aws_boto3.client_config import ClientConfig


class LoadBalancerManager:
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

    @property
    def elb_client(self):
        return self.get_session().client("elb")

    def get_all_network_balancers_in_vpc(self):
        return self.elb_client.describe_load_balancers(PageSize=10)

    def delete_elb(self, load_balancer_name):
        logger.info(f"Deleting load balancer with ARN: {load_balancer_name}")
        self.elb_client.delete_load_balancer(LoadBalancerName=load_balancer_name)

    def delete_all_elbs(self):
        """Delete all elastic load balancers and verify if there are stale entries after deletion"""
        logger.info("Getting all load balancers...")
        all_elbs = self.get_all_network_balancers_in_vpc()["LoadBalancerDescriptions"]
        for elb in all_elbs:
            self.delete_elb(elb["LoadBalancerName"])
        all_elbs = self.elb_client.describe_load_balancers()["LoadBalancerDescriptions"]
        assert not all_elbs, f"Found load balancers, but should be deleted. ELBs list: {all_elbs}"
        logger.info("Successfuly deleted all load balancers.")
