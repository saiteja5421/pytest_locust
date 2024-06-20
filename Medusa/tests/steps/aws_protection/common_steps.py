import logging
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import CSPBackupModel
from pytest_check import check
import os
import time
import paramiko
import random
import string

from typing import Optional
from waiting import wait, TimeoutExpired
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.csp_type import CspType
from lib.common.enums.rds_snapshot_type import RDSSnapshotType
from lib.common.enums.ec2_type import Ec2Type
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.platform.azure.azure_factory import Azure
from tests.e2e.azure_protection.azure_context import AzureContext
from tests.steps.aws_protection.eks.csp_eks_backup_steps import get_k8s_app_backup_count
from utils.timeout_manager import TimeoutManager

from lib.common.enums.backup_type import BackupType
from lib.common.enums.account_validation_status import ValidationStatus
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.ec2_username import EC2Username
from lib.common.enums.task_status import TaskStatus
from lib.common.error_codes import (
    TaskErrorCodeSyncAccountInstances,
    TaskErrorCodeSyncAccountVolumes,
)
from lib.dscc.backup_recovery.aws_protection.common.models.asset_set import AssetSet
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag

from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import (
    CSPVolumeListModel,
    CSPVolumeModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import (
    CSPMachineInstanceListModel,
    CSPMachineInstanceModel,
)
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.aws_boto3.remote_ssh_manager import RemoteConnect
from lib.platform.kafka.kafka_manager import KafkaManager
from lib.platform.host.io_manager import IOManager
from lib.platform.host.io_steps import (
    copy_vdbench_custom_config_file_to_ec2_instance,
    copy_vdbench_executable_to_ec2_instance,
    create_vdbench_config_file_for_generating_files_and_dirs,
    create_vdbench_config_file_in_ec2_instance,
    install_java_in_remote_host,
    run_vdbench,
)
from lib.platform.aws_boto3.models.instance import Instance

from azure.mgmt.compute.models import VirtualMachine

import tests.steps.aws_protection.backup_steps as BackupSteps
import tests.steps.aws_protection.restore_steps as RestoreSteps
import tests.steps.aws_protection.inventory_manager_steps as IMS
import tests.steps.aws_protection.cloud_account_manager_steps as CAMS
import tests.steps.aws_protection.eks.csp_eks_inventory_steps as EKSInvSteps
import tests.steps.aws_protection.assets.standard_asset_creation_steps as SA
from tests.steps.tasks import tasks
from tests.e2e.aws_protection.context import Context


logger = logging.getLogger()


# region Tags


def tag_aws_assets(
    context: Context,
    aws: AWS,
    asset_id_list: list[str],
    asset_type_list: list[AssetType],
    key: str,
    value: str,
):
    """Create and Add a Tag using 'key' and 'value' to all AWS Assets using the provided CSP Asset IDs and Types

    Args:
        context (Context): The Context
        aws (AWS): AWS Account
        asset_id_list (list[str]): list of CSP Asset IDs
        asset_type_list (list[str]): list of CSP Asset Types
        key (str): Tag Key
        value (str): Tag Value
    """
    logger.info(f"Tagging with {key}:{value} aws resources {asset_id_list} types: {asset_type_list}")

    tag = Tag(Key=key, Value=value)
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        aws_resource = None
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            # get AWS Asset ID from CSP Asset cspInfo.id
            ec2_instance_id = context.inventory_manager.get_csp_machine_instance_by_id(csp_machine_id=asset_id).cspId
            aws_resource = aws.ec2.get_ec2_instance_by_id(ec2_instance_id=ec2_instance_id)
            # Set test case specific tags to the standard EC2
            aws.ec2.create_tags_to_different_aws_resource_types_by_id(
                resource_ids_list=[aws_resource.id], tags_list=[tag]
            )

        elif asset_type == AssetType.CSP_VOLUME:
            # get AWS Asset ID from CSP Asset cspInfo.id
            ebs_volume_id = context.inventory_manager.get_csp_volume_by_id(csp_volume_id=asset_id).cspId
            aws_resource = aws.ebs.get_ebs_volume_by_id(volume_id=ebs_volume_id)
            # Set test case specific tags to the standard EBS
            aws.ebs.create_ebs_volume_tags(volume=aws_resource, tags_list=[tag])

    logger.info(f"Tags added {key}:{value} aws resources {asset_id_list} types: {asset_type_list}")


def untag_aws_assets(
    context: Context,
    aws: AWS,
    asset_id_list: list[str],
    asset_type_list: list[AssetType],
    key: str,
    value: str,
):
    """Create and Remove a Tag using 'key' and 'value' from all AWS Assets using the provided CSP Asset IDs and Types

    Args:
        context (Context): The Context
        aws (AWS): AWS Account
        asset_id_list (list[str]): list of CSP Asset IDs
        asset_type_list (list[str]): list of CSP Asset Types
        key (str): Tag Key
        value (str): Tag Value
    """

    logger.info(f"Removing tags from aws resources {asset_id_list}")

    tag = Tag(Key=key, Value=value)
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        aws_resource = None
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            # get AWS Asset ID from CSP Asset cspInfo.id
            ec2_instance_id = context.inventory_manager.get_csp_machine_instance_by_id(csp_machine_id=asset_id).cspId
            aws_resource = aws.ec2.get_ec2_instance_by_id(ec2_instance_id=ec2_instance_id)
            # Set test case specific tags to the standard EC2
            aws.ec2.remove_tags_from_different_aws_resources_by_id(
                aws_resource_id_list=[aws_resource.id], tags_list=[tag]
            )

        elif asset_type == AssetType.CSP_VOLUME:
            # get AWS Asset ID from CSP Asset cspInfo.id
            ebs_volume_id = context.inventory_manager.get_csp_volume_by_id(csp_volume_id=asset_id).cspId
            aws_resource = aws.ebs.get_ebs_volume_by_id(volume_id=ebs_volume_id)
            # Set test case specific tags to the standard EBS
            aws.ec2.remove_tags_from_different_aws_resources_by_id(
                aws_resource_id_list=[aws_resource.id], tags_list=[tag]
            )

    logger.info(f"Tags removed from aws resources {asset_id_list}")


def validate_key_pair(aws: AWS, key_pair_name: str) -> bool:
    """Ensures a 'key_pair_name' exists in the 'AWS' provided. A 'key_pair_name' is created if it does not exist.

    Args:
        aws (AWS): AWS Account
        key_pair_name (str): The name of the key_pair to validate

    Returns:
        bool: Returns True if the key_pair_name does not exist and a new key_pair is created, False otherwise.
    """
    # if the key pair doesn't exist
    if not aws.ec2.get_ec2_key_pair(key_name=key_pair_name):
        logger.info(f"key pair does not exist: {key_pair_name}")
        # create a new key_pair
        aws.ec2.create_ec2_key_pair(key_name=key_pair_name)
        return True

    logger.info(f"key pair exists: {key_pair_name}")
    return False


# endregion

# region Assets


def terminate_ec2_and_delete_all_volumes(context: Context, instance_name: str):
    """
    Terminate Ec2 instance and delete its volumes

    Args:
        context (Context): Context object
        instance_name (str): Name of the EC2 instance to be terminated
    """
    logger.info(f"Terminate instance {instance_name}")
    ec2_instance_filter = f"name eq '{instance_name}'"
    ec2_instances: CSPMachineInstanceListModel = IMS.get_csp_instances(context, filter=ec2_instance_filter)
    if ec2_instances.total == 0:
        logger.warn(f"Instance was not found {instance_name}")
        return
    ec2_instance = ec2_instances.items[0]
    context.aws_one.ec2.stop_and_terminate_ec2_instance(ec2_instance.cspId)
    logger.info(f"Instance terminated {ec2_instance.cspId}")
    root_device = ec2_instance.cspInfo.rootDevice
    for info in ec2_instance.volumeAttachmentInfo:
        if info.device != root_device:
            logger.info(f"Delete volume {info.attachedTo.name}")
            # get CSP Volume by "name" to get the "cspId" for AWS
            logger.info(f"resourceUri = {info.attachedTo.resource_uri}")
            csp_volume_id = info.attachedTo.resource_uri.split("/")[-1]
            logger.info(f"csp_volume_id = {csp_volume_id}")
            csp_volume = context.inventory_manager.get_csp_volume_by_id(csp_volume_id=csp_volume_id)
            logger.info(f"csp_volume.cspId = {csp_volume.cspId}")
            context.aws_one.ebs.delete_volume(csp_volume.cspId)
            logger.info(f"Volume deleted {info.attachedTo.name}")


# endregion

# region Kafka / Headers / Messages


def get_kafka_headers(kafka_manager: KafkaManager, ce_type: str, customer_id: str) -> dict:
    """
    Get Kafka headers

    Args:
        kafka_manager (KafkaManager): Kafka Manager
        ce_type (str): ce type
        customer_id (str): customer ID
    Returns:
        dict: Dict of header details
    """
    headers = {
        "ce_id": kafka_manager.account_id,
        "ce_source": kafka_manager.account_id,
        "ce_specversion": b"1.0",
        "ce_type": ce_type.encode("utf-8"),
        "ce_partitionkey": kafka_manager.account_id,
        "ce_customerid": customer_id.encode("utf-8"),
        "ce_tracestate": kafka_manager.account_id,
        "ce_time": b"2022-04-12T20:25:32.247125707Z",
    }

    return headers


def send_kafka_message(kafka_manager: KafkaManager, requested_event, event_type: str, customer_id: str):
    """
    Send kafka message

    Args:
        kafka_manager (KafkaManager): Kafka Manager
        requested_event: requested event
        event_type (str): event type
        customer_id (str): customer ID
    """
    kafka_headers = get_kafka_headers(kafka_manager=kafka_manager, ce_type=event_type, customer_id=customer_id)
    kafka_manager.send_message(event=requested_event, user_headers=kafka_headers)


# endregion

# region Writing/Validating Data / Connecting to EC2 Instance / DMCore / EC2 Folder Creations / VDBench


def write_data(context: Context, instance: Instance):
    """
    Write_data method will perform IO on instance for which the user is passing

    Args:
        context (Context): Specify the context
        instance (Instance): EC2 instance
    """
    # Write some data on EC2 instance
    copy_vdbench_executable_to_ec2_instance(context=context, ec2_instance_id=instance)
    create_vdbench_config_file_in_ec2_instance(context=context, instance=instance)
    assert run_vdbench(context=context, instance=instance), f"IO failed on ec2 instance '{instance}'"


def write_and_validate_data_vdbench(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    key_file: str = None,
    source_instance_id: str = None,
    file_count: int = 2,
    file_size: str = "1g",
    dir_name: str = "/dir1",
    depth: int = 1,
    width: int = 2,
    validate: bool = False,
):
    """write and validate vdbench method will generate files and directories with data

    Args:
        context (Context): context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 Instance ID
        key_file (str): Key Pair File Name to connect to EC2 instance
        source_instance_id (str, optional): Instance ID from which we are restoring. Defaults to None.
        file_count (int, optional): Total number of files need to be generated. Defaults to 2.
        file_size (str, optional): File size. Defaults to "1g".
        dir_name (str, optional): Source directory name. Defaults to "/dir1".
        depth (int, optional): Depth of directories. Defaults to 1.
        width (int, optional): Number of sub directories to be created under parent directory. Defaults to 2.
        validate (bool, optional): Data validation flag. Defaults to False.
    Usage:
        Write data -> write_and_validate_data_vdbench(context=context, instance=ec2_instance)
        Validate data -> write_and_validate_data_vdbench(context=context, instance=ec2_instance, validate=True)
    """
    client = connect_to_ec2_instance(
        context=context,
        aws=aws,
        account_id=account_id,
        ec2_instance_id=ec2_instance_id,
        key_file=key_file,
        source_aws_ec2_instance_id=source_instance_id,
    )

    io_manager = IOManager(context=context, client=client)

    if not validate:
        copy_vdbench_executable_to_ec2_instance(io_manager=io_manager)
        install_java_in_remote_host(io_manager=io_manager)

    create_vdbench_config_file_for_generating_files_and_dirs(
        context=context,
        file_count=file_count,
        file_size=file_size,
        dir_name=dir_name,
        depth=depth,
        width=width,
        io_manager=io_manager,
    )
    assert run_vdbench(io_manager=io_manager, validate=validate), f"IO failed on ec2 instance '{ec2_instance_id}'"
    client.close_connection()


def azure_write_and_validate_data_vdbench(
    context: Context,
    azure: Azure,
    vm_name: str,
    resource_group_name: str,
    username: str,
    key_file: str = None,
    file_count: int = 2,
    file_size: str = "1g",
    dir_name: str = "/dir1",
    depth: int = 1,
    width: int = 2,
    validate: bool = False,
):
    """write and validate vdbench method will generate files and directories with data

    Args:
        context (Context): context object
        azure (Azure): Azure Factory object
        vm_name (str): Azure VM Name
        username (str): Username of the VM provided while creation
        resource_group_name (str): Azure resource group name under which the VM is present
        key_file (str): Key Pair File Name to connect to EC2 instance
        source_instance_id (str, optional): Instance ID from which we are restoring. Defaults to None.
        file_count (int, optional): Total number of files need to be generated. Defaults to 2.
        file_size (str, optional): File size. Defaults to "1g".
        dir_name (str, optional): Source directory name. Defaults to "/dir1".
        depth (int, optional): Depth of directories. Defaults to 1.
        width (int, optional): Number of sub directories to be created under parent directory. Defaults to 2.
        validate (bool, optional): Data validation flag. Defaults to False.
    Usage:
        Write data -> write_and_validate_data_vdbench(context=context, instance=ec2_instance)
        Validate data -> write_and_validate_data_vdbench(context=context, instance=ec2_instance, validate=True)
    """
    client: RemoteConnect = connect_to_azure_vm(
        context=context,
        azure=azure,
        vm_name=vm_name,
        username=username,
        resource_group_name=resource_group_name,
        key_file=key_file,
    )
    try:
        io_manager = IOManager(context=context, client=client)
        logger.info(f"Remote connection started to VM {vm_name}")

        if not validate:
            copy_vdbench_executable_to_ec2_instance(io_manager=io_manager)
            install_java_in_remote_host(io_manager=io_manager)
            logger.info("VD BENCH binary copied.")

        create_vdbench_config_file_for_generating_files_and_dirs(
            context=context,
            file_count=file_count,
            file_size=file_size,
            dir_name=dir_name,
            depth=depth,
            width=width,
            io_manager=io_manager,
        )

        assert run_vdbench(io_manager=io_manager, validate=validate), f"IO failed on vm: '{vm_name}'"
        client.close_connection()
    except Exception as e:
        logger.error(f"DMCore action failed: {e}")
        client.close_connection()
        raise e


def write_and_validate_data_vdbench_with_custom_config_file(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    key_file: str,
    config_file_name: str,
    source_instance_id: str = None,
    validate: bool = False,
):
    """This method will write and validate data using custom vdbench config file

    Args:
        context (Context): context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 Instance ID
        key_file (str): Key Pair File Name to connect to EC2 instance
        config_file_name (str): Custom config file name
        source_instance_id (str, None): Source Instance ID used to get the username to connect to ec2_instance_id.
                                        Defaults to None.
        validate (bool, optional): Data validation flag. Defaults to False.
    Usage:
        Write data -> write_and_validate_data_vdbench_with_custom_config_file(
        context=context,
        aws=context.aws_one,
        account_id=context.aws_account_id,
        ec2_instance_id="i-056158f9d1055bfb8"
        key_file="key_file_name",
        config_file_name=context.vdbench_custom_config_file
    )
        Validate data -> write_and_validate_data_vdbench_with_custom_config_file(
        context=context,
        aws=context.aws_one,
        account_id=context.aws_account_id,
        ec2_instance_id="i-056158f9d1055bfb8"
        key_file="key_file_name",
        config_file_name=context.vdbench_custom_config_file
        source_instance_id="i-056158f9d1055bfb9" # only required if running on a restored instance
        validate=True
    )
    """
    client = connect_to_ec2_instance(
        context=context,
        aws=aws,
        account_id=account_id,
        ec2_instance_id=ec2_instance_id,
        key_file=key_file,
        source_aws_ec2_instance_id=source_instance_id,
    )
    io_manager = IOManager(context=context, client=client)

    copy_vdbench_executable_to_ec2_instance(io_manager=io_manager)

    install_java_in_remote_host(io_manager=io_manager)
    copy_vdbench_custom_config_file_to_ec2_instance(io_manager=io_manager)
    assert run_vdbench(
        io_manager=io_manager,
        validate=validate,
        custom_config_file_name=config_file_name,
    ), f"IO failed on ec2 instance '{ec2_instance_id}'"
    client.close_connection()


def write_and_validate_data_dm_core(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    validation: bool = False,
    key_file: str = None,
    source_aws_ec2_instance_id: str = None,
    percentage_to_fill: int = 5,
    copy_dm_core: bool = False,
):
    """SSH into the 'ec2_instance' and writes / validates data

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
        validation (bool, optional): Whe set to True, data will be validated, False will write data. Defaults to False.
        key_file (str, optional): EC2 Key File path. Defaults to None.
        source_aws_ec2_instance_id(str, optional): EC2 ID from AWS Console. MUST provide value if data has to be
            written/validated on a restored EC2. The reason is that the restored instance does not provide AMI values
            as the AMI is set as 'Private'. Defaults to None.
        percentage_to_fill (int): Percentage to fill / write data. Defaults to 5.
        copy_dm_core (bool): Copy the dm core package. Defaults to False.
    """
    client: RemoteConnect = connect_to_ec2_instance(
        context=context,
        aws=aws,
        account_id=account_id,
        ec2_instance_id=ec2_instance_id,
        key_file=key_file,
        source_aws_ec2_instance_id=source_aws_ec2_instance_id,
    )

    try:
        ec2_status = aws.ec2.ec2_client.describe_instance_status(InstanceIds=[ec2_instance_id])
        logger.info(f"Ec2 {ec2_instance_id} status {ec2_status['InstanceStatuses']}")

        io_manager = IOManager(context=context, client=client)
        logger.info(f"Remote connection started to {ec2_instance_id}")

        if not validation or copy_dm_core:
            io_manager.copy_dmcore_binary_to_remote_host()
            logger.info("DM CORE binary copied.")

        logger.info("DM CORE started")
        status = io_manager.run_dmcore(
            validation=validation,
            percentage_to_fill=percentage_to_fill,
        )
        client.close_connection()
    except Exception as e:
        logger.error("DM copy after connecting to ec2 failed: {e}")
        client.close_connection()
        raise e

    logger.info(f"DM CORE finished with status: {status}")
    assert status


def connect_to_ec2_instance(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    key_file: str = None,
    source_aws_ec2_instance_id: str = None,
) -> RemoteConnect:
    """SSH into the 'ec2_instance'

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
        key_file (str, optional): EC2 Key File path. Defaults to None.
        source_aws_ec2_instance_id(str, optional): EC2 ID from AWS Console
        MUST provide value if data has to be written/validated on a restored EC2.
        The reason is that the restored instance does not provide AMI values as the AMI is set as 'Private'.
        Defaults to None.
    Returns:
        RemoteConnect: Returns remote connect client
    """

    ec2 = aws.ec2.get_ec2_instance_by_id(ec2_instance_id)

    ec2_instance = aws.ec2.get_ec2_instance_by_id(source_aws_ec2_instance_id) if source_aws_ec2_instance_id else ec2
    user_name: str = EC2Username.get_ec2_username(ec2_instance=ec2_instance)

    key_file = f"{key_file}.pem" if key_file else f"{context.key_pair}.pem"
    public_dns_name = ""
    try:
        public_dns_name = aws.ec2.wait_for_public_dns(ec2_instance_id)
        ec2_address = public_dns_name
    except Exception as e:
        logger.info(f"RemoteConnect will use ip instead of public DNS. Error: {e}")
        ec2_address = ec2.public_ip_address

    ec2_state = aws.ec2.get_instance_state(ec2_instance_id)
    logger.info(f"Instance state: {ec2_state}")
    aws.ec2.wait_instance_status_ok(ec2)

    logger.info(f"Remote connection starting to {ec2_instance_id}, account {account_id}")
    logger.info(f"Key pair file {key_file}")
    logger.info(f"ec2 ip: {ec2.public_ip_address}, public dns: {public_dns_name}, connect address: {ec2_address}")
    logger.info(f"Searching in directory: {os.getcwd()}")
    logger.info(f"Private key pair exists: {os.path.exists(key_file)}")
    logger.info(f"env HTTP_PROXY: {os.getenv('HTTP_PROXY')}")
    logger.info(f"context proxy: {context.proxy}")

    client = None

    retries = 20
    for i in range(retries):
        try:
            logger.info("Starting ssh ec2 tunnel connection")
            client = RemoteConnect(
                instance_dns_name=ec2_address,
                username=user_name,
                pkey=paramiko.RSAKey.from_private_key_file(key_file),
                window_size=52428800,
                packet_size=327680,
            )
            if client:
                break
        except Exception as e:
            logger.info(f"Connection failed retrying {i}/{retries}: {e}")
            try:
                if "invalid start byte" in str(e):
                    logger.warn("This usually means that ec2 is not yet ready to connect.")
                    time.sleep(60)
            except Exception as parse_e:
                logger.warn(f"cant parse {e} - {parse_e}")

    assert client, "RemoteConnect object was not created."
    return client


def write_data_to_root_volume_and_create_snapshot(
    context: Context,
    aws: AWS,
    key_pair: str,
    aws_ec2_instance_id: str,
    aws_ebs_volume_id: str = None,
    aws_ebs_snapshot_description: str = "Automation - Testing Import Snapshot Restore",
    root_volume_data_write_folder: str = "/DataWrite",
    root_device: str = "xvda",
    dm_core_data_folder: str = "test",
    percentage_to_fill: int = 5,
    create_snapshot: bool = True,
):
    """Create folder on EC2 root volume, write data, & create snapshot

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        key_pair (str): EC2 key pair name
        aws_ec2_instance_id (str): EC2 Instance ID
        aws_ebs_volume_id (str, optional): EBS Volume ID. Defaults to None.
        aws_ebs_snapshot_description (str, optional): EBS Volume snapshot description. Defaults to "Automation - Testing Import Snapshot Restore".
        root_volume_data_write_folder (str, optional): Volume folder name path to write. Defaults to "/DataWrite".
        root_device (str, optional): Volume device attachment. Defaults to "xvda".
        dm_core_data_folder (str, optional): Folder name for DM Core Data. Defaults to "test".
        percentage_to_fill (int, optional): Percentage to fill / write data. Defaults to 5.
        create_snapshot (bool): Create snapshot of the volume. Defaults to True.

    Returns:
        AWS Snapshot Object: AWS EBS Snapshot of root volume if create_snapshot else None
    """

    logger.info(f"Creating {root_volume_data_write_folder} folder on EC2 {aws_ec2_instance_id} for writing data")
    create_folder_on_ec2_instance(
        context=context,
        aws=aws,
        ec2_instance_id=aws_ec2_instance_id,
        account_id=context.aws_account_id,
        key_file=key_pair,
        folder_name=root_volume_data_write_folder,
    )

    logger.info(f"Writing data to {aws_ec2_instance_id} using DMCore")
    run_dm_core_on_root_device(
        context=context,
        aws=aws,
        ec2_instance_id=aws_ec2_instance_id,
        device=root_device,
        export_file_name=f"{root_volume_data_write_folder}/{dm_core_data_folder}",
        account_id=context.aws_account_id,
        key_file=key_pair,
        validation=False,
        percentage_to_fill=percentage_to_fill,
    )

    if create_snapshot:
        time.sleep(50)  # giving time for DMCore actions to complete before creating a snapshot
        logger.info(f"Creating Snapshot {aws_ebs_snapshot_description}")
        aws_ebs_snapshot = aws.ebs.create_ebs_volume_snapshot(
            volume_id=aws_ebs_volume_id,
            description=aws_ebs_snapshot_description,
        )
        logger.info(f"Created Snapshot is {aws_ebs_snapshot}")

        return aws_ebs_snapshot


def data_validation_for_restored_root_ebs(
    context: Context,
    aws: AWS,
    key_pair: str,
    restored_aws_ebs_volume_id: str,
    aws_ec2_instance_id: str = None,
    restored_volume_data_validation_folder: str = "/mnt/DataRead",
    restored_volume_device: str = "xvdh",
    percentage_to_fill: int = 5,
    root_volume_data_write_folder: str = "/DataWrite",
    dm_core_data_folder: str = "test",
):
    """Data validation for restored root EBS

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        key_pair (str): EC2 ey pair name
        restored_aws_ebs_volume_id (str): Restored EBS Volume ID
        aws_ec2_instance_id (str, optional): EC2 Instance ID. Defaults to None.
        restored_volume_data_validation_folder (str, optional): Volume folder name path to read. Defaults to "/mnt/DataRead".
        restored_volume_device (str, optional): Restored Volume device attachment. Defaults to "xvdh".
        percentage_to_fill (int, optional): Percentage to fill / write data. Defaults to 5.
        root_volume_data_write_folder (str, optional): Volume folder name path to write. Defaults to "/DataWrite".
        dm_core_data_folder (str, optional): Folder name for DM Core Data. Defaults to "test".
    """
    logger.info(
        f"Creating {restored_volume_data_validation_folder} folder on EC2 {aws_ec2_instance_id} for data validation"
    )
    create_folder_on_ec2_instance(
        context=context,
        aws=aws,
        ec2_instance_id=aws_ec2_instance_id,
        account_id=context.aws_account_id,
        key_file=key_pair,
        folder_name=restored_volume_data_validation_folder,
    )
    time.sleep(30)

    logger.info(f"Getting file system of the restored volume for device {restored_volume_device}")
    file_system: str = get_device_file_system(
        context=context,
        aws=aws,
        ec2_instance_id=aws_ec2_instance_id,
        key_file=key_pair,
        account_id=context.aws_account_id,
        device=restored_volume_device,
    )

    logger.info(
        f"Mounting File System {file_system} on {restored_volume_data_validation_folder} folder for data validation"
    )
    mount_drive_on_ec2_instance(
        context=context,
        aws=aws,
        ec2_instance_id=aws_ec2_instance_id,
        key_file=key_pair,
        account_id=context.aws_account_id,
        mount_device=file_system,
        mount_folder=restored_volume_data_validation_folder,
    )
    time.sleep(30)  # time for volume mount to complete before validating data

    logger.info(f"Validating data on restored volume {restored_aws_ebs_volume_id}")
    run_dm_core_on_root_device(
        context=context,
        aws=aws,
        ec2_instance_id=aws_ec2_instance_id,
        key_file=key_pair,
        account_id=context.aws_account_id,
        device=restored_volume_device,
        export_file_name=f"{restored_volume_data_validation_folder}{root_volume_data_write_folder}/{dm_core_data_folder}",
        validation=True,
        percentage_to_fill=percentage_to_fill,
    )


def create_folder_on_ec2_instance(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    key_file: str = None,
    source_aws_ec2_instance_id: str = None,
    folder_name: str = "/write-data",
):
    """Creates folder on EC2 root volume

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
        key_file (str, optional): EC2 Key File path. Defaults to None.
        source_aws_ec2_instance_id(str, optional): EC2 ID from AWS Console
        MUST provide value if data has to be written/validated on a restored EC2.
        The reason is that the restored instance does not provide AMI values as the AMI is set as 'Private'.
        Defaults to None.
        folder_name (str, optional): name of the folder to be created. Defaults to /write-data
    """
    client = connect_to_ec2_instance(
        context=context,
        aws=aws,
        account_id=account_id,
        ec2_instance_id=ec2_instance_id,
        key_file=key_file,
        source_aws_ec2_instance_id=source_aws_ec2_instance_id,
    )

    ec2_status = aws.ec2.ec2_client.describe_instance_status(InstanceIds=[ec2_instance_id])
    logger.info(f"Ec2 {ec2_instance_id} status {ec2_status['InstanceStatuses']}")

    io_manager = IOManager(context=context, client=client)
    logger.info(f"Remote connection started to {ec2_instance_id}")

    std_out = io_manager.client.execute_command(command=f"mkdir {folder_name}")
    logger.info(f"Folder {folder_name} created on EC2 instance {ec2_instance_id}, {std_out}")
    client.close_connection()


def get_device_file_system(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    device: str,
    key_file: str = None,
    source_aws_ec2_instance_id: str = None,
) -> str:
    """Returns the File System of the device which can then be mounted to a folder
    This will be useful for restored volumes (specifically for root volume)

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
        device (str): Device path on which data has to be written / verified. Eg. xvda, xvdf, etc.
        key_file (str, optional): EC2 Key File path. Defaults to None.
        source_aws_ec2_instance_id(str, optional): EC2 ID from AWS Console
        MUST provide value if data has to be written/validated on a restored EC2.
        The reason is that the restored instance does not provide AMI values as the AMI is set as 'Private'.
        Defaults to None.

    Returns:
        (str): file_system
    """
    client = connect_to_ec2_instance(
        context=context,
        aws=aws,
        account_id=account_id,
        ec2_instance_id=ec2_instance_id,
        key_file=key_file,
        source_aws_ec2_instance_id=source_aws_ec2_instance_id,
    )

    ec2_status = aws.ec2.ec2_client.describe_instance_status(InstanceIds=[ec2_instance_id])
    logger.info(f"Ec2 {ec2_instance_id} status {ec2_status['InstanceStatuses']}")

    io_manager = IOManager(context=context, client=client)
    logger.info(f"Remote connection started to {ec2_instance_id}")

    std_out = io_manager.client.execute_command(command=f"sudo fdisk -l  | grep {device} | grep 'Linux filesystem'")
    logger.info(f"Command output {std_out}")  # eg. output '/dev/xvdk1   24576 16777182 16752607   8G Linux filesystem'

    file_system: str = std_out[0].split()[0].strip()
    logger.info(f"Device {device} file system is on {file_system}")
    client.close_connection()
    return file_system


def mount_drive_on_ec2_instance(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    mount_device: str,
    mount_folder: str,
    key_file: str = None,
    source_aws_ec2_instance_id: str = None,
):
    """Mounts specified EC2 drive on the given folder

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
        mount_device (str): Device path which has to be mounted. Eg. xvda, xvdf, etc.
        mount_folder (str): Folder path on which mount_device has to be mounted. Eg. /test, etc.
        key_file (str, optional): EC2 Key File path. Defaults to None.
        source_aws_ec2_instance_id(str, optional): EC2 ID from AWS Console
        MUST provide value if data has to be written/validated on a restored EC2.
        The reason is that the restored instance does not provide AMI values as the AMI is set as 'Private'.
        Defaults to None.
    """
    client = connect_to_ec2_instance(
        context=context,
        aws=aws,
        account_id=account_id,
        ec2_instance_id=ec2_instance_id,
        key_file=key_file,
        source_aws_ec2_instance_id=source_aws_ec2_instance_id,
    )

    ec2_status = aws.ec2.ec2_client.describe_instance_status(InstanceIds=[ec2_instance_id])
    logger.info(f"Ec2 {ec2_instance_id} status {ec2_status['InstanceStatuses']}")

    io_manager = IOManager(context=context, client=client)
    logger.info(f"Remote connection started to {ec2_instance_id}")

    std_out = io_manager.client.execute_command(command=f"mount {mount_device} {mount_folder}")
    logger.info(f"Device {mount_device} mounted on {mount_folder}, {std_out}")
    client.close_connection()


def run_dm_core_on_root_device(
    context: Context,
    aws: AWS,
    account_id: str,
    ec2_instance_id: str,
    device: str,
    export_file_name: str,
    validation: bool = False,
    key_file: str = None,
    source_aws_ec2_instance_id: str = None,
    percentage_to_fill=5,
    copy_dm_core=False,
):
    """SSH into the 'ec2_instance' and writes / validates data

    Args:
        context (Context): Context object
        aws (AWS): AWS object
        account_id (str): AWS Account ID
        ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
        device (str): Device path on which data has to be written / verified. Eg. xvda, xvdf, etc.
        export_file_name (str): Folder on which data has to be written / verified.
                                Provide a folder name on EC2 root volume.
                                This is the path on which a volume is mounted or a folder on the root volume
        validation (bool, optional): Whe set to True, data will be validated, False will write data. Defaults to False.
        key_file (str, optional): EC2 Key File path. Defaults to None.
        source_aws_ec2_instance_id (str, optional): EC2 ID from AWS Console. MUST provide value if data has to be
            written/validated on a restored EC2. The reason is that the restored instance does not provide AMI values as
            the AMI is set as 'Private'. Defaults to None.
        percentage_to_fill (int, optional): Percentage to fill / write data. Defaults to 5.
        copy_dm_core (bool, optional): Copy dm core to device. Defaults to False.
    """
    client = connect_to_ec2_instance(
        context=context,
        aws=aws,
        account_id=account_id,
        ec2_instance_id=ec2_instance_id,
        key_file=key_file,
        source_aws_ec2_instance_id=source_aws_ec2_instance_id,
    )

    ec2_status = aws.ec2.ec2_client.describe_instance_status(InstanceIds=[ec2_instance_id])
    logger.info(f"Ec2 {ec2_instance_id} status {ec2_status['InstanceStatuses']}")

    io_manager = IOManager(context=context, client=client)
    logger.info(f"Remote connection started to {ec2_instance_id}")

    if not validation or copy_dm_core:
        io_manager.copy_dmcore_binary_to_remote_host()
        logger.info("DM CORE binary copied.")

    # time.sleep(10)
    logger.info("DM CORE started")
    status = io_manager.run_dm_core_on_custom_drive(
        device=device,
        validation=validation,
        percentage_to_fill=percentage_to_fill,
        export_file_name=export_file_name,
    )
    client.close_connection()
    logger.info("DM CORE finished")
    assert status


def connect_to_azure_vm(
    context: AzureContext,
    azure: Azure,
    vm_name: str,
    username: str,
    resource_group_name: str,
    key_file: str = None,
) -> RemoteConnect:
    """SSH into the Azure VM

    Args:
        context (AzureContext): AzureContext object
        azure (Azure): AzureFactory object
        vm_name (str): Azure VM Name
        username (str): Username of the VM provided while creation
        resource_group_name (str): Azure resource group name under which the VM is present
        key_file (str, optional): SSH key file name. Defaults to None.

    Returns:
        RemoteConnect: RemoteConnect object with open connection to the VM
    """

    vm: VirtualMachine = azure.az_vm_manager.get_vm_by_name(resource_group_name=resource_group_name, vm_name=vm_name)
    vm_public_ip = azure.az_vm_manager.get_vm_public_ip(vm=vm, resource_group_name=resource_group_name)

    assert vm_public_ip, f"VM {vm_name} in RG: {resource_group_name} does not have a public IP"

    key_file = f"{key_file}.pem" if key_file else f"{context.key_pair}.pem"

    logger.info(f"Remote connection starting to {vm_name}")
    logger.info(f"Key pair file {key_file}")
    logger.info(f"VM IP: {vm_public_ip}")
    logger.info(f"Searching in directory: {os.getcwd()}")
    logger.info(f"Private key pair exists: {os.path.exists(key_file)}")
    logger.info(f"env HTTP_PROXY: {os.getenv('HTTP_PROXY')}")
    logger.info(f"context proxy: {context.proxy}")

    client = None

    retries = 20
    for i in range(retries):
        try:
            logger.info("Starting ssh ec2 tunnel connection")
            client = RemoteConnect(
                instance_dns_name=vm_public_ip,
                username=username,
                pkey=paramiko.RSAKey.from_private_key_file(key_file),
                window_size=52428800,
                packet_size=327680,
            )
            if client:
                break
        except Exception as e:
            logger.info(f"Connection failed retrying {i}/{retries}: {e}")
            try:
                if "invalid start byte" in str(e):
                    logger.warn("This usually means that VM is not yet ready to connect.")
                    time.sleep(60)
            except Exception as parse_e:
                logger.warn(f"cant parse {e} - {parse_e}")

    assert client, "RemoteConnect object was not created."
    return client


def azure_write_and_validate_data_dm_core(
    context: AzureContext,
    azure: Azure,
    vm_name: str,
    resource_group_name: str,
    username: str,
    key_file: str = None,
    percentage_to_fill: int = 5,
    copy_dm_core: bool = False,
    validation: bool = False,
):
    """SSH into the Azure VM and writes / validates data

    Args:
        context (AzureContext): AzureContext object
        azure (Azure): Azure Factory object
        vm_name (str): Azure VM Name
        username (str): Username of the VM provided while creation
        resource_group_name (str): Azure resource group name under which the VM is present
        key_file (str, optional): SSH key file name. Defaults to None.
        percentage_to_fill (int, optional): Percentage to fill / write data. Defaults to 5.
        copy_dm_core (bool, optional): Copy the dm core package. Defaults to False.
        validation (bool, optional): Validates the written data using dmcore. Defaults to False
    """
    client: RemoteConnect = connect_to_azure_vm(
        context=context,
        azure=azure,
        vm_name=vm_name,
        username=username,
        resource_group_name=resource_group_name,
        key_file=key_file,
    )

    try:
        io_manager = IOManager(context=context, client=client)
        logger.info(f"Remote connection started to VM {vm_name}")

        if not validation or copy_dm_core:
            io_manager.copy_dmcore_binary_to_remote_host()
            logger.info("DM CORE binary copied.")

        logger.info("DM CORE started")
        status = io_manager.run_dmcore(
            validation=validation,
            percentage_to_fill=percentage_to_fill,
        )
        client.close_connection()
    except Exception as e:
        logger.error(f"DMCore action failed: {e}")
        client.close_connection()
        raise e

    logger.info(f"DM CORE finished with status: {status}")
    assert status


# endregion

# region Register/Unregister/Validate AWS Account / Stack / CFT


def register_aws_account_step(
    context: Context, aws_account_name: str, aws_account_id: str, aws: AWS = None
) -> CSPAccountModel:
    """
    Unregister the AWS account from DSCC if already present and re-registers it

    Args:
        context (Context): Specify the context
        aws_account_name (str): AWS account name
        aws_account_id (str): AWS account ID
        aws (AWS): If specified it will search for stack. When missing it will create new one to perform unprotect
    Returns:
        CSPAccountModel: Registered CSP Account
    """
    aws_arn = f"arn:aws:iam::{aws_account_id}:"
    logger.info(f"Registering account NAME: {aws_account_name} - ARN: {aws_arn}")
    csp_account = CAMS.get_csp_account_by_csp_name(context, account_name=aws_account_name, is_found_assert=False)
    if csp_account:
        if aws:
            create_stack_with_cloud_formation_template(
                context=context, csp_account_id=csp_account.id, aws=aws, stack_name="stack"
            )
        logger.info("Removing Regression test account")
        CAMS.delete_csp_account(context=context, csp_account_name=csp_account.name, unprotect_account=True)
    csp_account = CAMS.create_csp_account(context, aws_arn, aws_account_name, CspType.AWS)
    return csp_account


def register_account_and_create_standard_asset(
    context: Context,
    aws: AWS,
    account_id: str = "",
    account_name: str = "",
    asset_set: AssetSet = None,
    reregister_account: bool = False,
    aws_assets_only: bool = False,
    key_pair: str = "",
) -> AssetSet:
    """
    Register an AWS account and create standard asset

    Args:
        context (Context): Specify the context
        aws (AWS): AWS object
        account_id (str): AWS account name. Defaults to "".
        account_name (str): AWS account ID. Defaults to "".
        asset_set (AssetSet): Standard assets
        reregister_account (bool): Re-register the account. Defaults to False.
        aws_assets_only (bool): AWS assets only. Defaults to False.
        key_pair (str): Key pair to be used while creating standard asset. Defaults to "".
    Returns:
         AssetSet: Returns standard asset
    """
    if not account_id:
        account_id = context.aws_one_account_id
    if not account_name:
        account_name = context.aws_one_account_name
    if not asset_set:
        asset_set = context.asset_set_region_one_aws_one

    csp_account_before = CAMS.get_csp_account_by_csp_name(context, account_name=account_name, is_found_assert=False)
    logger.info(f"Account already registered: {csp_account_before}")
    if reregister_account or not csp_account_before:
        logger.info(f"Test account will be registered: {account_name}, reregister: {reregister_account}")
        csp_account = register_aws_account_step(context, account_name, account_id)

        # Clean AWS backups just to be sure that env is clear
        # TODO: delete backups, snapshots and amis from API (remove below two lines)
        if account_name == context.aws_one_account_name:
            context.aws_one.ec2.delete_all_amis()
            context.aws_one.ebs.delete_all_snapshots()
        if account_name == context.aws_two_account_name:
            context.aws_two.ec2.delete_all_amis()
            context.aws_two.ebs.delete_all_snapshots()

    else:
        csp_account = csp_account_before

    context.csp_account_id_aws_one = csp_account.id
    logger.info(f"Test account: {csp_account.id}")

    if reregister_account or not csp_account_before or csp_account.validationStatus != ValidationStatus.passed:
        create_stack_with_cloud_formation_template(
            context=context, csp_account_id=csp_account.id, aws=aws, stack_name="stack"
        )
        logger.info(f"Test stack created: {csp_account.id}")
        validate_aws_account_step(context, csp_account.id)
        logger.info(f"Test account validated: {csp_account.id}")

    key_pair = key_pair if key_pair else context.key_pair

    asset_set = SA.create_standard_assets(
        context=context,
        aws=aws,
        csp_account_name=account_name,
        asset_set=asset_set,
        region=aws.region_name,
        key_pair=key_pair,
        aws_assets_only=aws_assets_only,
    )
    return asset_set


def create_stack_with_cloud_formation_template(
    context: Context, csp_account_id: str, aws: AWS = None, stack_name: str = ""
):
    """
    Create stack with cloud formation template

    Args:
        context (Context): Specify the context
        csp_account_id (str): AWS account name. Defaults to "".
        aws (AWS): AWS object
        stack_name (str): Name of the stack to be created. Defaults to "".
    """
    cloud_formation_template = CAMS.get_csp_account_onboarding_template(context, csp_account_id)
    aws = aws if aws else context.aws_one
    stack_name = stack_name if stack_name else "stack"

    cf_stack = aws.cloud_formation.get_cf_stack(stack_name=stack_name)

    if cf_stack:
        logger.info(f"Deleting test stack: '{stack_name}'")
        aws.cloud_formation.delete_cf_stack(stack_name=stack_name)
    cf_status = aws.cloud_formation.create_cf_stack(
        stack_name=stack_name, template_body=cloud_formation_template.onboardingTemplate
    )
    if cf_status == "ROLLBACK_COMPLETE":
        roles_hpe = [
            "hpe-cam-backup-manager",
            "hpe-cam-data-extractor",
            "hpe-cam-restore-manager",
            "hpe-cam-configuration-validator",
            "hpe-cam-data-injector",
            "hpe-cam-inventory-manager",
        ]
        roles_aws = aws.iam.get_roles()
        assert set(roles_hpe).issubset(set(roles_aws))
    else:
        assert cf_status.stack_status == "CREATE_COMPLETE", "Creating the cloud formation failed"
    logger.info("CF Stack created")


def validate_aws_account_step(
    context: Context,
    csp_account_id: str,
    expected_validation_status: str = ValidationStatus.passed.value,
):
    """
    Validate AWS account on DSCC

    Args:
        context (Context): Specify the context
        csp_account_id (str): AWS account name.
        expected_validation_status (str): Expected validation status to compare. Defaults to ValidationStatus.passed.value
    """
    task_id = CAMS.validate_csp_account(context=context, csp_account_id=csp_account_id)
    task_status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=TimeoutManager.standard_task_timeout)

    if expected_validation_status == ValidationStatus.passed.value:
        assert task_status == TaskStatus.success.value.lower(), f"Validate account status: {task_status}"
    elif expected_validation_status == ValidationStatus.failed.value:
        assert task_status != TaskStatus.success.value.lower(), f"Validate account status: {task_status}"

    csp_account = CAMS.get_csp_account_by_csp_id(context=context, csp_account_id=csp_account_id)
    assert (
        csp_account.validationStatus.value == expected_validation_status
    ), f"Account Validation Status in DSCC: {csp_account.validationStatus}"


