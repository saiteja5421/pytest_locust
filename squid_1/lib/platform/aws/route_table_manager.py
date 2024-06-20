import logging
from typing import Callable

import boto3

from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class RouteTableManager:
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

    def get_all_route_tables(self):
        route_tables = self.ec2_resource.route_tables.all()
        return [route_table for route_table in route_tables]

    def create_route_table(self, vpc_id: str, dry_run: bool = False):
        logger.info(f" ----- Creating Route Table with VPC {vpc_id} ----- ")
        route_table = self.ec2_resource.create_route_table(DryRun=dry_run, VpcId=vpc_id)
        logger.info(f" ----- Route Table Created {route_table.id} ----- ")
        return route_table

    def delete_route_table(self, route_table_id: str, dry_run: bool = False):
        logger.info(f" ----- Deleting Route Table {route_table_id} ----- ")
        self.ec2_client.delete_route_table(DryRun=dry_run, RouteTableId=route_table_id)
        logger.info(f" ----- Route Table Deleted {route_table_id} ----- ")

    def associate_route_table(
        self, route_table_id: str, subnet_id: str = "", internet_gateway_id: str = "", dry_run: bool = False
    ):
        """
        NOTE: The parameter SubnetId cannot be used with the parameter GatewayId. Can only associate 1 at a time
        """
        logger.info(f"Check input for subnet_id {subnet_id} and internet_gateway_id {internet_gateway_id}")
        assert (subnet_id != "" and internet_gateway_id == "") or (subnet_id == "" and internet_gateway_id != "")

        if subnet_id != "" and internet_gateway_id == "":
            logger.info(f" ----- Associating Route Table {route_table_id} with Subnet {subnet_id} ----- ")
            response = self.ec2_client.associate_route_table(
                DryRun=dry_run,
                RouteTableId=route_table_id,
                SubnetId=subnet_id,
            )
        elif internet_gateway_id != "" and subnet_id == "":
            logger.info(
                f" ----- Associating Route Table {route_table_id} with Internet Gateway {internet_gateway_id} ----- "
            )
            response = self.ec2_client.associate_route_table(
                DryRun=dry_run, RouteTableId=route_table_id, GatewayId=internet_gateway_id
            )
        logger.info(f" ----- Route Table {route_table_id} was Associated {response['AssociationId']} ----- ")
        return response["AssociationId"]

    def disassociate_route_table(self, route_table_association_id: str, dry_run: bool = False):
        logger.info(f" ----- Disassociating Route Table {route_table_association_id} ----- ")
        self.ec2_client.disassociate_route_table(AssociationId=route_table_association_id, DryRun=dry_run)
        logger.info(f" ----- Route Table Disassociated {route_table_association_id} ----- ")

    def create_route(
        self, destination_cidr_block: str, internet_gateway_id: str, route_table_id: str, dry_run: bool = False
    ):
        """
        internet_gateway_id is the Internet Gateway ID that is attached to the VPC
        """
        logger.info(
            f" ----- Creating Route in Route Table {route_table_id} with Destination CIDR Block {destination_cidr_block} and Internet Gateway {internet_gateway_id} ----- "
        )
        response = self.ec2_client.create_route(
            DestinationCidrBlock=destination_cidr_block,
            DryRun=dry_run,
            GatewayId=internet_gateway_id,
            RouteTableId=route_table_id,
        )
        logger.info(
            f" ----- Route {destination_cidr_block} Created in {route_table_id}, Internet Gateway {internet_gateway_id} ----- "
        )
        return response

    def delete_route(self, destination_cidr_block: str, route_table_id: str, dry_run: bool = False):
        logger.info(
            f" ----- Deleting Route in Route Table {route_table_id} with Destination CIDR Block {destination_cidr_block} ----- "
        )
        self.ec2_client.delete_route(
            DestinationCidrBlock=destination_cidr_block, DryRun=dry_run, RouteTableId=route_table_id
        )
        logger.info(f" ----- Route Deleted {destination_cidr_block} from {route_table_id} ----- ")

    def get_all_route_tables_in_vpc(self, vpc_id):
        route_tables = self.ec2_resource.Vpc(vpc_id).route_tables.all()
        return route_tables

    def delete_all_route_tables_in_vpc(self, vpc_id):
        """Delete all route tables in provided VPC and verify if resources are deleted.
        Default route table deletion is skipped. Default VPC resources cannot be deleted without deleting VPC.

        Args:
            vpc_id (str): VPC ID from which route tables are deleted
        """
        route_tables = self.get_all_route_tables_in_vpc(vpc_id)
        for rtb in route_tables:
            if rtb.associations_attribute and rtb.associations_attribute[0]["Main"] == True:
                logger.info(rtb.id + " is the main route table, continue...")
                continue
            logger.info(f"Removing route table: {rtb.id}")
            table = self.ec2_resource.RouteTable(rtb.id)
            table.delete()
        route_tables_after_deletion = [rt for rt in self.get_all_route_tables_in_vpc(vpc_id)]
        assert (
            len(route_tables_after_deletion) <= 1
        ), f"Some route tables last after deletion. RTBs {route_tables_after_deletion}"
