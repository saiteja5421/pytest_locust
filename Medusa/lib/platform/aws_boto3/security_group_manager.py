import logging
from typing import Callable

import boto3
import botocore.exceptions as BotoException
from lib.platform.aws_boto3.client_config import ClientConfig

logger = logging.getLogger()


class SecurityGroupManager:
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

    def create_security_group(self, description: str, group_name: str, vpc_id: str = ""):
        security_group = self.ec2_resource.create_security_group(
            Description=description, GroupName=group_name, VpcId=vpc_id
        )
        logger.info(security_group)
        return security_group

    def get_security_group_id_by_name(self, security_group_names: list[str]) -> str:
        response = self.describe_security_groups_by_names(security_group_names=security_group_names)
        security_group_id = response["SecurityGroups"][0]["GroupId"]

        logger.info(f"----- Security Group Id is {security_group_id} -----")

        return security_group_id

    def get_security_group_by_id(self, security_group_id: str):
        security_group = self.ec2_resource.SecurityGroup(security_group_id)
        return security_group

    def delete_security_group(self, security_group_id: str) -> None:
        security_group = self.get_security_group_by_id(security_group_id)

        logger.info(f"----- Deleting Security Group {security_group_id} -----")

        security_group.delete()

        logger.info(f"----- Deleted Security Group {security_group_id} -----")

    def get_all_security_groups(self):
        return self.ec2_resource.security_groups.all()

    """
    subnet_ids = list of [security_groups_ids]
    """

    def get_all_security_groups_by_ids(self, security_group_ids: list[str]):
        return self.ec2_resource.security_groups.filter(GroupIds=security_group_ids)

    """
    tag_values = list of [tag_values]
    """

    def get_security_groups_by_tags(self, tag_name: str, tag_values: list[str]):
        return self.ec2_resource.security_groups.filter(Filters=[{"Name": f"tag:{tag_name}", "Values": tag_values}])

    """
    security_group_name = list of [security_group_names]
    """

    def get_security_groups_by_name(self, security_group_names: list[str]):
        response = self.ec2_resource.security_groups.filter(GroupNames=security_group_names)
        logger.info(f"Response: {response}")
        return response

    def describe_security_groups_by_ids(self, security_group_ids: list[str]):
        response = self.ec2_client.describe_security_groups(GroupIds=security_group_ids)
        logger.info(f"Response: {response}")
        return response

    def describe_security_groups_by_names(self, security_group_names: list[str]):
        response = self.ec2_client.describe_security_groups(
            Filters=[dict(Name="group-name", Values=security_group_names)]
        )
        logger.info(f"Response: {response}")
        return response

    def describe_security_groups_from_vpc(self, vpc_id):
        response = self.ec2_resource.Vpc(vpc_id).security_groups.all()
        logger.info(f"Response: {response}")
        return response

    def describe_security_group_rules(self, security_group_rule_ids: list):
        response = self.ec2_client.describe_security_group_rules(SecurityGroupRuleIds=security_group_rule_ids)
        logger.info(f"Response: {response}")
        return response

    def validate_source_sg_in_sg_rule(self, security_group_id: str, source_security_group_id: str):
        response = self.describe_security_groups_by_ids(security_group_ids=[security_group_id])
        for sg_ip_permission in response["SecurityGroups"][0]["IpPermissions"]:
            for user_id_group_pair in sg_ip_permission["UserIdGroupPairs"]:
                if user_id_group_pair["GroupId"] == source_security_group_id:
                    logger.info(f"Found {source_security_group_id} for SG IP Permission: {user_id_group_pair}")
                    return True
        return False

    def update_security_group_ingress_allow_all(self, security_group):
        try:
            self.update_security_group_ingress(
                security_group_id=security_group.id,
                ip_protocol="-1",
                from_port=0,
                to_port=65535,
                ip_ranges="0.0.0.0/0",
            )
        except BotoException.ClientError as e:
            error_expected = "InvalidPermission.Duplicate"
            if e.response["Error"]["Code"] == error_expected:
                logger.info("IP already present in security group")
            else:
                raise e

    def update_security_group_ingress(
        self,
        security_group_id: str,
        ip_protocol: str = "tcp",
        from_port: int = 22,
        to_port: int = 22,
        ip_ranges: str = "0.0.0.0/0",
    ):
        """Updates the ingress rule for a security group
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.authorize_security_group_ingress

        Args:
            security_group_id (str): ID of the security group which needs ingress update
            ip_protocol (str, optional): Defaults to "tcp".
            from_port (int, optional): Defaults to 22.
            to_port (int, optional): Defaults to 22.
            ip_ranges (str, optional): Updates CidrIp. Defaults to "0.0.0.0/0".

        Returns:
            dict: Data of the rule update

        NOTE: [IpPermissions] is an array where multiple ports can be passed to be opened.
        For the simplicity of this method definition, I have included only one rule for now.
        If required, this method can be called multiple times to add more ports / rules.
        We can enhance this later if needed.
        """
        data = self.ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    "IpProtocol": ip_protocol,
                    "FromPort": from_port,
                    "ToPort": to_port,
                    "IpRanges": [{"CidrIp": ip_ranges}],
                },
            ],
        )

        logger.info("Security Group Ingress Successfully Set %s" % data)
        return data

    def update_security_group_ingress_by_source_sg_name(
        self,
        security_group_id: str,
        source_sg_name: str,
    ):
        """Updates the ingress rule for a security group
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.authorize_security_group_ingress

        Args:
            security_group_id (str): ID of the security group which needs ingress update
            source_sg_name (str): Security Group Name of the Source

        Returns:
            dict: Data of the rule update
        """
        response = self.ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id, SourceSecurityGroupName=source_sg_name
        )
        logger.info(f"Response: {response}")
        return response

    def delete_security_group_ingress_by_sgr_ids(self, security_group_id: str, security_group_rule_ids: list):
        response = self.ec2_client.revoke_security_group_ingress(
            GroupId=security_group_id, SecurityGroupRuleIds=security_group_rule_ids
        )
        logger.info(f"Response: {response}")
        return response

    def delete_all_sgs_in_vpc(self, vpc_id):
        """Delete all inbound and outbound rules from security groups and delete all security groups, then verify if resources are deleted.
        Default security group deletion is skipped. Default VPC resources cannot be deleted without deleting VPC.

        Args:
            vpc_id (str): VPC ID from which security groups are deleted
        """
        sgs = self.describe_security_groups_from_vpc(vpc_id)
        logger.info("Deleting inbound and outbound rules.")
        for sg in sgs:
            if sg.group_name == "default":
                logger.info(sg.id + " is the default security group, continue...")
                continue
            if sg.ip_permissions:
                logger.info(f"Deleting inbound rules for SG: {sg.id}")
                sg.revoke_ingress(IpPermissions=sg.ip_permissions)
            else:
                logger.info(f"Security Group {sg.id} doesn't have inbound ruled, skipping deletion...")
            if sg.ip_permissions_egress:
                logger.info(f"Deleting outbound rules for SG: {sg.id}")
                permission = sg.ip_permissions_egress[0]
                self.ec2_client.revoke_security_group_egress(GroupId=sg.id, IpPermissions=[permission])
            else:
                logger.info(f"Security Group {sg.id} doesn't have outbound ruled, skipping deletion...")
        sgs = self.describe_security_groups_from_vpc(vpc_id)
        logger.info("Deleting security groups...")
        for sg in sgs:
            if sg.group_name == "default":
                logger.info(sg.id + " is the default security group, continue...")
                continue
            logger.info(f"Deleting security group: {sg.id}")
            sg.delete()
        sgs_after_deletion = self.describe_security_groups_from_vpc(vpc_id)
        assert all(
            [sg.group_name == "default" for sg in sgs_after_deletion]
        ), f"Not all security groups are deleted properly. There are some sgs that are not default. SGS: {sgs_after_deletion}"