def validate_and_verify_csp_account(context: Context, csp_account_id: str):
    """
    Validate and verify CSP AWS account on DSCC

    Args:
        context (Context): Specify the context
        csp_account_id (str): CSP AWS account name to be validated
    """
    timeout = TimeoutManager.standard_task_timeout
    task_id = CAMS.validate_csp_account(context=context, csp_account_id=csp_account_id)
    status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=timeout, interval=30)
    assert status.upper() == TaskStatus.success.value

    fetched_csp_account = CAMS.get_csp_account_by_csp_id(context=context, csp_account_id=csp_account_id)
    validation_status = fetched_csp_account.validationStatus
    assert (
        validation_status == ValidationStatus.passed
    ), f" CSP Account {csp_account_id} ValidationStatus. Expected: 'PASSED' Actual: {validation_status.value}"

    # Trigger Inventory Account Sync
    task_id = context.inventory_manager.trigger_account_inventory_sync(account_id=csp_account_id)
    inventory_status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=timeout, interval=30)
    assert inventory_status.upper() == TaskStatus.success.value


def validate_csp_account_failure(context: Context, csp_account_id: str):
    """
    Validate CSP AWS account on DSCC

    Args:
        context (Context): Specify the context
        csp_account_id (str): CSP AWS account name to be validated
    """
    status = ""
    timeout = TimeoutManager.standard_task_timeout
    timeout_verify = TimeoutManager.standard_task_timeout + 600
    try:
        task_id = CAMS.validate_csp_account(context=context, csp_account_id=csp_account_id)
        status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=timeout, interval=30)
    except Exception:
        status = "ERROR IN TEST EXECUTION"
        logger.info(f"CSP Account {csp_account_id} validation has failed as expected due to insufficient permission")
    finally:
        if status:
            assert (
                status.upper() != TaskStatus.success.value
            ), "Fail: CSP Account validation has been successful without sufficient permission"

    fetched_csp_account = CAMS.get_csp_account_by_csp_id(context=context, csp_account_id=csp_account_id)
    validation_status = fetched_csp_account.validationStatus
    assert (
        validation_status == ValidationStatus.failed
    ), f"CSP Account {csp_account_id} ValidationStatus. Expected: 'FAILED' Actual: {validation_status.value}"

    # Trigger Inventory Account Sync and Validate error
    expected_error_message = "Unable to retrieve"
    task_id = context.inventory_manager.trigger_account_inventory_sync(account_id=csp_account_id)
    task_error = tasks.wait_for_task_error(task_id=task_id, user=context.user, timeout=timeout_verify, interval=30)
    assert expected_error_message in task_error, f"{task_error=} should be {expected_error_message=}"


