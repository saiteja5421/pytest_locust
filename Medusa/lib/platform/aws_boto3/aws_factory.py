import datetime
import logging
import os

from lib.platform.aws_boto3.aws_session_manager import AWSSessionManager
from lib.platform.aws_boto3.client_config import ClientConfig
from lib.platform.aws_boto3.cloud_formation_manager import CloudFormationManager
from lib.platform.aws_boto3.ebs_manager import EBSManager
from lib.platform.aws_boto3.ec2_manager import EC2Manager
from lib.platform.aws_boto3.eks_manager import EKSManager
from lib.platform.aws_boto3.iam_roles_and_policy_manager import IAMRolesAndPolicyManager
from lib.platform.aws_boto3.internet_gateway_manager import InternetGatewayManager
from lib.platform.aws_boto3.kms_manager import KMSManager
from lib.platform.aws_boto3.load_balancer_manager import LoadBalancerManager
from lib.platform.aws_boto3.nat_gateway_manager import NatGatewayManager
from lib.platform.aws_boto3.network_access_list_manager import NetworkAccessListManager
from lib.platform.aws_boto3.network_interface_manager import NetworkInterfaceManager
from lib.platform.aws_boto3.rds_manager import RDSManager
from lib.platform.aws_boto3.route_table_manager import RouteTableManager
from lib.platform.aws_boto3.s3_manager import S3Manager
from lib.platform.aws_boto3.security_group_manager import SecurityGroupManager
from lib.platform.aws_boto3.ssm_manager import SSMManager
from lib.platform.aws_boto3.sts_manager import STSManager
from lib.platform.aws_boto3.subnet_manager import SubnetManager
from lib.platform.aws_boto3.vpc_manager import VPCManager

logger = logging.getLogger()


class AWS:
    def __init__(
        self,
        region_name: str,
        profile_name: str = "default",
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        role_arn: str = os.getenv("TEST_AWS_ROLE_ARN"),
        account_name: str = None,
        set_client_config: bool = False,
    ):
        self._localstack = True if os.getenv("LOCALSTACK_URL") else False

        self._aws_session_manager: AWSSessionManager = AWSSessionManager(
            region_name,
            profile_name,
            aws_access_key_id,
            aws_secret_access_key,
            role_arn,
        )
        self.account_name = account_name
        self.endpoint_url = os.getenv("LOCALSTACK_URL", None)
        self.region_name = region_name
        self._time_created = datetime.datetime.now()
        self.__aws_session = self.__set_session()

        self.client_config = None if not set_client_config else ClientConfig(region_name=self.region_name).client_config

        try:
            logger.info(f"AWS {self.account_name} session: {self.iam.get_current_user()}, region: {self.region_name}")
        except Exception as e:
            logger.warning(f"AWS {self.account_name} list iam session failed in region {self.region_name}: {str(e)}")

    def __repr__(self):
        return f"{vars(self)}"

    @property
    def ec2(self):
        return EC2Manager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def eks(self):
        return EKSManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def s3(self):
        return S3Manager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def ebs(self):
        return EBSManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def security_group(self):
        return SecurityGroupManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def subnet(self):
        return SubnetManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def vpc(self):
        return VPCManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def nat_gateway(self):
        return NatGatewayManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def network_interface(self):
        return NetworkInterfaceManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def nacl(self):
        return NetworkAccessListManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def elb(self):
        return LoadBalancerManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def internet_gateway(self):
        return InternetGatewayManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def route_table(self):
        return RouteTableManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def cloud_formation(self):
        return CloudFormationManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def iam(self):
        return IAMRolesAndPolicyManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def ssm(self):
        return SSMManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def sts(self):
        return STSManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def rds(self):
        return RDSManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    @property
    def kms(self):
        return KMSManager(
            aws_session=self._aws_session, endpoint_url=self.endpoint_url, client_config=self.client_config
        )

    def _aws_session(self):
        token_lifetime = datetime.timedelta(minutes=50)
        if datetime.datetime.now() > self._time_created + token_lifetime:
            logger.info(f"Refresh AWS session, {token_lifetime.seconds}s has passed since {self._time_created}")
            self._time_created = datetime.datetime.now()
            self.__aws_session = self.__set_session()
        return self.__aws_session

    def __set_session(self):
        return (
            self._aws_session_manager.aws_session
            if not self._localstack
            else self._aws_session_manager.localstack_session
        )
