"""
 Test case: TC-57482271
    Test Cloud Backup and Restore for the MAX supported VPC, Security Groups, and Subnets

    Original Regression Ticket: https://nimblejira.nimblestorage.com/browse/DCS-4965
    Convert to PSR Ticket: https://nimblejira.nimblestorage.com/browse/DCS-5878

Steps:
    - Per user:
        1.  Create 5 VPCs, 3 Subnets (2 public, 1 private) per VPC, 5 Security Groups, 5 EC2 Instances with 1 EBS Volume attached per VPC
            - If VPC(s) present, make use of them
            - Create additional VPC(s) to reach 5 MAX
                a)  VPC: 10.0.0.0/16
                    i)  Subnets: 10.0.1.0/24, 10.0.1.0/24, 10.0.1.0/24
                b)  VPC: 10.1.0.0/16
                    i)  Subnets: 10.1.1.0/24, 10.1.2.0/24, 10.1.3.0/24
                c)  VPC: 10.2.0.0/16
                    i)  Subnets: 10.2.1.0/24, 10.2.2.0/24, 10.2.3.0/24
                d)  VPC: 10.3.0.0/16
                    i)  Subnets: 10.3.1.0/24, 10.3.2.0/24, 10.3.3.0/24
                e)  VPC: 10.4.0.0/16
                    i)  Subnets: 10.4.1.0/24, 10.4.2.0/24, 10.4.3.0/24
        2.  Make 2/3 Subnets per VPC Public
            For each VPC:
            a)  Create Internet Gateway
                i)  Make use of any Unattached Internet Gateways as there is a 5 MAX per region like VPCs
            b)  Associate the Internet Gateway with the VPC
            c)  Create a Route Table
            d)  Associate the Route Table with the Internet Gateway
            e)  Associate the Route Table with the 2 Subnets to make them Public
        3.  Create Cloud Backup for each EC2 Instance (no need to write data)
            NOTE: Skipping Native Backup for this test case
        4.  Perform Restore for each EC2 Instance
            NOTE: Skipping -> Discussed with Ruben who wrote this TC: No longer performing Restore Operation as other Test Cases have that handled as we only need to test for max configurations w/Backup
"""

import sys
import datetime
import logging
import time
import uuid
from locust import HttpUser, between
from lib.platform.aws.aws_session import create_aws_session_manager, aws
from lib.dscc.backup_recovery.protection import protection_policy, protection_job, protection_group
from lib.dscc.backup_recovery.aws_protection import backups
from lib.dscc.backup_recovery.aws_protection.assets import ec2, ebs
from common import helpers
from tests.aws.max_vpc_subnet_security_group_ec2_cloud_backup.task import (
    CreateHPECloudBackupCopy2CloudTask,
)
from tests.steps.aws_protection import accounts_steps

from common.enums.ec2_type import Ec2Type
from common.enums.ebs_volume_type import EBSVolumeType
from common.enums.asset_info_types import AssetType
from lib.dscc.backup_recovery.aws_protection.accounts.models.csp_account import CSPAccount
from lib.dscc.backup_recovery.aws_protection.ebs.models.csp_volume import CSPVolume
from lib.dscc.backup_recovery.aws_protection.protection_groups.models.protection_group import ProtectionGroup
from lib.dscc.backup_recovery.aws_protection.ec2.models.csp_instance import (
    CSPMachineInstance,
)
from lib.platform.aws.models.instance import Tag
from lib.platform.aws.ebs_manager import EBSManager
from lib.platform.aws.ec2_manager import EC2Manager
from lib.platform.aws.internet_gateway_manager import InternetGatewayManager
from lib.platform.aws.route_table_manager import RouteTableManager
from lib.platform.aws.security_group_manager import SecurityGroupManager
from lib.platform.aws.subnet_manager import SubnetManager
from lib.platform.aws.vpc_manager import VPCManager
from tests.steps.aws_protection.ami_chooser import random_ami_chooser

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

from lib.logger import rp_agent
from locust import events, HttpUser, between
from locust.runners import WorkerRunner

logger = logging.getLogger(__name__)