def validate_csp_account_cleaned(aws: AWS):
    """Validate that there is no ec2 AMIs, RDS or EBS snapshots. Print findings and try to deleete them.

    Args:
        aws (AWS): AWS object
    """
    amis = aws.ec2.get_all_amis()
    ebs_snapshots = aws.ebs.get_all_snapshots()
    rds_snapshots_manual = aws.rds.get_all_db_snapshots(snapshot_type=RDSSnapshotType.MANUAL)
    rds_snapshots_automated = aws.rds.get_all_db_snapshots(snapshot_type=RDSSnapshotType.AUTOMATED)
    if amis["Images"]:
        logger.error(f"Amis list is not empty.\n Deleting:\n {amis}")
        aws.ec2.delete_all_amis()
    if ebs_snapshots["Snapshots"]:
        logger.error(f"EBS snapshots list is not empty.\nDeleting:\n {ebs_snapshots}")
        aws.ebs.delete_all_snapshots()
    if rds_snapshots_manual:
        logger.error(f"RDS manual snapshots list is not empty.\nDeleting:\n {rds_snapshots_manual}")
        aws.rds.delete_all_db_snapshots(snapshot_type=RDSSnapshotType.MANUAL)
    if rds_snapshots_automated:
        logger.error(
            f"RDS automated snapshots list is not empty.\n \
            Will not be deleted, first remove database.\n {rds_snapshots_automated}"
        )


