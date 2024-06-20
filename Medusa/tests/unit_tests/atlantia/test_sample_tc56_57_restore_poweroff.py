"""
Sample test to connect linux machines through SSM also write and validate data
"""

# Standard libraries
from datetime import datetime
import logging
import uuid
from pytest import fixture, mark

# Internal libraries
from lib.common.enums.backup_type import BackupType
from lib.common.enums.ec2_restore_operation import Ec2RestoreOperation
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.aws_availability_zone import AWSAvailabilityZone
from lib.common.enums.ebs_volume_type import EBSVolumeType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import CSPMachineInstanceModel
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.address import Address
from lib.platform.aws_boto3.models.instance import Tag
from lib.common.enums.ec2_username import EC2Username

# Steps
from tests.e2e.aws_protection.context import Context

from tests.steps.aws_protection.backup_steps import (
    get_ami_and_snapshot_status_list,
    delete_csp_instance_backups,
    get_csp_machine_instance_backups,
    run_backup_for_asset_and_wait_for_trigger_task,
)

# import tests.steps.aws_protection.backup_steps as BackupSteps
import tests.steps.aws_protection.common_steps as CommonSteps
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps
from tests.steps.aws_protection.assets import ec2_ebs_steps
from tests.steps.aws_protection.assets.standard_asset_creation_steps import (
    generate_key_pair,
    random_ami_chooser,
)
from tests.steps.aws_protection.policy_manager_steps import (
    assign_protection_policy,
    create_protection_policy,
    delete_protection_jobs_and_policy,
)
from tests.steps.aws_protection.inventory_manager_steps import (
    csp_machine_instance_refresh,
    get_csp_instance_by_ec2_instance_id,
    get_csp_instances,
    validate_protection_status,
    get_subnet_csp_id,
)
from lib.common.enums.protection_summary import ProtectionStatus
from lib.common.enums.state import State

logger = logging.getLogger()


PROTECTION_POLICY_NAME: str = "TC57_protection_policy"
RESTORE_EC2_CLOUD_BACKUP_NAME = "TC57_Restored_Cloud_Backup_EC2_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
RESTORE_EC2_BACKUP_NAME = "TC57_Restored_Backup_EC2_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
RESTORE_TAGS = [CSPTag(key="TC57_Restore_EC2_Backup", value="RestoreEc2Cloud")]
SG_NAME: str = "TC57-" + str(uuid.uuid4())
TAG_KEY: str = "TC57"
TAG_VALUE: str = "regression" + str(uuid.uuid4())
EC2_KEY_NAME: str = None

EC2_INSTANCE_ID: str = None
CSP_ACCOUNT: CSPAccountModel = None
CSP_EC2: CSPMachineInstanceModel = None
RESTORE_CSP_EC2: CSPMachineInstanceModel = None
ELASTIC_IP_INFO: Address = None

INSTANCE_ARN: str = "AmazonSSMRoleForInstancesQuickSetup"
INSTANCE_ROLE_NAME: str = "AmazonSSMRoleForInstancesQuickSetup"
AWS_ACCOUNT_ID: str = None


# Variable declaration for restore and terminate
###############################################################################################################
RESTORE_EC2_TERMINATE_CLOUD_BACKUP_NAME = "TC57_Restored_Terminate_Cloud_Backup_EC2_" + datetime.now().strftime(
    "%Y%m%d%H%M%S%f"
)
RESTORE_EC2_TERMINATE_BACKUP_NAME = "TC57_Restored_Terminate_Backup_EC2_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
RESTORE_TAGS_TERMINATE = [CSPTag(key="TC57_Restore_Terminate_EC2_Backup", value="RestoreTerminateEc2Cloud")]
RESTORE_CSP_TERMINATE_EC2: CSPMachineInstanceModel = None
###############################################################################################################


