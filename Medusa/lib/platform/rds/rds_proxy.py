from dataclasses import dataclass
import time
from sshtunnel import BaseSSHTunnelForwarderError
import http.client
import urllib.parse
import logging
import uuid
from lib.common.enums.os import OS
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.host.SSHProxyDscc import SSHProxyDscc
from waiting import wait, TimeoutExpired
from tests.steps.aws_protection.assets.standard_asset_creation_steps import (
    generate_key_pair,
    get_latest_ami_image_filters,
)

logger = logging.getLogger()


@dataclass
class DBBindings:
    db_host: str
    db_port: int
    local_port: int


class RDSProxy:
    """
    RDS Proxy to connect HPE network via ec2 and web-proxy to database.

    RDS DB:
        Create RDS DB if not already created.

    Ec2 bastion (must be Ubuntu):
        Create ec2 and use as bastion by setting ec2_bastion_id and key_pair_name variables
        or allow RDSProxy to create ec2 bastion instance by not setting those variables.

    Security Group:
        Checks ingress/ingoing Security Group Rules, add necessary connections from EC2 bastion -> RDS DB

    Teardown:
        Close proxy which will close tunnel, terminate bastion instance, terminate RDS DB.
        Best to use in teardown as if the test fails, an instance/RDS/SG Rules would not be terminated.
        RDSProxy will not terminate instances passed by
    """

    def __init__(
        self,
        aws: AWS,
        web_proxy: str,
        start: bool = True,
        db_bindings: list[DBBindings] = list(),
        ec2_bastion_id: str = None,
        key_pair_name: str = None,
    ):
        self.aws: AWS = aws

        # Check if EC2 bastion instance is created, if so get the availability zone to check with RDS DB
        self._ec2_bastion_created = True if ec2_bastion_id and key_pair_name else False
        self._aws_name = f"ec2_rds_bastion-{str(uuid.uuid4())}"
        self._ec2_bastion_dns = ""
        self._server = None
        self._http_con = None
        self.ec2_bastion_id = ec2_bastion_id
        self.web_proxy = web_proxy
        self.key_pair_name = key_pair_name if self._ec2_bastion_created else self._aws_name

        self.remote_bindings = [(binding.db_host, binding.db_port) for binding in db_bindings]
        self.locals_bindings = [("0.0.0.0", binding.local_port) for binding in db_bindings]

        if start:
            for i in range(5):
                try:
                    self.init_proxy()
                    self.start_proxy()
                    break
                except BaseSSHTunnelForwarderError as e:
                    seconds = 120 + i * 120
                    time.sleep(seconds)
                    logger.warn(f"Create RDS proxy connection retry: {i}, Error: {e}")

    def start_proxy(self):
        self._server.start_ssh_dscc()

    def init_proxy(self):
        if not self._ec2_bastion_created:
            self._setup_ec2_bastion()
        # NOTE: Public DNS Name / IP is not working from GET Instance ID when not created originally
        self._get_ec2_dns()

        url = urllib.parse.urlparse(self.web_proxy)
        self._http_con = http.client.HTTPConnection(url.hostname, url.port)
        self._http_con.set_tunnel(self._ec2_bastion_dns, 22)
        self._http_con.connect()

        self._server = SSHProxyDscc(
            (self._ec2_bastion_dns, 22),
            ssh_username="ubuntu",
            ssh_private_key=f"{self.key_pair_name}.pem",
            remote_bind_addresses=self.remote_bindings,
            local_bind_addresses=self.locals_bindings,
            ssh_proxy=self._http_con.sock,
        )

    def stop_proxy(self):
        self._server.stop()
        self._http_con.close()

    def close_proxy(self):
        self.stop_proxy()
        if not self._ec2_bastion_created:
            self._terminate_ec2_bastion()

    def _setup_ec2_bastion(self):
        availability_zone = [
            zone["ZoneName"] for zone in self.aws.ec2.ec2_client.describe_availability_zones()["AvailabilityZones"]
        ][0]
        subnet = [
            subnet for subnet in self.aws.subnet.get_all_subnets() if subnet.availability_zone == availability_zone
        ][0]
        security_group = [
            security_group
            for security_group in self.aws.security_group.get_all_security_groups()
            if security_group.vpc_id == subnet.vpc_id
        ][-1]

        self.aws.security_group.update_security_group_ingress_allow_all(security_group)

        if not self._ec2_bastion_created:
            generate_key_pair(self.aws, self.key_pair_name)

        ubuntu_image = get_latest_ami_image_filters(self.aws, OS.UBUNTU)

        ec2_instances = self.aws.ec2.create_custom_config_ec2_instances(
            key_name=self.key_pair_name,
            image_id=ubuntu_image,
            availability_zone=availability_zone,
            subnet_id=subnet.id,
            security_groups=[security_group.id],
            tags=[Tag(Key="Name", Value=self._aws_name)],
        )
        self.ec2_bastion_id = ec2_instances[0].id

    def _get_ec2_dns(self):
        try:
            self._ec2_bastion_dns = wait(
                lambda: self.aws.ec2.get_ec2_instance_by_id(self.ec2_bastion_id).public_dns_name,
                timeout_seconds=60 * 6,
                sleep_seconds=10,
            )
        except TimeoutExpired as e:
            logger.info(f"Timeout waiting for ec2 bastion dns exceeded : {self.ec2_bastion_id}")
            raise e

    def _terminate_ec2_bastion(self):
        try:
            self.aws.ec2.terminate_ec2_instance(ec2_instance_id=self.ec2_bastion_id)
        except Exception as e:
            logger.warn(f"Ec2 was not terminated {self.ec2_bastion_id}\n {e}")

        try:
            self.aws.ec2.delete_key_pair(key_name=self.key_pair_name)
        except Exception as e:
            logger.warn(f"Key pair was not deleted {self.key_pair_name}\n {e}")