def register_and_validate_csp_aws_account(
    context: Context,
    aws_account_id: str,
    aws_account_name: str,
    aws_session: AWS = None,
    refresh_timeout: int = 500,
    stack_name: str = "api-stack",
):
    """Register and validate aws account with k8s refresh task validation
    Args:
        context (Context): test context
        aws_account_id (str): AWS account id
        aws_account_name (str): AWS account name
        aws_session (AWS, optional): AWS session object. Defaults to None.
        refresh_timeout (int, optional): K8s refresh task timeout. Defaults to 500.
        stack_name (str, optional): Cloud formation stack name. Defaults to "api-stack".
    """
    if not aws_session:
        aws_session = context.aws_eks
    # This method will remove the account if already existed, then registers it
    csp_account = register_aws_account_step(context, aws_account_name, aws_account_id)
    logger.info(f"Successfully registered aws account: {aws_account_id} with name: {aws_account_name}")
    logger.debug(f"CSP account info {csp_account}")
    # resource_uri = csp_account.consoleUri.replace("data-services", "api/v1")

    # Download CFT and check CFT, if exists, remove and create a new one
    create_stack_with_cloud_formation_template(context, csp_account.id, aws=aws_session, stack_name=stack_name)

    # Validate AWS account
    validate_aws_account_step(
        context,
        csp_account.id,
        expected_validation_status=ValidationStatus.passed.value,
    )
    logger.info(f"Successfully validated aws account: {aws_account_id} with name: {aws_account_name}")

    # Wait for 100 seconds to trigger k8s refresh inventory task
    time.sleep(100)
    eks_k8s_refresh_task_list = tasks.get_tasks_by_name_and_resource(
        user=context.user,
        task_name=f"Refresh cloud service provider account EKS inventory [{aws_account_name}]",
        resource_uri=csp_account.resourceUri,
    )
    logger.info(f"task response: {eks_k8s_refresh_task_list}")
    if eks_k8s_refresh_task_list.total:
        task_id = eks_k8s_refresh_task_list.items[0].id
        task_status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=refresh_timeout)
        assert (
            task_status == TaskStatus.success.value.lower()
        ), f"eks k8s refresh failed, not able to list all the clusters: {task_status}"
        logger.info("Successfully refreshed eks inventory, now we can list the clusters")