@fixture(scope="function")
def context():
    global EC2_KEY_NAME, EC2_INSTANCE_ID, ELASTIC_IP_INFO, AWS_ACCOUNT_ID
    context = Context()
    aws: AWS = context.aws_one

    ami_image_id = random_ami_chooser(aws)
    availability_zone = AWSAvailabilityZone(aws.ec2.get_availability_zone())

    # Tags to create ec2 instance
    tags: list[Tag] = [Tag(Key=TAG_KEY, Value=TAG_VALUE)]
    logger.info("Fetching a VPC for new subnet creation.")

    # Creating EC2 and EBS
    ec2_key_pair: str = "ec2-key-" + str(uuid.uuid4())
    generate_key_pair(aws=aws, key_pair=ec2_key_pair)
    EC2_KEY_NAME = ec2_key_pair
    ec2_instances, ebs_volume = ec2_ebs_steps.create_ec2_with_ebs_attached(
        aws=aws,
        ec2_key_name=EC2_KEY_NAME,
        ec2_image_id=ami_image_id,
        availability_zone=availability_zone.value,
        tags=tags,
        volume_size=10,
        volume_device="/dev/sdh",
        volume_type=EBSVolumeType.GP2.value,
    )
    EC2_INSTANCE_ID = ec2_instances[0].id

    logger.info(f"Fetching CSP Account {context.aws_one_account_name}")
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, context.aws_one_account_name)
    AWS_ACCOUNT_ID = csp_account.cspId.split(":")[-2]
    logger.info(f"AWS Account ID = {AWS_ACCOUNT_ID}")

    # Allocate elastic IP Address to EC2 instance
    ELASTIC_IP_INFO = aws.ec2.create_elastic_ip()
    aws.ec2.associate_elastic_ip_to_instance(
        allocation_id=ELASTIC_IP_INFO.AllocationId,
        ec2_instance_id=EC2_INSTANCE_ID,
    )

    logger.info(f"""Associating ["arn":{INSTANCE_ARN}, "name":{INSTANCE_ROLE_NAME}] to {EC2_INSTANCE_ID}""")
    context.aws_one.ec2.associate_iam_profile(
        instance_id=EC2_INSTANCE_ID,
        aws_account_id=AWS_ACCOUNT_ID,
        arn=INSTANCE_ARN,
        name=INSTANCE_ROLE_NAME,
    )

    yield context

    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    get_ami_and_snapshot_status_list(aws)
    # Cleanup Elastic IP
    if ELASTIC_IP_INFO:
        logger.info(f"Disassociate and release elastic ip {ELASTIC_IP_INFO.PublicIp} from restored EC2 instance")
        aws.ec2.disassociate_and_release_elastic_ip(
            association_id=ELASTIC_IP_INFO.AssociationId,
            allocation_id=ELASTIC_IP_INFO.AllocationId,
            public_ip=ELASTIC_IP_INFO.PublicIp,
        )

    # Delete AWS EC2 Instance & attached EBS Volume
    if EC2_INSTANCE_ID:
        logger.info(f"Cleanup Source EC2 instance {EC2_INSTANCE_ID} and ebs volume {ebs_volume.id}")
        ec2_ebs_steps.cleanup_ec2_instances_by_id(
            aws=aws, ec2_instance_ids=[EC2_INSTANCE_ID], delete_attached_volumes=True
        )

    # Delete Restore AWS EC2 Instance & attached EBS Volume
    if RESTORE_CSP_EC2:
        logger.info(f"Cleanup Source EC2 instance {RESTORE_CSP_EC2.id} and ebs volume")
        ec2_ebs_steps.cleanup_ec2_instances_by_id(
            aws=aws,
            ec2_instance_ids=[RESTORE_CSP_EC2.cspId],
            delete_attached_volumes=True,
        )

    # Delete Restore AWS EC2 Instance & attached EBS Volume
    if RESTORE_CSP_TERMINATE_EC2:
        logger.info(f"Cleanup Source EC2 instance {RESTORE_CSP_TERMINATE_EC2.id} and ebs volume")
        ec2_ebs_steps.cleanup_ec2_instances_by_id(
            aws=aws,
            ec2_instance_ids=[RESTORE_CSP_TERMINATE_EC2.cspId],
            delete_attached_volumes=True,
        )

    # Delete Backups
    if CSP_EC2:
        logger.info(f"Delete source instance {CSP_EC2.id} backups")
        delete_csp_instance_backups(
            context=context,
            instance_ids=[CSP_EC2.id],
            csp_account=CSP_ACCOUNT,
            region=context.aws_one_region_name,
        )
        csp_machine_instance_refresh(context=context, csp_machine_id=CSP_EC2.id)
        expected_status = ProtectionStatus.LAPSED if CSP_EC2.backupInfo else ProtectionStatus.PENDING
        if State.DELETED.value == CSP_EC2.state:
            expected_status = ProtectionStatus.PAUSED
        if not validate_protection_status(
            context=context,
            asset_id=CSP_EC2.id,
            asset_type=AssetType.CSP_MACHINE_INSTANCE,
            expected_status=expected_status,
            validate=False,
        ):
            logger.error(f"Protection status did not change to the expected state {expected_status.value}")

    if context.protection_policy_id:
        logger.info(
            f"Deleting Protection Jobs & Protection Policy {context.protection_policy_id}, {PROTECTION_POLICY_NAME}"
        )
        delete_protection_jobs_and_policy(context=context, protection_policy_name=PROTECTION_POLICY_NAME)

    if context.security_group:
        logger.info(f"Deleting Security Group {SG_NAME}")
        aws.security_group.delete_security_group(security_group_id=context.security_group.id)

    if EC2_KEY_NAME:
        logger.info(f"Delete keypair {EC2_KEY_NAME}")
        aws.ec2.delete_key_pair(key_name=EC2_KEY_NAME)

    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.order(575)
