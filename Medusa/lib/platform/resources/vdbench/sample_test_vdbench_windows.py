# Standard libraries
import logging
import uuid
from pytest import fixture
from lib.common.enums.aws_availability_zone import AWSAvailabilityZone
from lib.common.enums.ami_image_ids import AMIImageIDs
from lib.common.enums.ebs_volume_type import EBSVolumeType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.platform.aws_boto3.windows_session_manager import WindowsSessionManager
from tests.steps.aws_protection.assets.standard_asset_creation_steps import (
    generate_key_pair,
)
import tests.steps.aws_protection.assets.ec2_ebs_steps as EC2EBSSteps

# Utils
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.cloud_account_manager_steps import get_csp_account_by_csp_name

logger = logging.getLogger()

EC2_INSTANCE_ID: str = None
RESTORED_EC2_INSTANCE_ID: str = None
EBS_VOLUME_ID: str = None
KEY_PAIR: str = "ec2-key-" + str(uuid.uuid4())
SG_NAME: str = "SG-" + str(uuid.uuid4())
DRIVE_LETTER: str = "D"
FILE_SYSTEM_FORMAT: str = "NTFS"
INSTANCE_ARN: str = "AmazonSSMRoleForInstancesQuickSetup"
INSTANCE_ROLE_NAME: str = "AmazonSSMRoleForInstancesQuickSetup"

# Basic Auth and Encryption commands are required to make remote connection through code
BASIC_AUTH_COMMAND: str = """Set-Item -Force WSMan:\\localhost\\Service\\auth\\Basic $true"""
ENCRYPTION_COMMAND: str = """Set-Item -Force WSMan:\\localhost\\Service\\AllowUnencrypted $true"""

# Command to enable firewall for WinRM ports
FIREWALL_COMMAND: str = (
    """New-NetFirewallRule -DisplayName "Allow WinRM Ports" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5985-5986"""
)

TAG_KEY: str = "TC-Windows-Key"
TAG_VALUE: str = "regression" + str(uuid.uuid4())

POLICY_NAME: str = "TC_Windows Protection Policy"

# Recommended device names for Windows: /dev/sda1 for root volume. xvd[f-p] for data volumes.
VOLUME_DEVICE: str = "xvdf"
RESTORED_EC2_NAME: str = "Restored EC2 Sanity Instance TC75" + str(uuid.uuid4())


@fixture(scope="module")
def context():
    context = Context()
    yield context


def test_write_data_in_windows(context: Context):
    global EC2_INSTANCE_ID, EBS_VOLUME_ID

    logger.info("Fetching a VPC for new subnet creation.")
    vpc = context.aws_one.vpc.get_vpc(public_dns_support=True)

    # Creating a security group because "default" one does not have ingress enabled for SSH.
    logger.info(f"Creating new Security Group {SG_NAME}")
    sg = context.aws_one.security_group.create_security_group(
        description="TC-Windows-SG", group_name=SG_NAME, vpc_id=vpc.id
    )
    logger.info(f"Created new Security Group {SG_NAME}")

    logger.info(f"Updating Ingress rule for SG {SG_NAME}")
    context.aws_one.security_group.update_security_group_ingress(
        security_group_id=sg.id,
        ip_protocol="tcp",
        from_port=22,
        to_port=22,
        ip_ranges="0.0.0.0/0",
    )

    logger.info(f"Generating Key Pair {KEY_PAIR}")
    generate_key_pair(aws=context.aws_one, key_pair=KEY_PAIR)
    ec2_instances, ebs_volume = EC2EBSSteps.create_ec2_with_ebs_attached(
        aws=context.aws_one,
        ec2_key_name=KEY_PAIR,
        ec2_image_id=AMIImageIDs.WINDOWS_SERVER_2022_BASE_US_WEST_2.value,
        availability_zone=AWSAvailabilityZone.US_WEST_2A.value,
        tags=[],
        volume_size=10,
        volume_device=VOLUME_DEVICE,
        volume_type=EBSVolumeType.GP2.value,
        security_groups=[SG_NAME],
    )

    EC2_INSTANCE_ID = ec2_instances[0].id
    EBS_VOLUME_ID = ebs_volume.id

    logger.info(f"Fetching CSP Account {context.aws_one_account_name}")
    csp_account: CSPAccountModel = get_csp_account_by_csp_name(
        context=context, account_name=context.aws_one_account_name
    )
    AWS_ACCOUNT_ID = csp_account.cspId.split(":")[-2]
    logger.info(f"AWS Account ID = {AWS_ACCOUNT_ID}")

    logger.info(f"""Associating ["arn":{INSTANCE_ARN}, "name":{INSTANCE_ROLE_NAME}] to {EC2_INSTANCE_ID} """)
    context.aws_one.ec2.associate_iam_profile(
        instance_id=EC2_INSTANCE_ID,
        aws_account_id=AWS_ACCOUNT_ID,
        arn=INSTANCE_ARN,
        name=INSTANCE_ROLE_NAME,
    )

    ec2_instance = context.aws_one.ec2.get_ec2_instance_by_id(ec2_instance_id=EC2_INSTANCE_ID)

    # Setting up the Basic Auth, Encryption and Firewall will enable the session to be created
    logger.info(f"Generating Session for Windows EC2 {EC2_INSTANCE_ID}")
    windows_session_manager = WindowsSessionManager()
    password: str = windows_session_manager.get_ec2_password(
        aws=context.aws_one,
        ec2_instance=ec2_instance,
        private_key_file_path=f"{KEY_PAIR}.pem",
    )

    logger.info(f"Initializing and Formatting Disk. Assigning Drive Letter '{DRIVE_LETTER}'")
    context.aws_one.ssm.initialize_and_format_disk(
        ec2_instance_id=EC2_INSTANCE_ID,
        drive_letter=DRIVE_LETTER,
        file_system_format=FILE_SYSTEM_FORMAT,
    )

    # Install vdbench in windows
    context.aws_one.ssm.setup_vdbench_in_windows_instance(
        ec2_instance=ec2_instance,
        ec2_key_pair=KEY_PAIR,
        ec2_password=password,
        drive_letter=DRIVE_LETTER,
    )

    # write and validate data
    context.aws_one.ssm.write_and_validate_data_vdbench(
        ec2_instance_id=EC2_INSTANCE_ID,
        file_size="1g",
        file_count=2,
        dir_name="dir1",
        depth=1,
        width=2,
        devices=[DRIVE_LETTER],
        source_drive=DRIVE_LETTER,
    )
    context.aws_one.ssm.write_and_validate_data_vdbench(
        ec2_instance_id=EC2_INSTANCE_ID,
        file_size="1g",
        file_count=2,
        dir_name="dir1",
        depth=1,
        width=2,
        devices=[DRIVE_LETTER],
        source_drive=DRIVE_LETTER,
        validate=True,
    )

    # write and validate data using custom config file
    context.aws_one.ssm.write_and_validate_data_vdbench_with_custom_config_file(
        ec2_instance_id=EC2_INSTANCE_ID,
        source_drive=DRIVE_LETTER,
        remote_config_file=context.vdbench_config_file,
    )
    context.aws_one.ssm.write_and_validate_data_vdbench_with_custom_config_file(
        ec2_instance_id=EC2_INSTANCE_ID,
        source_drive=DRIVE_LETTER,
        remote_config_file=context.vdbench_config_file,
        validate=True,
    )