# endregion

# region Refresh Inventory


def refresh_inventory_with_retry(
    context: Context,
    account_id: str,
    timeout: int = TimeoutManager.standard_task_timeout,
    retry_count: int = 5,
):
    """
    Refreshes inventory for the provided DSCC account. Retries 5 times by default if a conflict occurs during
    inventory refresh

    Args:
        context (Context): Specify the context
        account_id (str): CSP AWS account name to be refreshed
        timeout (int): Timeout for wait task. Defaults to TimeoutManager.standard_task_timeout
        retry_count (int): Number of retry attempts. Defaults to 5.
    """
    logger.info(f"Refreshing account {account_id} inventory")

    for i in range(retry_count + 1):
        task_id = context.inventory_manager.trigger_account_inventory_sync(account_id)
        refresh_task_status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=timeout, log_result=True)

        # If an error occurs, retrieve the task error message
        task_error_code: int = 0
        if refresh_task_status.upper() != TaskStatus.success.value:
            task_error_code = tasks.get_task_error_code(task_id, context.user)

        # If the refresh request failed with a retriable error code, and there are retry attempts remaining,
        # log a warning and retry the request.
        retriable_error_codes = [
            TaskErrorCodeSyncAccountInstances,
            TaskErrorCodeSyncAccountVolumes,
        ]
        if (task_error_code in retriable_error_codes) and (i < retry_count):
            logger.warn(f"Inventory Manager refresh retry required, task_error_code={task_error_code}")
            continue

        expected_error = "account refresh is already in progress"
        task_error = tasks.get_task_error(task_id, context.user)
        if expected_error in task_error:
            logger.warn(f"Expected error waiting 60 sec, retry {i} : {task_error}")
            time.sleep(60)
            continue

        # Assert on failure
        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"Refresh failure, refresh_task_status={refresh_task_status}, task_error_code={task_error_code}"
        break