def test_backup_ondemand_poweroff_restore_terminate_restore_instance(context: Context):
    global RESTORE_CSP_EC2, CSP_EC2, CSP_ACCOUNT, RESTORE_CSP_TERMINATE_EC2, EC2_INSTANCE_ID
    aws = context.aws_one

    # Perform inventory refresh and fetching csp machine instance id
    csp_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_name(context, context.aws_one_account_name)
    CSP_ACCOUNT = csp_account
    CommonSteps.refresh_inventory_with_retry(context=context, account_id=CSP_ACCOUNT.id)

    # Get csp machine instance

    csp_ec2: CSPMachineInstanceModel = get_csp_instance_by_ec2_instance_id(
        context=context, ec2_instance_id=EC2_INSTANCE_ID, account_id=CSP_ACCOUNT.id
    )
    assert csp_ec2 is not None
    CSP_EC2 = csp_ec2

    # Create Protection policy
    delete_protection_jobs_and_policy(context=context, protection_policy_name=PROTECTION_POLICY_NAME)
    context.protection_policy_id = create_protection_policy(
        context=context, backup_only=True, name=PROTECTION_POLICY_NAME
    )
    logger.info(f"Protection policy created successfully {context.protection_policy_id}")

    # Write some data on EC2 instance
    ec2_instance = aws.ec2.get_ec2_instance_by_id(EC2_INSTANCE_ID)

    user_name: str = EC2Username.get_ec2_username(ec2_instance=ec2_instance)

    CommonSteps.write_and_validate_data_dm_core_ssm(
        context=context,
        ec2_instance=ec2_instance,
        user_name=user_name,
        percentage_to_fill=15,
    )

    # Assign the protection policy
    assign_protection_policy(
        context=context,
        asset_id=CSP_EC2.id,
        asset_type=AssetType.CSP_MACHINE_INSTANCE.value,
        protection_policy_id=context.protection_policy_id,
    )

    # Run Backup
    run_backup_for_asset_and_wait_for_trigger_task(
        context=context,
        asset_resource_uri=CSP_EC2.resourceUri,
        backup_type=BackupType.BACKUP,
    )

    # After wait completes get on demand backup
    ec2_backup_list = get_csp_machine_instance_backups(context=context, csp_machine_instance_id=CSP_EC2.id)
    assert ec2_backup_list.total >= 1
    ec2_backups = ec2_backup_list.items

    # Perform Restore
    subnet_csp_id: str = get_subnet_csp_id(
        context=context,
        account_id=CSP_ACCOUNT.id,
        subnet_id=CSP_EC2.cspInfo.networkInfo.subnetInfo.id,
    )

    CommonSteps.ec2_restore(
        context=context,
        source_ec2_instance=CSP_EC2,
        source_ec2_instance_backup=ec2_backups[0],
        restore_type=Ec2RestoreOperation.REPLACE.value,
        restored_ec2_name=RESTORE_EC2_BACKUP_NAME,
        availability_zone=CSP_EC2.cspInfo.availabilityZone,
        subnet_id=subnet_csp_id,
        tags=RESTORE_TAGS,
        aws=aws,
    )

    # NOTE: Old AWS EC2 Instance was stopped during restore

    # get Restored EC2_Instance by Name
    restored_ec2_instance_filter = f"accountInfo/id eq {CSP_ACCOUNT.id} and name eq '{RESTORE_EC2_BACKUP_NAME}'"
    restored_ec2_instances = get_csp_instances(context, filter=restored_ec2_instance_filter)

    # there should be one (1) returned ec2_instance
    assert restored_ec2_instances.total == 1, f"restored EC2 Instance not found: '{RESTORE_EC2_BACKUP_NAME}'"
    RESTORE_CSP_EC2 = restored_ec2_instances.items[0]

    # Get Restored EC2 instance object by instance id
    restored_ec2_instance_object = aws.ec2.get_ec2_instance_by_id(RESTORE_CSP_EC2.cspId)

    logger.info(
        f"""Associating ["arn":{INSTANCE_ARN}, "name":{INSTANCE_ROLE_NAME}] to {restored_ec2_instance_object.id}"""
    )
    context.aws_one.ec2.associate_iam_profile(
        instance_id=restored_ec2_instance_object.id,
        aws_account_id=AWS_ACCOUNT_ID,
        arn=INSTANCE_ARN,
        name=INSTANCE_ROLE_NAME,
    )

    # Once restore Done validate data integrity is maintained and dedupe ratio
    # Fetching username using source 'ec2_instance' because AMI for restored instance is set as 'Private'
    CommonSteps.write_and_validate_data_dm_core_ssm(
        context=context,
        ec2_instance=restored_ec2_instance_object,
        user_name=user_name,
        validation=True,
        percentage_to_fill=15,
    )

    # Validate IP and check status of the original instances after replacing by restore operation
    restored_ec2_instance_ip = aws.ec2.get_instance_ip_by_id(instance_id=RESTORE_CSP_EC2.cspId)
    ec2_instance_old_ip = ELASTIC_IP_INFO.PublicIp
    assert (
        restored_ec2_instance_ip == ec2_instance_old_ip
    ), "Elastic IP of new ec2 instance not matching with old instance"

    old_csp_ec2: CSPMachineInstanceModel = get_csp_instance_by_ec2_instance_id(
        context=context, ec2_instance_id=EC2_INSTANCE_ID, account_id=CSP_ACCOUNT.id
    )
    assert old_csp_ec2.cspInfo.state == "STOPPED", f"EC2 Instance {EC2_INSTANCE_ID} is not STOPPED!"

    #################################################################################################################
    # Perform terminate and Restore
    subnet_csp_id: str = get_subnet_csp_id(
        context=context,
        account_id=CSP_ACCOUNT.id,
        subnet_id=CSP_EC2.cspInfo.networkInfo.subnetInfo.id,
    )

    CommonSteps.ec2_restore(
        context=context,
        source_ec2_instance=CSP_EC2,
        source_ec2_instance_backup=ec2_backups[0],
        restore_type=Ec2RestoreOperation.REPLACE.value,
        restored_ec2_name=RESTORE_EC2_TERMINATE_BACKUP_NAME,
        availability_zone=CSP_EC2.cspInfo.availabilityZone,
        subnet_id=subnet_csp_id,
        tags=RESTORE_TAGS_TERMINATE,
        terminate_original=True,
        aws=aws,
    )

    # Old AWS EC2 is terminated during restore
    EC2_INSTANCE_ID = None

    # get Restored EC2_Instance by Name
    restored_ec2_instance_terminate_filter = (
        f"accountInfo/id eq {CSP_ACCOUNT.id} and name eq '{RESTORE_EC2_TERMINATE_BACKUP_NAME}'"
    )
    restored_ec2_instances_terminate = get_csp_instances(context, filter=restored_ec2_instance_terminate_filter)

    # there should be one (1) returned ec2_instance
    assert (
        restored_ec2_instances_terminate.total == 1
    ), f"restored EC2 Instance not found: '{RESTORE_EC2_TERMINATE_BACKUP_NAME}'"
    RESTORE_CSP_TERMINATE_EC2 = restored_ec2_instances_terminate.items[0]

    # Get Restored EC2 instance object by instance id
    restored_ec2_instance_terminate_object = aws.ec2.get_ec2_instance_by_id(RESTORE_CSP_TERMINATE_EC2.cspId)

    logger.info(
        f"""Associating ["arn":{INSTANCE_ARN}, "name":{INSTANCE_ROLE_NAME}] to {restored_ec2_instance_terminate_object.id}"""
    )
    context.aws_one.ec2.associate_iam_profile(
        instance_id=restored_ec2_instance_terminate_object.id,
        aws_account_id=AWS_ACCOUNT_ID,
        arn=INSTANCE_ARN,
        name=INSTANCE_ROLE_NAME,
    )

    # Once restore Done validate data integrity is maintained and dedupe ratio
    # Fetching username using source 'ec2_instance' because AMI for restored instance is set as 'Private'
    CommonSteps.write_and_validate_data_dm_core_ssm(
        context=context,
        ec2_instance=restored_ec2_instance_terminate_object,
        user_name=user_name,
        validation=True,
        percentage_to_fill=15,
    )

    # NOTE: After restore twice Elastic IP of new ec2 instance does not matching with old instance
    # ensure old esp ec2 is deleted
    old_csp_ec2_terminate: CSPMachineInstanceModel = get_csp_instance_by_ec2_instance_id(
        context=context, ec2_instance_id=ec2_instance.id, account_id=CSP_ACCOUNT.id
    )
    logger.info(f"Verifying Old csp ec2 instance {old_csp_ec2_terminate.state}")
    assert old_csp_ec2_terminate.state == "DELETED", "Old CSP EC2 instance not marked for deletion"
    #################################################################################################################