TAG_KEY: str = "TC57482271" + str(uuid.uuid4())
TAG_VALUE: str = "TC57482271_Regression"
SECURITY_GROUP_NAME_1: str = "tc57482271_sg1" + str(uuid.uuid4())
SECURITY_GROUP_NAME_2: str = "tc57482271_sg2" + str(uuid.uuid4())
SECURITY_GROUP_NAME_3: str = "tc57482271_sg3" + str(uuid.uuid4())
SECURITY_GROUP_NAME_4: str = "tc57482271_sg4" + str(uuid.uuid4())
SECURITY_GROUP_NAME_5: str = "tc57482271_sg5" + str(uuid.uuid4())
SECURITY_GROUP_NAME_LIST: list[str] = [
    SECURITY_GROUP_NAME_1,
    SECURITY_GROUP_NAME_2,
    SECURITY_GROUP_NAME_3,
    SECURITY_GROUP_NAME_4,
    SECURITY_GROUP_NAME_5,
]
TARGET_VPC_CIDR_BLOCK_LIST: list[str] = ["10.0.0.0/16", "10.1.0.0/16", "10.2.0.0/16", "10.3.0.0/16", "10.4.0.0/16"]
EXISTING_VPC_CIDR_BLOCK_LIST: list[str] = []
RANDOM_SUBNET_IPS: list[str] = ["250.0/24", "251.0/24", "252.0/24", "253.0/24", "254.0/24", "255.0/24"]
POSSIBLE_SUBNET_CIDR_BLOCKS: list[str] = []
TARGET_SUBNET_CIDR_BLOCK_LIST: list[str] = [
    "10.0.1.0/24",
    "10.0.2.0/24",
    "10.0.3.0/24",
    "10.1.1.0/24",
    "10.1.2.0/24",
    "10.1.3.0/24",
    "10.2.1.0/24",
    "10.2.2.0/24",
    "10.2.3.0/24",
    "10.3.1.0/24",
    "10.3.2.0/24",
    "10.3.3.0/24",
    "10.4.1.0/24",
    "10.4.2.0/24",
    "10.4.3.0/24",
]
NEW_SUBNET_IDS: list[str] = []
EXISTING_VPC_IDS_FOR_EXISTING_IG: list[str] = []
ATTACHED_IG_IDS_FOR_EXISTING_IG_VPC: list[str] = []
EXISTING_VPC_IDS_FOR_NEW_IG: list[str] = []
NEW_IG_IDS_FOR_EXISTING_VPC: list[str] = []
NEW_VPC_IDS_FOR_EXISTING_IG: list[str] = []
ATTACHED_EXISTING_IGS_FOR_NEW_VPC: list[str] = []
NEW_VPC_IDS_FOR_NEW_IG: list[str] = []
NEW_IG_IDS_FOR_NEW_VPC: list[str] = []
SG_ID_LIST: list[str] = []
ROUTE_TABLE_ID_LIST: list[str] = []
ROUTE_TABLE_ASSOCIATE_ID_LIST: list[str] = []
EC2_KEY_NAME = None
VOLUME_1_DEVICE: str = "/dev/sdh"
AWS_EC2_ID_LIST: list = []
AWS_EBS_ID_LIST: list = []
CSP_PROTECTION_GROUP: ProtectionGroup = []
KEY_PAIR_NAME = "TC57482271-key-" + str(uuid.uuid4())


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        logging.info("---- Start Load Test -----------")

        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])

        global ec2_manager
        ec2_manager = EC2Manager(aws_session_manager)

        logger.info(f"Generating Key Pair {KEY_PAIR_NAME}")
        ec2_manager.create_ec2_key_pair(key_name=KEY_PAIR_NAME)
        report_portal_dict = helpers.get_report_portal_info()
        user_count = environment.parsed_options.num_users
        run_time_mins = environment.parsed_options.run_time / 60
        logging.info(f"Number of users are {user_count}")
        logging.info("On test start: Add Report portal start launch ")
        global rp_mgr
        global rp_test_id
        global rp_logger
        test_case_name = "TC57482271 - Max VPCs, Subnets, SGs, EC2 Cloud Backups Workflow"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="BACKUP_RESTORE",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        logging.info(f"Number of users are {user_count}")
    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(60, 120)
    tasks = [CreateHPECloudBackupCopy2CloudTask]
    proj_id = None
    protection_policy_id = None
    csp_machine_id = None

    headers = helpers.gen_token()
    proxies = helpers.set_proxy()

    def _create_route_table_associations_security_group_routes_ec2s_ebs(
        self, vpc_id, count: int, availability_zone: str, subnet_ids: list[str], internet_gateway_id: str, tag: Tag
    ):
        # Create a Routing Table
        """
        NOTE:   When a VPC is created it automatically creates a Routing Table.
                But that table is fixed as a Main Route Table & will get the following Error with deletion:
                "The following route tables are main route tables, cannot be deleted until those route tables are set as
                non main route tables."
        """
        # Create a Routing Table with VPC
        route_table = self.route_table_manager.create_route_table(vpc_id=vpc_id, dry_run=False)
        ROUTE_TABLE_ID_LIST.append(route_table.id)

        # Associate 2 Subnets (to make them Public) to the Routing Table
        for k in range(0, 2):
            route_table_associate_id = self.route_table_manager.associate_route_table(
                route_table_id=route_table.id, subnet_id=subnet_ids[k], dry_run=False
            )
            ROUTE_TABLE_ASSOCIATE_ID_LIST.append(route_table_associate_id)

        # Create a Route in the Route Table
        self.route_table_manager.create_route(
            destination_cidr_block="0.0.0.0/0",
            internet_gateway_id=internet_gateway_id,
            route_table_id=route_table.id,
            dry_run=False,
        )

        # Create a Security Group
        logger.info(f"Creating new Security Group {SECURITY_GROUP_NAME_LIST[count]}")
        sg = self.security_group_manager.create_security_group(
            description="TC-57482271-SG", group_name=SECURITY_GROUP_NAME_LIST[count], vpc_id=vpc_id
        )
        logger.info(f"Created new Security Group {sg.id}")
        SG_ID_LIST.append(sg.id)

        # Create 5 EC2 Instances with 1 EBS Volume attached to each EC2
        # NOTE: EC2 uses the Private Subnet (3rd Subnet Created)
        for m in range(0, 5):
            ec2_prefix = "tc57482271_" + str(count) + "_" + str(m) + "_" + str(uuid.uuid4())
            image_id = random_ami_chooser(self.aws)
            ec2_instances = self.ec2_manager.create_custom_config_ec2_instances(
                key_name=KEY_PAIR_NAME,
                image_id=image_id,
                subnet_id=subnet_ids[2],
                availability_zone=availability_zone,
                tags=[tag],
                resource_type="instance",
                security_groups=[sg.id],
                min_count=1,
                max_count=1,
                instance_type=Ec2Type.T2_MICRO.value,
                device_index=0,
                associate_public_ip_address=True,
            )
            ec2_instance_name = ec2_prefix + "_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            new_tags = [Tag(Key="Name", Value=ec2_instance_name), *[tag]]
            self.ec2_manager.create_tags_for_ec2_instance(ec2_instance=ec2_instances[0], tags_list=new_tags)
            volume = self.ebs_manager.create_ebs_volume(
                size=10,
                volume_type=EBSVolumeType.GP2.value,
                tags=[tag],
                resource_type="volume",
                encrypted=False,
                availability_zone=availability_zone,
            )
            self.ebs_manager.attach_volume_to_ec2_instance(
                volume_id=volume.id, device=VOLUME_1_DEVICE, instance_id=ec2_instances[0].id
            )
            AWS_EC2_ID_LIST.append(ec2_instances[0].id)
            AWS_EBS_ID_LIST.append(volume.id)

        # def _delete_ec2_attached_volumes(self, csp_machine_instance: CSPMachineInstance):
        #     for volume in csp_machine_instance.volumeAttachmentInfo:
        #         if not volume.deleteOnTermination:
        #             csp_volume_id = volume.attachedTo.resourceUri.split("/")[-1]
        #             csp_volume: CSPVolume = ebs.get_csp_volume_by_id(csp_volume_id=csp_volume_id)
        #             logger.info(f"Deleting EBS Volume ID {csp_volume.cspInfo.id} - CSP Volume ID {csp_volume_id}")
        #             self.ebs_manger.delete_volume(volume_id=csp_volume.cspInfo.id)

    def on_start(self):
        self.protection_policy_id: str = None
        self.protection_group_id: str = None
        self.protection_job_id: str = None
        self.protection_job = None
        self.protection_group = None
        self.protection_policy = None
        self.protection_job_task_uri: str = None
        self.account = None
        self.csp_account = None
        self.csp_account_id = None
        self.csp_account_resource_uri = None
        self.csp_ec2_list: list = []
        self.csp_ec2_ids: list = []
        self.csp_ec2_resource_uri_list: list = []
        self.protection_policy_name = "TC57482271_Protection_Policy_" + str(uuid.uuid4())
        self.protection_group_name = "TC57482271_Protection_Group_EC2_" + str(uuid.uuid4())

        config = helpers.read_config()
        self.aws = aws(config["testbed"]["AWS"])
        self.aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        self.ec2_manager = EC2Manager(self.aws_session_manager)
        self.ebs_manager = EBSManager(self.aws_session_manager)
        self.vpc_manager = VPCManager(self.aws_session_manager)
        self.security_group_manager = SecurityGroupManager(self.aws_session_manager)
        self.internet_gateway_manager = InternetGatewayManager(self.aws_session_manager)
        self.route_table_manager = RouteTableManager(self.aws_session_manager)
        self.subnet_manager = SubnetManager(self.aws_session_manager)

        tag = Tag(Key=TAG_KEY, Value=TAG_VALUE)
        availability_zone = self.ec2_manager.get_availability_zone()

        # Create 5 VPCs & 5 Security Groups
        # NOTE: 5 VPCs & 5 Internet Gateways max per Region

        # If a VPC already exists, make use of that VPC
        vpc_count: int = 0
        available_vpcs = self.vpc_manager.get_all_vpcs()
        vpcs = [vpc for vpc in available_vpcs]
        if len(vpcs) > 0:
            # NOTE: No need to check # of VPCs as there can only be 5 MAX
            for i in range(0, len(vpcs)):
                # NOTE: Do NOT delete this VPC!
                EXISTING_VPC_CIDR_BLOCK_LIST.append(vpcs[i].cidr_block)

                # Update VPC count
                vpc_count = vpc_count + 1

                vpc_cidr_block: str = vpcs[i].cidr_block

                # If Subnet(s) already exist, make use of those Subnet(s)
                existing_subnet_range: int = 0
                create_subnet_range: int = 0

                # Use empty list to save 3 subnet ids needed for _create_route_table_associations_security_group_routes_ec2s_ebs()
                subnet_ids_for_vpc: list[str] = []
                subnet_cidr_blocks: list[str] = []
                valid_subnet_ids: list[str] = []
                valid_subnet_cidr_blocks: list[str] = []
                subnets = self.subnet_manager.get_all_subnets()
                for subnet in subnets:
                    if subnet.vpc_id == vpcs[i].id:
                        valid_subnet_ids.append(subnet.id)
                        valid_subnet_cidr_blocks.append(subnet.cidr_block)

                # Have only 3 Subnets, update create loop iteration(s) based off of existing subnet(s)
                if len(valid_subnet_ids) >= 3:
                    existing_subnet_range = 3
                    create_subnet_range = 0
                else:
                    existing_subnet_range = len(valid_subnet_ids)
                    create_subnet_range = 3 - existing_subnet_range

                for j in range(0, existing_subnet_range):
                    # NOTE: Do NOT delete this Subnet!
                    subnet_cidr_blocks.append(valid_subnet_cidr_blocks[j])
                    subnet_ids_for_vpc.append(valid_subnet_ids[j])

                # Create Subnets to fullfil the 3 Subnet Count per VPC
                if create_subnet_range > 0:
                    # NOTE: Need to match Subnet CIDR Block with VPC CIDR Block
                    cidr_block: str = ""
                    period_counter: int = 0
                    update_and_break: bool = False
                    for character in vpc_cidr_block:
                        if period_counter == 2:
                            update_and_break = True
                        if character == ".":
                            period_counter = period_counter + 1
                        if update_and_break:
                            for random_subnet_ip in RANDOM_SUBNET_IPS:
                                temp_subnet_cidr_block = cidr_block + random_subnet_ip
                                POSSIBLE_SUBNET_CIDR_BLOCKS.append(temp_subnet_cidr_block)
                            break
                        elif update_and_break == False:
                            cidr_block = cidr_block + character

                    for possible_subnet_cidr_block in POSSIBLE_SUBNET_CIDR_BLOCKS:
                        # Check if POSSIBLE_SUBNET_CIDR_BLOCKS is not already created/in-use
                        if possible_subnet_cidr_block not in subnet_cidr_blocks:
                            logger.info(
                                f"Creating new Subnet with availability zone: {availability_zone} , and VPC: {vpcs[i].id}, {vpcs[i].cidr_block}"
                            )
                            subnet = self.subnet_manager.create_subnet(
                                availability_zone=availability_zone,
                                cidr_block=possible_subnet_cidr_block,
                                vpc_id=vpcs[i].id,
                            )
                            NEW_SUBNET_IDS.append(subnet.id)
                            subnet_ids_for_vpc.append(subnet.id)
                            logger.info(f"Created new Subnet: {subnet.id}")
                            create_subnet_range = create_subnet_range - 1

                        if create_subnet_range == 0:
                            break

                # Create an Internet Gateway & Associate the Internet Gateway with the VPC
                # NOTE: Need to check if Internet Gateway exists, and check if VPC already has an internet gateway attached
                create_ig_flag: bool = True
                attach_ig_flag: bool = True
                exit_flag: bool = False

                # Get latest Internet Gateways
                available_internet_gateways = self.internet_gateway_manager.get_all_internet_gateways()

                for internet_gateway in available_internet_gateways:
                    # Check if already have internet gateway used
                    if internet_gateway.attachments:
                        for internet_gateway_attachements in internet_gateway.attachments:
                            if (
                                internet_gateway_attachements["State"] == "available"
                                and internet_gateway_attachements["VpcId"] == vpcs[i].id
                            ):
                                internet_gateway_for_vpc = internet_gateway
                                create_ig_flag = False
                                attach_ig_flag = False
                                exit_flag = True
                                break
                    else:
                        internet_gateway_for_vpc = internet_gateway
                        create_ig_flag = False
                        attach_ig_flag = True
                    if exit_flag:
                        break

                if create_ig_flag and attach_ig_flag:
                    EXISTING_VPC_IDS_FOR_NEW_IG.append(vpcs[i].id)
                    internet_gateway_for_vpc = self.internet_gateway_manager.create_internet_gateway()
                    NEW_IG_IDS_FOR_EXISTING_VPC.append(internet_gateway_for_vpc.id)
                    self.internet_gateway_manager.attach_internet_gateway(
                        internet_gateway_id=internet_gateway_for_vpc.id, vpc_id=vpcs[i].id, dry_run=False
                    )

                if (create_ig_flag == False) and attach_ig_flag:
                    EXISTING_VPC_IDS_FOR_EXISTING_IG.append(vpcs[i].id)
                    self.internet_gateway_manager.attach_internet_gateway(
                        internet_gateway_id=internet_gateway_for_vpc.id, vpc_id=vpcs[i].id, dry_run=False
                    )
                    ATTACHED_IG_IDS_FOR_EXISTING_IG_VPC.append(internet_gateway_for_vpc.id)
                available_subnet = self.subnet_manager.get_subnet_by_id(subnet_ids_for_vpc[2])
                self._create_route_table_associations_security_group_routes_ec2s_ebs(
                    vpc_id=vpcs[i].id,
                    count=vpc_count,
                    availability_zone=available_subnet.availability_zone,
                    subnet_ids=subnet_ids_for_vpc,
                    internet_gateway_id=internet_gateway_for_vpc.id,
                    tag=tag,
                )

        # Create additional VPCs to reach the 5 VPC MAX
        create_vpc_count: int = 5 - vpc_count

        for i in range(0, create_vpc_count):
            # Create VPC, should auto create a Route Table, but not Subnets nor Internet Gateway
            # NOTE: Check if TARGET_VPC_CIDR_BLOCK is already used in prsesnt VPC: EXISTING_VPC_CIDR_BLOCK_LIST
            # NOTE: This check also satisfies the TARGET_SUBNET_CIDR_BLOCK
            for j in range(0, len(TARGET_VPC_CIDR_BLOCK_LIST)):
                if TARGET_VPC_CIDR_BLOCK_LIST[j] not in EXISTING_VPC_CIDR_BLOCK_LIST:
                    logger.info(f"Creating new VPC with CIDR Block: {TARGET_VPC_CIDR_BLOCK_LIST[i]}")
                    vpc = self.vpc_manager.create_vpc(cidr_block=TARGET_VPC_CIDR_BLOCK_LIST[i])
                    break

            # Create VPC is still in progress when Create Subnet gets run . . .
            time.sleep(3)
            logger.info(f"Created new VPC: {vpc.id}")

            # Use empty list to save 3 subnet ids needed for _create_route_table_associations_security_group_routes_ec2s_ebs()
            subnet_ids_for_vpc: list[str] = []

            # Will Create 3 Subnets per VPC
            for j in range(0, 3):
                logger.info(f"Creating new Subnet with availability zone: {availability_zone} , and VPC: {vpc.id}")
                subnet = self.subnet_manager.create_subnet(
                    availability_zone=availability_zone,
                    cidr_block=TARGET_SUBNET_CIDR_BLOCK_LIST[(3 * i) + j],
                    vpc_id=vpc.id,
                )
                NEW_SUBNET_IDS.append(subnet.id)
                subnet_ids_for_vpc.append(subnet.id)
                logger.info(f"Created new Subnet: {subnet.id}")

            # Create an Internet Gateway & Associate the Internet Gateway with the VPC
            # Check if existing Internet Gateway present that has not been used yet
            create_ig_flag: bool = True
            attach_ig_flag: bool = True
            exit_flag: bool = False

            # Get latest Internet Gateways
            available_internet_gateways = self.internet_gateway_manager.get_all_internet_gateways()

            for internet_gateway in available_internet_gateways:
                # Check if any available Internet Gateways
                # NOTE: Can ignore any Internet Gateways already attached to a VPC, already covered in previous for-loop
                if len(internet_gateway.attachments) == 0:
                    internet_gateway_for_vpc = internet_gateway
                    create_ig_flag = False
                    break

            if create_ig_flag:
                NEW_VPC_IDS_FOR_NEW_IG.append(vpc.id)
                internet_gateway_for_vpc = self.internet_gateway_manager.create_internet_gateway()
                NEW_IG_IDS_FOR_NEW_VPC.append(internet_gateway_for_vpc.id)
                self.internet_gateway_manager.attach_internet_gateway(
                    internet_gateway_id=internet_gateway_for_vpc.id, vpc_id=vpc.id, dry_run=False
                )

            if create_ig_flag == False:
                NEW_VPC_IDS_FOR_EXISTING_IG.append(vpc.id)
                self.internet_gateway_manager.attach_internet_gateway(
                    internet_gateway_id=internet_gateway_for_vpc.id, vpc_id=vpc.id, dry_run=False
                )
                ATTACHED_EXISTING_IGS_FOR_NEW_VPC.append(internet_gateway_for_vpc.id)
            available_subnet = self.subnet_manager.get_subnet_by_id(subnet_ids_for_vpc[2])
            self._create_route_table_associations_security_group_routes_ec2s_ebs(
                vpc_id=vpc.id,
                count=i,
                availability_zone=available_subnet.availability_zone,
                subnet_ids=subnet_ids_for_vpc,
                internet_gateway_id=internet_gateway_for_vpc.id,
                tag=tag,
            )

        # Get CSP Account
        logger.info(f"\n----Step 1-  Get CSP Account for {config['testInput']['Account']['name']} -------")
        self.account = accounts_steps.Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        self.csp_account: CSPAccount = self.account.get_csp_account()
        self.customer_id: str = self.csp_account["customerId"]
        self.csp_account_id: str = self.csp_account["id"]
        self.csp_account_name: str = self.csp_account["name"]
        self.csp_account_resource_uri = self.csp_account["resourceUri"]
        logger.info(f"CSP Account: {self.csp_account}")
        assert self.csp_account is not None, f"Failed to retrieve csp_account"

        # Perform Inventory Sync
        logger.info(f"\n----Step 2-  Perform Inventory Refresh for {self.csp_account_id} -------")
        accounts_steps.refresh_account_inventory(config["testInput"]["Account"])

        # Validate Assets in DSCC
        # Check created assets from fixture
        logger.info("\n----Step 3-  Validate EC2 Instances in DSCC -------")
        for aws_ec2_id in AWS_EC2_ID_LIST:
            csp_instance = ec2.get_csp_ec2_instance_by_aws_id(
                ec2_instance_id=aws_ec2_id, account_id=self.csp_account_id
            )
            assert csp_instance, f"Did not find csp_instance, ec2_id: {aws_ec2_id}"
            logger.info(f"csp_instance found: {csp_instance['id']}")
            self.csp_ec2_list.append(csp_instance)
            self.csp_ec2_ids.append(csp_instance["id"])
            self.csp_ec2_resource_uri_list.append(csp_instance["resourceUri"])

        logger.info("\n----Step 4-  Validate EBS Volumes in DSCC -------")
        for aws_ebs_id in AWS_EBS_ID_LIST:
            csp_volume = ebs.get_csp_volume_by_aws_id(ebs_volume_id=aws_ebs_id, account_id=self.csp_account_id)
            assert csp_volume, f"Did not find csp_volume, ebs_id: {aws_ebs_id}"
            logger.info(f"csp_volume found: {csp_volume['id']}")

        # Create Custom Protection Group & Add EC2 Instances
        logger.info("\n----Step 5-  Create Custom Protection Group for EC2 Instances -------")
        self.protection_group_id = protection_group.create_static_protection_group(
            csp_account_id=self.csp_account_id,
            csp_ec2_id_list=self.csp_ec2_ids,
            group_name=self.protection_group_name,
            regions=[self.aws.region_name],
            client=self.client,
            headers=self.headers,
            proxies=self.proxies,
            asset_type=AssetType.CSP_MACHINE_INSTANCE,
        )

        # Create Protection Policy (Cloud Only)
        logger.info(f"\n----Step 6-  Creating Protection Policy: {self.protection_policy_name}")
        self.protection_policy = protection_policy.create_protection_policy(
            policy_name=self.protection_policy_name, cloud_only=True
        )
        self.protection_policy_id = self.protection_policy["id"]
        logger.info(f"Protection Policy created, Name: {self.protection_policy_name}, ID: {self.protection_policy_id}")

        # Assign Protection Policy to Protection Group
        logger.info("\n----Step 7-  Assign Protection Policy  -------")
        self.protection_job_task_uri = protection_job.create_protection_job(
            asset_id=self.protection_group_id,
            protections_id_one=self.protection_policy["protections"][0]["id"],
            protection_policy_id=self.protection_policy_id,
            asset_type=AssetType.CSP_PROTECTION_GROUP,
        )
        logger.info(f"Protection Job taskUri: {self.protection_job_task_uri}")

        # Get Protection Job ID
        protection_job_response = protection_job.get_protection_job_by_asset_id(asset_id=self.protection_group_id)
        self.protection_job_id = protection_job_response["items"][0]["id"]
        logger.info(f"Protection Job ID: {self.protection_job_id}")

    def on_stop(self):
        logger.info(f"\n\n---- User test completed -------")
        logger.info(f"\n{'Teardown Start'.center(40, '*')}")
        if self.protection_job_id:
            logger.info(
                f"Unassigning Protection Policy {self.protection_policy_name}, Protection Job ID: {self.protection_job_id}"
            )
            unprotect_job_response_local = protection_job.unprotect_job(self.protection_job_id)
            logger.info(unprotect_job_response_local)

        # Delete protection policy
        if self.protection_policy_id:
            logger.info(f"Deleting Protection Policy {self.protection_policy_name}")
            delete_protection_policy_response = protection_policy.delete_protection_policy(self.protection_policy_id)
            logger.info(delete_protection_policy_response)

        # Delete Protection Group
        if self.protection_group_id:
            logger.info(f"Deleting Protection Group {self.protection_group_id}")
            protection_group.delete_protection_group(protection_group_id=self.protection_group_id)

        # Delete EC2 Backups
        for csp_ec2_id in self.csp_ec2_ids:
            backup_response_data = backups.get_all_csp_machine_instance_backups(csp_ec2_id)
            for backup in backup_response_data["items"]:
                backup_id = backup["id"]
                backups.delete_csp_machine_instance_backup(csp_ec2_id, backup_id)

        if AWS_EBS_ID_LIST:
            for i in range(0, len(AWS_EBS_ID_LIST)):
                logger.info(
                    f"Detaching and deleting EBS {AWS_EBS_ID_LIST[i]}, path {VOLUME_1_DEVICE} from EC2  {AWS_EC2_ID_LIST[i]}"
                )
                self.ebs_manager.detach_volume_from_instance(
                    volume_id=AWS_EBS_ID_LIST[i], device=VOLUME_1_DEVICE, instance_id=AWS_EC2_ID_LIST[i], force=False
                )
                self.ebs_manager.delete_volume(volume_id=AWS_EBS_ID_LIST[i])

        if AWS_EC2_ID_LIST:
            for ec2_instance_id in AWS_EC2_ID_LIST:
                logger.info(f"Terminating EC2 {ec2_instance_id}")
                self.ec2_manager.stop_and_terminate_ec2_instance(ec2_instance_id=ec2_instance_id, wait=True)
                logger.info("EC2 Instance Terminated")

        # Delete Security Groups
        for sg_id in SG_ID_LIST:
            logger.info(f"Deleting Security Group: {sg_id}")
            self.security_group_manager.delete_security_group(security_group_id=sg_id)
        # Delete Route, Disassociate 2 Subnets from Route Tables, and Delete Route Tables
        for i in range(0, len(ROUTE_TABLE_ID_LIST)):
            self.route_table_manager.delete_route(
                destination_cidr_block="0.0.0.0/0", route_table_id=ROUTE_TABLE_ID_LIST[i], dry_run=False
            )
            for j in range(0, 2):
                self.route_table_manager.disassociate_route_table(
                    route_table_association_id=ROUTE_TABLE_ASSOCIATE_ID_LIST[(i * 2) + j], dry_run=False
                )
            self.route_table_manager.delete_route_table(route_table_id=ROUTE_TABLE_ID_LIST[i], dry_run=False)
        # Delete Subnet IDs
        for subnet_id in NEW_SUBNET_IDS:
            self.subnet_manager.delete_subnet(subnet_id=subnet_id)

        # Detach & Delete Internet Gateways from existing VPC & newly created VPC
        # Existing VPC & Internet Gateway (NOT attached) -> Detach Internet Gateway
        for i in range(0, len(ATTACHED_IG_IDS_FOR_EXISTING_IG_VPC)):
            self.internet_gateway_manager.detach_internet_gateway(
                internet_gateway_id=ATTACHED_IG_IDS_FOR_EXISTING_IG_VPC[i],
                vpc_id=EXISTING_VPC_IDS_FOR_EXISTING_IG[i],
                dry_run=False,
            )

        # Existing VPC -> Detach & Delete newly created Internet Gateway
        for i in range(0, len(NEW_IG_IDS_FOR_EXISTING_VPC)):
            self.internet_gateway_manager.detach_internet_gateway(
                internet_gateway_id=NEW_IG_IDS_FOR_EXISTING_VPC[i], vpc_id=EXISTING_VPC_IDS_FOR_NEW_IG[i], dry_run=False
            )
            self.internet_gateway_manager.delete_internet_gateway(
                internet_gateway_id=NEW_IG_IDS_FOR_EXISTING_VPC[i], dry_run=False
            )

        # Newly created VPC & Internet Gateway (NOT attached) -> Detach Internet Gateway
        for i in range(0, len(ATTACHED_EXISTING_IGS_FOR_NEW_VPC)):
            self.internet_gateway_manager.detach_internet_gateway(
                internet_gateway_id=ATTACHED_EXISTING_IGS_FOR_NEW_VPC[i],
                vpc_id=NEW_VPC_IDS_FOR_EXISTING_IG[i],
                dry_run=False,
            )

        # Newly created VPC & IG -> Detach & Delete newly created Internet Gateway
        for i in range(0, len(NEW_IG_IDS_FOR_NEW_VPC)):
            self.internet_gateway_manager.detach_internet_gateway(
                internet_gateway_id=NEW_IG_IDS_FOR_NEW_VPC[i], vpc_id=NEW_VPC_IDS_FOR_NEW_IG[i], dry_run=False
            )
            self.internet_gateway_manager.delete_internet_gateway(
                internet_gateway_id=NEW_IG_IDS_FOR_NEW_VPC[i], dry_run=False
            )

        # Delete VPC IDs
        for vpc_id in NEW_VPC_IDS_FOR_EXISTING_IG + NEW_VPC_IDS_FOR_NEW_IG:
            self.vpc_manager.delete_vpc(vpc_id=vpc_id)

        logger.info(f"Delete keypair {EC2_KEY_NAME}")
        self.ec2_manager.delete_key_pair(key_name=KEY_PAIR_NAME)

        logger.info(f"\n{'Teardown Complete: Context'.center(40, '*')}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info(f"----- on test stop------")

    logger.info(f"Delete keypair {EC2_KEY_NAME}")
    ec2_manager.delete_key_pair(key_name=KEY_PAIR_NAME)


@events.request.add_listener
def record_in_report_portal(
    request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs
):
    rp_agent.log_request_stats_in_reportportal(rp_logger, request_type, name, response_time, exception, start_time, url)


@events.quitting.add_listener
def do_checks(environment, **_kw):
    if isinstance(environment.runner, WorkerRunner):
        return

    RP_TEST_STATUS = rp_agent.ReportPortalStatus.PASSED
    logger = rp_agent.set_logger(rp_logger)
    rp_agent.log_stats_summary(environment, logger)

    stats_total = environment.runner.stats.total
    fail_ratio = stats_total.fail_ratio

    check_fail_ratio = 0.01
    logger.info(f"Total number of requests {stats_total.num_requests}")
    if stats_total.num_requests == 0:
        logger.error(f"TEST FAILED: Since no requests occurred")
        RP_TEST_STATUS = rp_agent.ReportPortalStatus.FAILED
        environment.process_exit_code = 3
    else:
        if fail_ratio > check_fail_ratio:
            logger.error(f"CHECK FAILED: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)")
            RP_TEST_STATUS = rp_agent.ReportPortalStatus.FAILED
            environment.process_exit_code = 3
        else:
            logger.info(
                f"CHECK SUCCESSFUL: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
            )

    if rp_mgr:
        rp_mgr.finish_test_step(step_id=rp_test_id, status=RP_TEST_STATUS)
        rp_mgr.finish_launch()