def refresh_inventory_and_validate_csp_asset_count(
    context: Context, aws_account_id: str, account_id_filter: str = ""
) -> tuple[int, int]:
    """Refresh the csp account inventory and match the csp inventory asset count with aws assets

    Args:
        context (Context): context
        aws_account_id (str): CSP AWS account ID
        account_id_filter (str, optional): Account ID to filter. Defaults to "".
    Returns:
        tuple[int, int]: Returns count of CSP instance and CSP volumes
    """
    active_aws_instances: list = []
    active_aws_volumes: list = []
    active_csp_instances: list[CSPMachineInstanceModel] = []
    active_csp_volumes: list[CSPVolumeModel] = []
    refresh_inventory_with_retry(context, account_id=aws_account_id)
    aws = context.aws_one
    aws_volumes = aws.ebs.get_all_volumes()
    aws_instances = aws.ec2.get_all_instances()

    # Filter out terminated assets as won't appear in DSCC
    for aws_instance in aws_instances:
        if aws_instance.state["Name"] != "terminated":
            active_aws_instances.append(aws_instance)
    for aws_volume in aws_volumes:
        if aws_volume.state != "terminated":
            active_aws_volumes.append(aws_volume)

    # Sort through only assets fo that account_id
    csp_instances = IMS.get_csp_instances(context=context, filter=account_id_filter)
    csp_volumes = IMS.get_csp_volumes(context=context, filter=account_id_filter)

    # Filter out DELETED assets (due to present backups) since won't appear in AWS
    for csp_instance in csp_instances.items:
        if csp_instance.state != "DELETED" and csp_instance.cspInfo.cspRegion == context.aws_one_region_name:
            active_csp_instances.append(csp_instance)
    for csp_volume in csp_volumes.items:
        if csp_volume.state != "DELETED" and csp_volume.cspInfo.cspRegion == context.aws_one_region_name:
            active_csp_volumes.append(csp_volume)

    # Check if CSP count matches AWS count
    assert len(active_aws_instances) == len(
        active_csp_instances
    ), f"The CSP instance count {len(active_csp_instances)} doesn't match with AWS Ec2 Instance Count {len(active_aws_instances)}"
    assert len(active_aws_volumes) == len(
        active_csp_volumes
    ), f"The CSP Volume count {len(active_csp_volumes)} doesn't match with AWS Volume Count {len(active_aws_volumes)}"

    return len(active_csp_instances), len(active_csp_volumes)


# endregion

# region Restore


def ec2_restore(
    context: Context,
    source_ec2_instance: CSPMachineInstanceModel,
    source_ec2_instance_backup: CSPBackupModel,
    restore_type: str,
    restored_ec2_name: str,
    availability_zone: str,
    aws: AWS,
    subnet_id: str = "AWS Default",
    tags: Optional[list[CSPTag]] = None,
    terminate_original: bool = False,
    selected_device_indexes: list[int] = list(),
):
    """The ec2_restore method will restore ec2 instance

    Args:
        context (Context): context object
        source_ec2_instance (CSPMachineInstanceModel): CSP Machine Instance, for relevant account and instance data
        source_ec2_instance_backup (CSPBackupModel): CSP Backup which we restore
        restore_type (str): Type of restore: "CREATE" or "REPLACE"
        restored_ec2_name (str): Name of the restored EC2 Instance
        availability_zone (str): Availability Zone for the restored EC2 Instance
        aws : AWS object
        subnet_id (str, optional): subnet id to be used while restore. Defaults to "AWS Default".
        tags (list[CSPTag], optional): Tags to be used while restore. Defaults to None.
        terminate_original (bool, optional): If True, source EC2 will be terminated. Defaults to False.
        selected_device_indexes (list[int], optional): Partial Instance Restore(Selected Volumes).
            If empty list restore selected volume functionality will be not executed. Default to list().
    """

    # Compose payloads with the retrieved details
    # Payload for restore csp_machine_instance
    # required fields:
    # - id (machine_instance_id)
    # - backupId
    # - accountId (CSP)
    # - availabilityZone
    # - region
    # - instanceType
    # - maintain default "operationType": CREATE
    if selected_device_indexes:
        block_device_mappings = RestoreSteps.get_block_device_mappings(
            context,
            source_ec2_instance.id,
            source_ec2_instance_backup.id,
        )
    else:
        block_device_mappings = None

    # check instance type is available during restore
    instance_type = aws.ec2.choose_next_available_instance_type(
        ec2_instance_type=Ec2Type(source_ec2_instance.cspInfo.instanceType)
    )

    ec2_restore_payload = RestoreSteps.build_restore_machine_instance_payload(
        source_ec2_instance.accountInfo.id,
        availability_zone,
        source_ec2_instance.cspInfo.cspRegion,
        instance_type,
        source_ec2_instance.cspInfo.keyPairName,
        source_ec2_instance.cspInfo.networkInfo.securityGroups[0].cspId,
        subnet_id,
        terminate_original=terminate_original,
        operation_type=restore_type,
        tags=tags,
        block_device_mappings=block_device_mappings,
    )
    # the restored ec2_instance, we'll give it a specific "name" and use it as a filter
    ec2_restore_payload.target_machine_instance_info.name = restored_ec2_name

    # Restore backup as a new instance and wait for task to complete
    ec2_restore_task_id = RestoreSteps.restore_machine_instance_and_wait(
        context, source_ec2_instance_backup.id, ec2_restore_payload
    )
    # check that there are no task errors;
    machine_instance_error_msg = tasks.get_task_error(ec2_restore_task_id, context.user)
    logger.info(f"ec2_machine restore task error: {machine_instance_error_msg}")
    assert machine_instance_error_msg == "", f"Error: {machine_instance_error_msg}"

    if terminate_original is True:
        waiter = aws.ec2.ec2_client.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=[source_ec2_instance.cspId])

    restored_ec2_instance_id: str = None
    filters = [
        {"Name": "instance-state-name", "Values": ["running"]},
        {"Name": "tag:Name", "Values": [restored_ec2_name]},
    ]
    if tags:
        for tag in tags:
            filters.append({"Name": f"tag:{tag.key}", "Values": [tag.value]})
    for i in range(10):
        aws_results = aws.ec2.ec2_client.describe_instances(Filters=filters)
        if len(aws_results["Reservations"][0]["Instances"]) == 1:
            restored_ec2_instance_id: str = aws_results["Reservations"][0]["Instances"][0]["InstanceId"]
            break
        time.sleep(3)

    assert restored_ec2_instance_id is not None
    waiter = aws.ec2.ec2_client.get_waiter("instance_running")
    waiter.wait(InstanceIds=[restored_ec2_instance_id])


def ebs_restore(
    context: Context,
    aws: AWS,
    source_ebs_vol: CSPVolumeModel,
    ebs_backup: CSPBackupModel,
    restore_ebs_name: str,
    restore_type: str = "ATTACH",
    machine_instance_id: str = None,
    delete_original_volume: bool = False,
    device: str = "/dev/sdh",
    volume_size: int = 10,
    tags: Optional[list[CSPTag]] = None,
):
    """
    ebs_restore method will restore the EBS volume

    Arguments:
        context (Context): Context object
        aws (AWS) : AWS object
        source_ebs_vol (CSPVolumeModel): EBS volume using which we get accountId, availabilityZone, region and type to restore backup
        ebs_backup (CSPBackupModel): EBS volume backup which we restore
        restore_ebs_name (str): Name of the restored EBS
        restore_type (str, optional): Type of restore: "CREATE", "REPLACE", or "ATTACH". Defaults to "ATTACH"
        machine_instance_id (str, optional): Machine instance id. Defaults to None
        delete_original_volume (bool, optional): Set to True if we want to delete source ebs volume after restore. Defaults to False
        device (str, optional): Volume device. E.g. /dev/sda. Defaults to "/dev/sdh"
        volume_size (int, optional): Size of the EBS volume to restore. Defaults to 10
        tags (list[CSPTag], optional): Tags to be used while restore. Defaults to None.
    """

    # Payload for restore csp_volume
    # required fields:
    # - id (volume_id) -> used in POST call
    # - backupId
    # - accountId (CSP)
    # - availabilityZone
    # - region
    # - sizeInGiB
    # - volumeType
    # - omit machineInstanceId(used if we want to attach this vol as part of the restore;this volume remains unattached)

    if restore_type == "ATTACH":
        restore_size_in_GiB = volume_size
    else:
        restore_size_in_GiB = source_ebs_vol.cspInfo.sizeInGiB

    # NOTE: Replace Restore type does not allow for device name parameter otherwise will result in failure
    if restore_type == "REPLACE":
        device = None

    ebs_restore_payload = RestoreSteps.build_restore_volume_payload(
        account_id=source_ebs_vol.accountInfo.id,
        availability_zone=source_ebs_vol.cspInfo.availabilityZone,
        region=source_ebs_vol.cspInfo.cspRegion,
        size_in_GiB=restore_size_in_GiB,
        volume_type=source_ebs_vol.cspInfo.volumeType,
        machine_instance_id=machine_instance_id,
        attachment_type=restore_type,
        delete_original_volume=delete_original_volume,
        tags=tags,
        device=device,
    )

    # the restored ebs_volume, we'll give it a specific "name" and use it as a filter
    ebs_restore_payload.target_volume_info.name = restore_ebs_name

    logger.info(f"Restore payload:\n{ebs_restore_payload.to_json()}")

    # TODO: Need to implement Advance options while restoring
    logger.info(f"Restoring Volume {source_ebs_vol.id}, Backup ID = {ebs_backup.id}")
    ebs_restore_task_id = RestoreSteps.restore_volume_and_wait(
        context=context,
        backup_id=ebs_backup.id,
        restore_payload=ebs_restore_payload,
    )
    logger.info(f"Success - volume restored from {source_ebs_vol.id}")

    # check that there are no task errors
    volume_error_msg = tasks.get_task_error(ebs_restore_task_id, context.user)
    logger.info(f"ebs_volume restore task error: {volume_error_msg}")
    assert volume_error_msg == "", f"Error: {volume_error_msg}"

    if delete_original_volume is True:
        waiter = aws.ec2.ec2_client.get_waiter("volume_deleted")
        waiter.wait(VolumeIds=[source_ebs_vol.cspId])

    restored_ebs_volume_id: str = None
    filters = [
        {"Name": "tag:Name", "Values": [restore_ebs_name]},
    ]
    if tags:
        for tag in tags:
            filters.append({"Name": f"tag:{tag.key}", "Values": [tag.value]})
    for i in range(10):
        aws_results = aws.ec2.ec2_client.describe_volumes(Filters=filters)
        if len(aws_results["Volumes"]) == 1:
            restored_ebs_volume_id: str = aws_results["Volumes"][0]["VolumeId"]
            break
        time.sleep(3)

    assert restored_ebs_volume_id is not None

    if restore_type == "CREATE":
        waiter = aws.ec2.ec2_client.get_waiter("volume_available")
        waiter.wait(VolumeIds=[restored_ebs_volume_id])

    elif restore_type == "ATTACH" or restore_type == "REPLACE":
        waiter = aws.ec2.ec2_client.get_waiter("volume_in_use")
        waiter.wait(VolumeIds=[restored_ebs_volume_id])


# endregion

# region Backups


def run_and_verify_cloud_backup(
    context: Context,
    csp_account: CSPAccountModel,
    csp_asset_id: str,
    asset_type: AssetType,
    region: str = None,
    wait_for_task_complete: bool = False,
    copy_2_cloud: bool = True,
    wait_timeout: int = TimeoutManager.create_cloud_backup_timeout,
) -> str:
    """Trigger cloud backup and copy to cloud endpoint. Optionally Wait for Nightly CVSA Cycle Task to complete.

    Args:
        context (Context): Context Object
        csp_account (CSPAccountModel): CSPAccountModel object
        csp_asset_id (str): CSP Instance, CSP Volume ID, CSP Protection Group ID
        asset_type (AssetType): CSP_MACHINE_INSTANCE | CSP_VOLUME | CSP_PROTECTION_GROUP
        region (str, optional): AWS Region. Defaults to None
        wait_for_task_complete (bool, optional): Condition to Wait for cloud backup task to complete. Defaults to False
        copy_2_cloud (bool, optional): If True, the /copy2cloud endpoint is called. Defaults to True.
        wait_timeout (int, optional): Number of seconds to wait for "trigger_task_id" to complete. Defaults to 7200 (2 Hours).

    Returns:
        str: The "trigger_task_id" of the Cloud Backup task
    """
    logger.info(f"Running cloud backup on {asset_type} {csp_asset_id}")
    if not region:
        region = context.aws_one_region_name

    csp_asset = None
    csp_machine_instances_list = []
    csp_volumes_list = []
    csp_eks_list = []
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        csp_asset = IMS.get_csp_instance_by_id(context=context, csp_machine_id=csp_asset_id)
        csp_machine_instances_list = [csp_asset]
    elif asset_type == AssetType.CSP_VOLUME:
        csp_asset = IMS.get_csp_volume_by_id(context=context, csp_volume_id=csp_asset_id)
        csp_volumes_list = [csp_asset]
    elif asset_type == AssetType.CSP_K8S_APPLICATION:
        cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(
            context, context.eks_cluster_name, context.eks_cluster_aws_region
        )
        csp_asset = context.eks_inventory_manager.get_k8s_app_by_id(cluster_info.id, csp_asset_id)
        csp_eks_list = [csp_asset]
    elif asset_type == AssetType.CSP_PROTECTION_GROUP:
        csp_asset = context.inventory_manager.get_protection_group_by_id(protection_group_id=csp_asset_id)
        filter: str = f"accountInfo/id eq {csp_account.id} and {csp_asset.id} in protectionGroupInfo/id"
        csp_machine_instances_list: CSPMachineInstanceListModel = IMS.get_csp_instances(context=context, filter=filter)
        csp_machine_instances_list = csp_machine_instances_list.items if csp_machine_instances_list else []
        csp_volumes_list: CSPVolumeListModel = IMS.get_csp_volumes(context=context, filter=filter)
        csp_volumes_list = csp_volumes_list.items if csp_volumes_list else []

    trigger_task_id = BackupSteps.run_backup_for_asset_and_wait_for_trigger_task(
        context=context,
        asset_resource_uri=csp_asset.resourceUri,
        backup_type=BackupType.CLOUD_BACKUP,
        wait_for_task_complete=wait_for_task_complete,
        wait_for_task_ready_for_copy2cloud=copy_2_cloud,
    )
    logger.info(f"CloudBackup Trigger Task {trigger_task_id} for asset {csp_asset.id} started...")

    def _wait_for_backup(asset_id, asset_type: AssetType):
        logger.info(f"Waiting for CSPBackup status OK: {asset_type.value} {asset.id}")
        BackupSteps.wait_for_backups_status_ok(context=context, asset_id=asset_id, asset_type=asset_type)
        logger.info("CSPBackup state/status are all OK")

    for asset in csp_machine_instances_list:
        _wait_for_backup(asset.id, AssetType.CSP_MACHINE_INSTANCE)
    for asset in csp_volumes_list:
        _wait_for_backup(asset.id, AssetType.CSP_VOLUME)
    for asset in csp_eks_list:
        _wait_for_backup(asset.id, AssetType.CSP_K8S_APPLICATION)

    if copy_2_cloud:
        # DCS-6465 | This could be a timing issue
        #
        # FILEPOC run on 1-19 has Cloud Backup for Volume not completed by /copy2cloud call.
        # HUMIO shows the Cloud Backup task de2e301a-fccb-4fd5-9a13-3084d8eb4211 completed at: 2023-01-19 05:40:24.011
        # while the following /copy2cloud task 0c1aa9bc-c00a-4460-a2aa-c45b00bf5f2f        at: 2023-01-19 05:39:08.543
        # has already determined: "Skipping the CVSA bring up, no backups to Copy-to-Cloud or Delete customerID: 12177e34a3ab11ecba053e8c42b606cc..."
        #
        # The test called /copy2cloud at: 2023-01-19 05:39:03
        #
        # We will add a 3 minute pause here and monitor. The hope is this allows the /copy2cloud task to see the pending Cloud Backup
        # logger.info(f"DCS-6465 Sleeping for 3 minutes following trigger task: {trigger_task_id}")
        # time.sleep(180)

        # Run /copy2cloud to start the CloudBackup
        logger.info(f"Calling Copy2Cloud for {csp_account.name} in Region {region}")
        BackupSteps.run_copy2cloud_endpoint(context=context, account_name=csp_account.name, region=region)
        logger.info("copy2cloud endpoint called")

        logger.info(
            f"Find and wait for copy2cloud task to complete. customerID: {csp_account.customerId} accountID: {csp_account.id}"
        )
        # look for and wait for the "TaskForNightlyCVSACycle <region>" task to complete
        copy2cloud_task_id = BackupSteps.find_and_wait_for_copy2cloud(
            context=context,
            customer_id=csp_account.customerId,
            account_id=csp_account.id,
            account_name=csp_account.name,
            region=region,
        )
        logger.info(f"copy2cloud task: {copy2cloud_task_id} is complete")

        logger.info(f"Waiting for CloudBackup Trigger task to complete: {trigger_task_id}")
        # Now we can wait for the CloudBackup Trigger task to run to completion
        tasks.wait_for_task(task_id=trigger_task_id, user=context.user, timeout=wait_timeout)
        logger.info(f"CloudBackup Trigger Task complete: {trigger_task_id}")

        error_msg = tasks.get_task_error(task_id=trigger_task_id, user=context.user)
        logger.info(f"CloudBackup Task contains error_msg: {error_msg}")
        assert error_msg == ""

    return trigger_task_id


def run_and_verify_eks_cloud_backup(
    context: Context,
    csp_account: CSPAccountModel,
    csp_asset_id: str,
    asset_type: AssetType,
    region: str = None,
    wait_for_task_complete: bool = False,
    copy_2_cloud: bool = True,
    wait_timeout: int = TimeoutManager.create_cloud_backup_timeout,
    csp_cluster_id: str = None,
) -> str:
    """Trigger cloud backup and copy to cloud endpoint for the operator role for an eks cloud . Optionally Wait for Nightly CVSA Cycle Task to complete.

    Args:
        context (Context): Context Object
        csp_account (CSPAccountModel): CSPAccountModel object
        csp_asset_id (str): CSP Instance, CSP Volume ID, CSP Protection Group ID
        asset_type (AssetType): CSP_MACHINE_INSTANCE | CSP_VOLUME | CSP_PROTECTION_GROUP
        region (str, optional): AWS Region. Defaults to None
        wait_for_task_complete (bool, optional): Condition to Wait for cloud backup task to complete. Defaults to False
        copy_2_cloud (bool, optional): If True, the /copy2cloud endpoint is called. Defaults to True.
        wait_timeout (int, optional): Number of seconds to wait for "trigger_task_id" to complete. Defaults to 7200 (2 Hours).
        csp_cluster_id (str): CSP EKS cluster ID

    Returns:
        str: The "trigger_task_id" of the Cloud Backup task
    """
    logger.info(f"Running cloud backup on {asset_type} {csp_asset_id}")
    if not region:
        region = context.aws_one_region_name

    csp_asset = None
    csp_eks_list = []
    if asset_type == AssetType.CSP_K8S_APPLICATION:
        csp_asset = context.eks_inventory_manager.get_k8s_app_by_id(csp_cluster_id, csp_asset_id)
        csp_eks_list = [csp_asset]

    backup_count_before = get_k8s_app_backup_count(context, csp_asset_id, CSPBackupType.HPE_CLOUD_BACKUP)
    logger.info(f"Backup count before cloud backup trigger: {backup_count_before}")

    trigger_task_id = BackupSteps.run_backup_for_asset_and_wait_for_trigger_task(
        context=context,
        asset_resource_uri=csp_asset.resourceUri,
        backup_type=BackupType.CLOUD_BACKUP,
        wait_for_task_complete=wait_for_task_complete,
        wait_for_task_ready_for_copy2cloud=copy_2_cloud,
    )
    logger.info(f"CloudBackup Trigger Task {trigger_task_id} for asset {csp_asset.id} started...")

    def _wait_for_backup(asset_id, asset_type: AssetType):
        logger.info(f"Waiting for CSPBackup status OK: {asset_type.value} {asset.id}")
        BackupSteps.wait_for_backups_status_ok(context=context, asset_id=asset_id, asset_type=asset_type)
        logger.info("CSPBackup state/status are all OK")

    for asset in csp_eks_list:
        _wait_for_backup(asset.id, AssetType.CSP_K8S_APPLICATION)

    if copy_2_cloud:
        # DCS-6465 | This could be a timing issue
        #
        # FILEPOC run on 1-19 has Cloud Backup for Volume not completed by /copy2cloud call.
        # HUMIO shows the Cloud Backup task de2e301a-fccb-4fd5-9a13-3084d8eb4211 completed at: 2023-01-19 05:40:24.011
        # while the following /copy2cloud task 0c1aa9bc-c00a-4460-a2aa-c45b00bf5f2f        at: 2023-01-19 05:39:08.543
        # has already determined: "Skipping the CVSA bring up, no backups to Copy-to-Cloud or Delete customerID: 12177e34a3ab11ecba053e8c42b606cc..."
        #
        # The test called /copy2cloud at: 2023-01-19 05:39:03
        #
        # We will add a 3 minute pause here and monitor. The hope is this allows the /copy2cloud task to see the pending Cloud Backup
        # logger.info(f"DCS-6465 Sleeping for 3 minutes following trigger task: {trigger_task_id}")
        # time.sleep(180)

        # Run /copy2cloud to start the CloudBackup
        logger.info(f"Calling Copy2Cloud for {csp_account.name} in Region {region}")
        BackupSteps.run_copy2cloud_endpoint(context=context, account_name=csp_account.name, region=region)
        logger.info("copy2cloud endpoint called")

        logger.info(
            f"Find and wait for copy2cloud task to complete. customerID: {csp_account.customerId} accountID: {csp_account.id}"
        )
        # look for and wait for the "TaskForNightlyCVSACycle <region>" task to complete
        copy2cloud_task_id = BackupSteps.find_and_wait_for_copy2cloud(
            context=context,
            customer_id=csp_account.customerId,
            account_id=csp_account.id,
            account_name=csp_account.name,
            region=region,
        )
        logger.info(f"copy2cloud task: {copy2cloud_task_id} is complete")

        logger.info(f"Waiting for CloudBackup Trigger task to complete: {trigger_task_id}")
        # Now we can wait for the CloudBackup Trigger task to run to completion
        tasks.wait_for_task(task_id=trigger_task_id, user=context.user, timeout=wait_timeout)
        logger.info(f"CloudBackup Trigger Task complete: {trigger_task_id}")

        backup_count_after = get_k8s_app_backup_count(context, csp_asset_id, CSPBackupType.HPE_CLOUD_BACKUP)
        logger.info(f"Backup count after cloud backup trigger: {backup_count_after}")

        assert (
            backup_count_after == backup_count_before + 1
        ), f"Cloud backup count for K8S application didn't change after taking a backup. Was {backup_count_after}, should be {backup_count_before + 1}"

        error_msg = tasks.get_task_error(task_id=trigger_task_id, user=context.user)
        if error_msg:
            logger.warning(f"CloudBackup Task contains error_msg: {error_msg}")
        assert error_msg == ""

    return trigger_task_id


# endregion

# region Wait Function


def wait_for_condition(lambda_function, timeout: int = 600, sleep: int = 10, error_msg: str = ""):
    """Wait for lambda_function to be True.  Checks every "sleep" seconds until True or "timeout" is reached.

    Args:
        lambda_function (func): The lambda function that will be executed every 'sleep' seconds
        timeout (int, optional): The total wait time in seconds. Defaults to 600.
        sleep (int, optional): lambda check is made every 'sleep' seconds. Defaults to 10.
        error_msg (str, optional): An error message to append to the base error message. Defaults to "".
    """
    timeout_error = f"Timeout of {timeout} seconds elapsed: {error_msg}"

    try:
        wait(
            lambda: lambda_function(),
            timeout_seconds=timeout,
            sleep_seconds=sleep,
        )
    except TimeoutExpired:
        assert False, timeout_error


def wait_for_kafka_message_consume(
    kafka_manager: KafkaManager,
    consumer_group: str,
    timeout_seconds: int = 120,
    sleep_seconds: int = 1,
):
    """
    Retrieves the highest offset for the specified consumer group and waits for the
    committed offset to reach that value.  The timeout_seconds and sleep_seconds mean
    the same as in the "waiting" library.

    Args:
        kafka_manager (KafkaManager): Kafka Manager
        consumer_group (str): consumer group
        timeout_seconds (int, optional): Wait timeout. Defaults to 120.
        sleep_seconds (int, optional): Sleep time. Defaults to 1.
    """
    _, end_offset = kafka_manager.consumer_group_offset(consumer_group, 0)

    def _wait_for_message_consume():
        current_offset, _ = kafka_manager.consumer_group_offset(consumer_group, 0)
        return current_offset >= end_offset

    wait(
        _wait_for_message_consume,
        timeout_seconds=timeout_seconds,
        sleep_seconds=sleep_seconds,
    )


# endregion


def generate_random_string_data(num_lines: int = 10) -> list[str]:
    """Generate random string data in an array. For use with RemoteConnect.write_data_to_remote_file()

    Args:
        num_lines (int, optional): Number of entries to create in the array of strings. Defaults to 10.

    Returns:
        list[str]: an array of random strings
    """
    string_data: list[str] = []

    for _ in range(num_lines):
        string_data.append("".join(random.choices(string.ascii_letters, k=256)) + "\n")

    return string_data


def verify_and_set_aws_account_health_status(
    context: Context,
    aws_account_name: str,
    aws_account_id: str,
    aws_session: str,
    stack_name: str,
) -> CSPAccountModel:
    """
    Verifies AWS account health check, if it is not found register the account and not in validated state, reregister the AWS account.

    Args:
        context (Context): Specify the context
        aws_account_name (str): AWS account name
        aws_account_id (str): AWS account ID
        aws_session (str): AWS account session id
        stack_name (str): cloud formation template stack name
    Returns:
        CSPAccountModel: Registered CSP Account
    """
    logger.info(f"Verify AWS account id: {aws_account_id} and name: {aws_account_name} health check started...")
    csp_account = CAMS.get_csp_account_by_csp_name(context, account_name=aws_account_name, is_found_assert=False)
    if not csp_account:
        register_and_validate_csp_aws_account(
            context,
            aws_account_id=aws_account_id,
            aws_account_name=aws_account_name,
            aws_session=aws_session,
            stack_name=stack_name,
        )
    if csp_account and csp_account.validationStatus.value != ValidationStatus.passed.value:
        register_and_validate_csp_aws_account(
            context,
            aws_account_id=aws_account_id,
            aws_account_name=aws_account_name,
            aws_session=aws_session,
            stack_name=stack_name,
        )
    if csp_account and csp_account.validationStatus.value == ValidationStatus.passed.value:
        logger.info("AWS account is already in validated state, lets continue...")
    logger.info(f"AWS account id: {aws_account_id} and name: {aws_account_name} health check completed successfully...")
    return


def write_and_validate_data_dm_core_ssm(
    context: Context,
    ec2_instance: Instance,
    user_name: str,
    validation: bool = False,
    percentage_to_fill: int = 5,
    copy_dm_core: bool = False,
):
    """SSH into the 'ec2_instance' and writes / validates data

    Args:
        context (Context): Context object
        ec2_instance (Instance): AWS EC2 instance
        user_name (str): ec2 user name to be used to determine the home directory
        validation (bool, optional): Whe set to True, data will be validated, False will write data. Defaults to False.
        percentage_to_fill (int): Percentage to fill / write data. Defaults to 5.
        copy_dm_core (bool): Copy the dm core package. Defaults to False.
    """
    if not validation or copy_dm_core:
        context.aws_one.ssm.copy_dmcore_to_linux_ec2_instance(ec2_instance=ec2_instance, user_name=user_name)
        logger.info("DM CORE binary copied to linux is successful.")

    logger.info("Begin to Run DM CORE")
    status = context.aws_one.ssm.run_dmcore(
        ec2_instance_id=ec2_instance.id,
        user_name=user_name,
        validation=validation,
        percentage_to_fill=percentage_to_fill,
    )

    logger.info(f"DM CORE finished with status: {status}")
    assert status


def delete_dscc_assets(aws: AWS, key: str, name: str):
    def _check_name(tags, key, name):
        for tag in tags:
            if key in tag["Key"] and name in tag["Value"].lower():
                return True
        return False

    logger.info("Deleting EC2")
    instances = aws.ec2.get_all_instances()
    for ec2_instance in instances:
        if ec2_instance.tags and _check_name(ec2_instance.tags, key, name):
            logger.info(f"deleting {ec2_instance.id}")
            aws.ec2.terminate_ec2_instance(ec2_instance_id=ec2_instance.id)
            for device in ec2_instance.block_device_mappings:
                # commenting out the condition as deleteOnTermination field is removed with the new GLC change
                # if not device["Ebs"]["DeleteOnTermination"]:
                logger.info(f"Delete volume {device['Ebs']['VolumeId']}")
                aws.ebs.delete_volume(device["Ebs"]["VolumeId"])
                logger.info(f"Volume deleted {device['Ebs']['VolumeId']}")

    logger.info("Deleting EBS")
    ebs_volumes = aws.ebs.get_all_volumes()
    for ebs_volume in ebs_volumes:
        if ebs_volume.tags and _check_name(ebs_volume.tags, key, name):
            logger.info(f"deleting {ebs_volume.id}")
            aws.ebs.delete_volume(volume_id=ebs_volume.id)

    logger.info("Deleting RDS")
    rds_instances = aws.rds.get_all_db_instances()
    for rds_instance in rds_instances:
        if name in rds_instance["DBInstanceIdentifier"]:
            logger.info(f"deleting {rds_instance['DBInstanceIdentifier']}")
            aws.rds.delete_db_instance_by_id(db_instance_identifier=rds_instance["DBInstanceIdentifier"])


def run_copy2cloud_endpoint_and_wait_for_complete(
    context: Context,
    csp_account: CSPAccountModel,
    region: str,
    trigger_task_ids: list,
    wait_timeout: int = TimeoutManager.create_cloud_backup_timeout,
):
    """run copy2cloud end point and wait for cloud backups to complete

    Args:
        context (Context): Context object
        csp_account (CSPAccountModel): CSP AWS account information object
        region (str): Region name
        trigger_task_ids (list): Triggered cloud backup tasks to verify
        wait_timeout (int, optional): Timeout to wait for cloud backup to complete. Defaults to TimeoutManager.create_cloud_backup_timeout.
    """
    # Run /copy2cloud to start the CloudBackup
    logger.info(f"Calling Copy2Cloud for {csp_account.name} in Region {region}")
    BackupSteps.run_copy2cloud_endpoint(context=context, account_name=csp_account.name, region=region)
    logger.info("copy2cloud endpoint called")

    logger.info(
        f"Find and wait for copy2cloud task to complete. customerID: {csp_account.customerId} accountID: {csp_account.id}"
    )
    # look for and wait for the "TaskForNightlyCVSACycle <region>" task to complete
    copy2cloud_task_id = BackupSteps.find_and_wait_for_copy2cloud(
        context=context,
        customer_id=csp_account.customerId,
        account_id=csp_account.id,
        account_name=csp_account.name,
        region=region,
    )
    logger.info(f"copy2cloud task: {copy2cloud_task_id} is complete")
    for trigger_task_id in trigger_task_ids:
        logger.info(f"Waiting for CloudBackup Trigger task to complete: {trigger_task_id}")
        # Now we can wait for the CloudBackup Trigger task to run to completion
        tasks.wait_for_task(task_id=trigger_task_id, user=context.user, timeout=wait_timeout)
        logger.info(f"CloudBackup Trigger Task complete: {trigger_task_id}")


def validate_aclm_cleanup_from_aws(aws: AWS):
    """Validates that ManagedBy - HPE tag is removed from AMIs and snapshots for assets in the specified AWS region
    after a CSP account is unprotected

    Args:
        aws (AWS): AWS object
    """
    managed_by_hpe_tag = Tag(Key="ManagedBy", Value="HPE")
    with check:
        logger.info(f"Checking if EBS snapshots exist with {managed_by_hpe_tag} tag")
        snapshots = aws.ebs.get_snapshot_by_tag(tag=managed_by_hpe_tag)
        assert snapshots is None, f"Expected 0 snapshots, found snapshots {snapshots}"

    with check:
        logger.info(f"Checking if AMIs exist with {managed_by_hpe_tag} tag")
        amis = aws.ec2.get_ami_by_tag(tag=managed_by_hpe_tag)
        assert len(amis) == 0, f"Expected 0 AMIs, found {len(amis)}"

    with check:
        logger.info(f"Checking if RDS snapshots exist with {managed_by_hpe_tag} tag")
        rds_snapshots = aws.rds.get_snapshots_by_tag(tag=managed_by_hpe_tag)
        assert len(rds_snapshots) == 0, f"Expected 0 AMIs, found {len(rds_snapshots)}"
