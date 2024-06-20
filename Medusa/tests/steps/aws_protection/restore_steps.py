"""
This Module contains steps Related to Restore Workflow. This includes:
    Restore ec2 and ebs.
    Verifying Restore Related Tasks are Completed.
    Getting backups to restore.
"""

import logging
from typing import Optional
from uuid import UUID

import requests

from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.ebs_volume_type import EBSVolumeType
from lib.common.enums.ec2_restore_operation import Ec2RestoreOperation
from lib.common.enums.task_status import TaskStatus
from lib.common.enums.az_regions import AZRegion

from lib.common.users.user import User
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import (
    CSPBackupListModel,
    CSPBackupModel,
    VolumeAttachmentInfoModel,
)
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import CSPVolumeModel
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import CSPMachineInstanceModel
from lib.platform.aws_boto3.aws_factory import AWS

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag, ObjectCspIdName, AttachmentInfo

from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_payload_model import (
    InstanceAttachmentInfoModel,
    PostRestoreCspMachineInstanceModel,
    RestoreEC2AWSInfoModel,
    PostRestoreCspVolumeFromCspInstanceBackupModel,
    PostRestoreCspVolumeModel,
    RestoreEBSAWSInfoModel,
    RestoreAzureDiskInfoModel,
    TargetVolumeInfoModel,
    TargetMachineInstanceInfoModel,
    OriginalMachineInstanceInfoModel,
)

from tests.e2e.aws_protection.context import Context
import tests.steps.aws_protection.backup_steps as BS
import tests.steps.aws_protection.inventory_manager_steps as IMS
from tests.steps.tasks import tasks
import tests.steps.aws_protection.common_steps as CommonSteps

logger = logging.getLogger()


def build_restore_machine_instance_payload(
    account_id: UUID,
    availability_zone: str,
    region: str,
    instance_type: str,
    key_pair: str,
    security_group: str,
    subnet_id: str,
    disable_termination: bool = False,
    terminate_original: bool = False,
    operation_type: str = "CREATE",
    tags: Optional[list[CSPTag]] = None,
    name: str = "",
    block_device_mappings: list[VolumeAttachmentInfoModel] = None,
    private_ip: str = None,
) -> PostRestoreCspMachineInstanceModel:
    """
    Build restore machine instance payload.

    Args:
        account_id (UUID): csp AWS account id
        availability_zone (str): aws availability zone string. example: "us-west-2b"
        region (str): aws region. example: "us-west-2"
        instance_type (str): aws instance type. example: "t2.micro"
        key_pair (str): aws key pair name used for ssh
        security_group (str): aws security group id. example: "sg-0d79b89dedd33bec6"
        subnet_id (str): aws subnet id. example: "subnet-05e149185ce295f0d"
        disable_termination (bool, optional): Disable terminating the restored machine instance until
            the corresponding setting is changed in the cloud service provider account.. Defaults to False.
        terminate_original (bool, optional): Indicates if the original machine instance is to be terminated
            after the restore operation. Defaults to False.
        operation_type (str, optional): Indicates whether an existing machine instance is to be replaced.
            Allowed: CREATE, REPLACE. Defaults to "CREATE".
        tags (Optional[list[CSPTag]], optional): List of tags assigned to the restored machine (default is None).
        name (str): restored ec2 instance name
        block_device_mappings (list[VolumeAttachmentInfoModel], optional): Partial Instance Restore(Selected Volumes).
            If None restore selected volume functionality will be not executed. Default to list().
        private_ip (str): private address ip

    Returns:
        PostRestoreCspMachineInstanceModel: restore ec2 payload that can be used in restore_machine_instance_and_wait()
    """
    ec2_aws: RestoreEC2AWSInfoModel = RestoreEC2AWSInfoModel(
        availability_zone=availability_zone,
        csp_region=region,
        instance_type=instance_type,
        csp_tags=tags,
        key_pair_name=key_pair,
        security_group_ids=[security_group],
        disable_termination=disable_termination,
        subnet_csp_id=subnet_id,
        private_ip_address=private_ip,
        block_device_mappings=block_device_mappings,
    )

    # The "name" in TargetMachineInstanceInfo will override any "Name" CSPTag provided.
    # Defaults to ""
    # If the "tags" provided have a "Name" CSPTag, use its value for the "TargetMachineInstanceInfoModel"
    if tags:
        for tag in tags:
            if tag.key == "Name":
                name = tag.value
                break

    target_machine_info: TargetMachineInstanceInfoModel = TargetMachineInstanceInfoModel(
        account_id=account_id, csp_info=ec2_aws, name=name
    )

    original_machine_info: OriginalMachineInstanceInfoModel = OriginalMachineInstanceInfoModel(
        terminate_original=terminate_original
    )

    restore_machine_payload: PostRestoreCspMachineInstanceModel = PostRestoreCspMachineInstanceModel(
        target_machine_instance_info=target_machine_info,
        original_machine_instance_info=original_machine_info,
        operation_type=operation_type,
    )

    return restore_machine_payload


def build_restore_volume_payload(
    account_id: UUID,
    availability_zone: str,
    region: str,
    size_in_GiB: int,
    volume_type: str,
    machine_instance_id: UUID = None,
    attachment_type: str = "ATTACH",
    delete_original_volume: bool = False,
    tags: Optional[list[CSPTag]] = None,
    device: str = None,
) -> PostRestoreCspVolumeModel:
    """
    Build restore volume payload

    Args:
        account_id (UUID): csp AWS account id
        availability_zone (str): aws availability zone string. example: "us-west-2b"
        region (str):  aws region. example: "us-west-2"
        size_in_GiB (int): Size of the restored volume. This shouldn't be less than size of the backup.
        volume_type (str):  aws volume type. example: "gp2"
        machine_instance_id (UUID, optional): Id of the machine instance to which the restored volume is to be attached.
            Defaults to None.
        attachment_type (str, optional): Specifies if the restored volume needs to replace an existing volume or
            if it needs to be attached without replacing any volume. In case of the former, source volume of
            the backup would be replaced. In case of the latter, the volume would be attached under the specified
            device name. Defaults to "ATTACH".
        delete_original_volume (bool, optional): Indicates whether a replaced volume needs to be deleted after
            the restore operation. Used only if attachmentType is "REPLACE". Defaults to False.
        tags (Optional[list[CSPTag]], optional): List of tags assigned to the restored volume. Defaults to None.
        device (str, optional): The device name under which the restored volume is to be attached to
            the machine instance. Needed if attachmentType is "ATTACH". Note that there shouldn't be any volume
            attached to the instance under this device name. Otherwise, the operation would fail. Defaults to None.

    Returns:
        PostRestoreCspVolumeModel: restore volume payload that can be used in restore_volume_and_wait()
    """
    ebs_aws: RestoreEBSAWSInfoModel = RestoreEBSAWSInfoModel(
        availability_zone=availability_zone,
        csp_region=region,
        size_inGiB=size_in_GiB,
        volume_type=volume_type,
        csp_tags=tags,
    )
    target_volume_info: TargetVolumeInfoModel = TargetVolumeInfoModel(account_id=account_id, csp_info=ebs_aws)

    attachment_info: InstanceAttachmentInfoModel = None
    # if a machine_instance_id is provided, then populate an InstanceAttachmentInfoModel object
    if machine_instance_id:
        attachment_info = InstanceAttachmentInfoModel(
            machine_instance_id=machine_instance_id,
            attachment_type=attachment_type,
            delete_original_volume=delete_original_volume,
            device=device,
        )

    restore_volume_payload = PostRestoreCspVolumeModel(target_volume_info=target_volume_info)
    if attachment_info:
        restore_volume_payload.instance_attachment_info.append(attachment_info)

    return restore_volume_payload


def build_restore_volume_payload_from_ec2_backup(
    device_name: str,
    account_id: UUID,
    availability_zone: str,
    region: str,
    size_in_GiB: int,
    volume_type: str,
    tags: Optional[list[CSPTag]] = None,
    encryption_keyARN: Optional[str] = None,
    iops: Optional[int] = None,
    is_encrypted: bool = False,
    multiattach: Optional[bool] = None,
    throughput_inMiBps: Optional[int] = None,
) -> PostRestoreCspVolumeFromCspInstanceBackupModel:
    """
    Build restore volume payload from EC2 backup

    Args:
        device_name (str): The device name (for example, /dev/sdh or xvdh).
        A combination of backup_id and device_name is used to retrieve the snapshotId required to restore csp volume
        account_id (UUID): csp AWS account id
        availability_zone (str): aws availability zone string. example: "us-west-2b"
        region (str):  aws region. example: "us-west-2"
        size_in_GiB (int): Size of the restored volume. This shouldn't be less than size of the backup.
        volume_type (str):  aws volume type. example: "gp2"
        tags (Optional[list[CSPTag]], optional): List of tags assigned to the restored volume. Defaults to None.
        encryption_keyARN (str, optional): ARN of the key used for encrypting the restored volume. This option should be
            specified only if isEncrypted is set to true.
        iops (int, optional): Number of I/O operations per second (IOPS) provisioned for the restored volume.
        is_encrypted: Defaults to false. Indicates whether the restored volume is to be encrypted or re-encrypted with a
            different key.
        multiattach (bool, optional): Indicates whether the restored volume should have Multi-Attach property enabled.
        throughput_inMiBps (int, optional): Throughput supported by the restored volume. Applies only to certain volume
            types as specified by AWS.

    Returns:
        PostRestoreCspVolumeFromCspInstanceBackupModel: restore volume payload that can be used in
            restore_volume_from_ec2_backup_and_wait()
    """
    ebs_aws: RestoreEBSAWSInfoModel = RestoreEBSAWSInfoModel(
        availability_zone=availability_zone,
        csp_region=region,
        size_inGiB=size_in_GiB,
        volume_type=volume_type,
        is_encrypted=is_encrypted,
        csp_tags=tags,
        multiattach=multiattach,
        iops=iops,
        throughput_inMiBps=throughput_inMiBps,
        encryption_keyARN=encryption_keyARN,
    )

    # The name property in the TargetVolumeInfo object will override any "Name" CSPTag provided.
    # Defaults to "Target volume name"
    # If the "tags" provided have a "Name" CSPTag, use its value for the "TargetVolumeInfo"
    target_volume_name = "Target volume name"
    if tags:
        for tag in tags:
            if tag.key == "Name":
                target_volume_name = tag.value
                break

    target_volume_info: TargetVolumeInfoModel = TargetVolumeInfoModel(
        account_id=account_id, csp_info=ebs_aws, name=target_volume_name
    )

    restore_volume_payload = PostRestoreCspVolumeFromCspInstanceBackupModel(
        device_name=device_name, target_volume_info=target_volume_info
    )

    return restore_volume_payload


def get_restored_asset_names_from_task(user: User, task_id: str, asset_type: AssetType) -> tuple[str, str]:
    """Return the AWS Volume and DSCC Volume names for a CSP Machine Instance /restore-volume operation.

    Args:
        user (User): The context.user object
        task_id (str): The ID of the CSP Instance /restore-volume or /restore task
        asset_type (AssetType): CSP_MACHINE_INSTANCE or CSP_VOLUME

    Returns:
        tuple[str, str]: The AWS Volume Name, and the DSCC Volume Name if the Restored Volume was given a name.
    """
    task_logs = tasks.get_task_logs(task_id=task_id, user=user)

    search_term = "vol-"  # default
    search_index = 3
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        search_term = "i-"
        search_index = 4

    aws_name: str = ""
    dscc_name: str = ""

    # NOTE: If a name ("Name" CSPTag) is provided for the Restored Volume, the Task Log entry will be:
    #     Volume created successfully vol-029c72259475f4aeb (ebs restored volume)
    # If no name is provided, then the Task Log entry will be:
    #     Volume created successfully vol-029c72259475f4aeb
    #
    # Machine Instance created successfully i-025824b3a8419dca3 (ec2 restored instance)
    #           Volume created successfully vol-029c72259475f4aeb (ebs restored volume)

    # usually the 3rd entry
    for log in task_logs:
        if search_term in log["message"]:
            log_msg: str = log["message"]

            aws_name = log_msg.split(" ")[search_index]
            dscc_start = log_msg.find("(")
            if dscc_start != -1:
                # +1 and -1 to remove the parens
                dscc_name = log_msg[dscc_start + 1 : -1]
            # exit once we find the log_msg we're looking for
            break

    return aws_name, dscc_name


def validate_instance_with_payload(
    context: Context,
    aws: AWS,
    instance_restore_payload: PostRestoreCspMachineInstanceModel,
    csp_instance: CSPMachineInstanceModel,
) -> bool:
    """Validate a CSP Instance matches the requested values in the "instance_restore_payload"

    Args:
        context (Context): The test Context
        aws (AWS): The AWS Account
        instance_restore_payload (PostRestoreCspMachineInstanceModel): The payload that was supplied to the CSP Machine Instance /restore API
        csp_instance (CSPMachineInstanceModel): The Restored CSP Machine Instance from DSCC

    Returns:
        bool: True if the validation passes, False otherwise
    """
    validated: bool = True

    # validate target_machine_instance_info (TargetMachineInstanceInfo) - always provided
    inst_info = instance_restore_payload.target_machine_instance_info

    if csp_instance.accountInfo.id != inst_info.account_id:
        validated = False
        logger.error(f"accountId mismatch: payload {inst_info.account_id}  actual {csp_instance.accountInfo.id}")

    if csp_instance.cspInfo.availabilityZone != inst_info.csp_info.availability_zone:
        validated = False
        logger.error(
            f"availabilityZone mismatch: payload {inst_info.csp_info.availability_zone}  actual: {csp_instance.cspInfo.availabilityZone}"
        )

    if csp_instance.cspInfo.cspRegion != inst_info.csp_info.csp_region:
        validated = False
        logger.error(
            f"region mismatch: payload {inst_info.csp_info.csp_region}  actual: {csp_instance.cspInfo.cspRegion}"
        )

    if csp_instance.cspInfo.instanceType != inst_info.csp_info.instance_type:
        validated = False
        logger.error(
            f"instanceType mismatch: payload {inst_info.csp_info.instance_type}  actual: {csp_instance.cspInfo.instanceType}"
        )

    if csp_instance.cspInfo.keyPairName != inst_info.csp_info.key_pair_name:
        validated = False
        logger.error(
            f"keyPairName mismatch: payload {inst_info.csp_info.key_pair_name}  actual: {csp_instance.cspInfo.keyPairName}"
        )

    for sg_id in inst_info.csp_info.security_group_ids:
        if not get_security_group_from_csp_instance(security_group_id=sg_id, csp_instance=csp_instance):
            validated = False
            logger.error(f"securityGroup mismatch: missing {sg_id}")

    for tag in inst_info.csp_info.csp_tags:
        if tag not in csp_instance.cspInfo.cspTags:
            validated = False
            logger.error(f"Missing CSPTag {tag}")

    # NOTE Get ec2_instance from AWS for a few values?
    ec2_instance = aws.ec2.get_ec2_instance_by_id(ec2_instance_id=csp_instance.cspId)

    if ec2_instance.iam_instance_profile != inst_info.csp_info.iam_instance_profile:
        validated = False
        logger.error(
            f"iam_instance_profile mismatch: payload {inst_info.csp_info.iam_instance_profile}  actual: {ec2_instance.iam_instance_profile}"
        )

    # Only if a Private IP Address was specified in the restore payload, should we check for a match.  A Private IP Address is always assigned regardless
    if inst_info.csp_info.private_ip_address:
        if csp_instance.cspInfo.networkInfo.privateIpAddress != inst_info.csp_info.private_ip_address:
            validated = False
            logger.error(
                f"privateIpAddress mismatch: payload {inst_info.csp_info.private_ip_address}  actual: {csp_instance.cspInfo.networkInfo.privateIpAddress}"
            )

    subnet_csp_id: str = IMS.get_subnet_csp_id(
        context=context,
        account_id=csp_instance.accountInfo.id,
        subnet_id=csp_instance.cspInfo.networkInfo.subnetInfo.id,
    )

    if subnet_csp_id != inst_info.csp_info.subnet_csp_id:
        validated = False
        logger.error(f"subnetId mismatch: payload {inst_info.csp_info.subnet_csp_id}  actual: {subnet_csp_id}")

    if csp_instance.name != inst_info.name:
        validated = False
        logger.error(f"name mismatch: payload {inst_info.name}  actual: {csp_instance.name}")

    # block_device_mappings
    # -- inst_info.csp_info.aws.block_device_mappings[]
    # -- csp_instance.volumeAttachmentInfo[]
    # for each block device in the payload, check the volume was created
    if inst_info.csp_info.block_device_mappings:
        for block_device_mapping in inst_info.csp_info.block_device_mappings:
            attachment_info = get_attachment_info_from_csp_instance(
                block_device_name=block_device_mapping.device_name, csp_instance=csp_instance
            )

            if not attachment_info:
                validated = False
                logger.error(f"block device not found on restored instance: {block_device_mapping.device_name}")
                continue
            # delete on termination
            # commenting out the condition as deleteOnTermination field is removed with the new GLC change
            # if attachment_info.deleteOnTermination != block_device_mapping.volume_details.delete_on_termination:
            #     validated = False
            #     logger.error(
            #         f"deleteOnTermination mismatch: payload {block_device_mapping.ebs.delete_on_termination}  actual: {attachment_info.deleteOnTermination}"
            #     )
            # otherwise, continue to validate this block_device_mapping with DSCC CSPVolume
            csp_volume = IMS.get_csp_volume_by_id(
                context=context, csp_volume_id=attachment_info.attachedTo.resource_uri.split("/")[-1]
            )

            if block_device_mapping.volume_details.volume_size != csp_volume.cspInfo.sizeInGiB:
                validated = False
                logger.error(
                    f"volume_size mismatch: payload {block_device_mapping.volume_details.volume_size}  actual: {csp_volume.cspInfo.sizeInGiB}"
                )

            vol_iops = calculate_iops(
                payload_iops=block_device_mapping.volume_details.iops,
                size_in_gb=block_device_mapping.volume_details.volume_size,
            )
            # if "block_device_mapping.ebs.iops" is None - CSPVolume should have the minimum of 100
            if csp_volume.cspInfo.iops != vol_iops:
                validated = False
                logger.error(
                    f"iops mismatch: payload {block_device_mapping.volume_details.iops}  actual: {csp_volume.cspInfo.iops}"
                )

            if csp_volume.cspInfo.volumeType != block_device_mapping.volume_details.volume_type:
                validated = False
                logger.error(
                    f"volumeType mismatch: payload {block_device_mapping.volume_details.volume_type}  actual: {csp_volume.cspInfo.volumeType}"
                )

            if csp_volume.cspInfo.isEncrypted != block_device_mapping.volume_details.is_encrypted:
                validated = False
                logger.error(
                    f"isEncrypted mismatch: payload {block_device_mapping.volume_details.is_encrypted}  actual: {csp_volume.cspInfo.isEncrypted}"
                )

            # TODO if necessary
            # throughput_in_mi_bps - not in CSPVolume
            # kms_key_id - not in CSPVolume

    return validated


def get_attachment_info_from_csp_instance(
    block_device_name: str, csp_instance: CSPMachineInstanceModel
) -> AttachmentInfo:
    for attachment in csp_instance.volumeAttachmentInfo:
        if attachment.device == block_device_name:
            return attachment


def get_security_group_from_csp_instance(
    security_group_id: str, csp_instance: CSPMachineInstanceModel
) -> ObjectCspIdName:
    for object_id_name in csp_instance.cspInfo.networkInfo.securityGroups:
        if security_group_id == object_id_name.cspId:
            return object_id_name


def calculate_iops(payload_iops: int, size_in_gb: int, volume_type: str = EBSVolumeType.GP2.value):
    iops = 0
    # NOTE: if the restore payload did not specify an "iops": Baseline of 3 IOPS per GiB with a minimum of 100 IOPS
    if payload_iops:
        iops = payload_iops
    else:
        iops = size_in_gb * 3

    if iops < 100:
        iops = 100

    if volume_type == EBSVolumeType.GP3.value and iops < 3000:
        iops = 3000

    return iops


def validate_volume_with_payload(
    aws: AWS,
    volume_restore_payload: PostRestoreCspVolumeFromCspInstanceBackupModel,
    csp_volume: CSPVolumeModel,
) -> bool:
    """Validate a CSP Volume matches the requested values in the "volume_restore_payload"

    Args:
        aws (AWS): The AWS Account
        volume_restore_payload (PostRestoreCspVolumeFromCspInstanceBackupModel): The payload that was supplied to the CSP Machine Instance /restore-volume API
        csp_volume (CSPVolumeModel): The CSP Volume from DSCC

    Returns:
        bool: True if the validation passes, False otherwise
    """
    validated: bool = True

    # validate target_volume_info (TargetVolumeInfo) - always provided
    vol_info = volume_restore_payload.target_volume_info

    if csp_volume.accountInfo.id != vol_info.account_id:
        validated = False
        logger.error(f"accountId mismatch: payload {vol_info.account_id}  actual {csp_volume.accountInfo.id}")

    if csp_volume.cspInfo.availabilityZone != vol_info.csp_info.availability_zone:
        validated = False
        logger.error(
            f"availabilityZone mismatch: payload {vol_info.csp_info.availability_zone}  actual: {csp_volume.cspInfo.availabilityZone}"
        )

    if csp_volume.cspInfo.cspRegion != vol_info.csp_info.csp_region:
        validated = False
        logger.error(f"region mismatch: payload {vol_info.csp_info.csp_region}  actual: {csp_volume.cspInfo.cspRegion}")

    if csp_volume.cspInfo.sizeInGiB != vol_info.csp_info.size_inGiB:
        validated = False
        logger.error(
            f"sizeInGiB mismatch: payload {vol_info.csp_info.size_inGiB}  actual: {csp_volume.cspInfo.sizeInGiB}"
        )

    if csp_volume.cspInfo.volumeType != vol_info.csp_info.volume_type:
        validated = False
        logger.error(
            f"volumeType mismatch: payload {vol_info.csp_info.volume_type}  actual: {csp_volume.cspInfo.volumeType}"
        )

    if csp_volume.cspInfo.isEncrypted != vol_info.csp_info.is_encrypted:
        validated = False
        logger.error(
            f"isEncrypted mismatch: payload {vol_info.csp_info.is_encrypted}  actual: {csp_volume.cspInfo.isEncrypted}"
        )

    for tag in vol_info.csp_info.csp_tags:
        if tag not in csp_volume.cspInfo.cspTags:
            validated = False
            logger.error(f"Missing CSPTag {tag}")

    # NOTE: if the restore payload did not specify an "iops": Baseline of 3 IOPS per GiB with a minimum of 100 IOPS
    vol_iops = calculate_iops(
        payload_iops=vol_info.csp_info.iops,
        size_in_gb=vol_info.csp_info.size_inGiB,
        volume_type=vol_info.csp_info.volume_type,
    )

    # if "vol_info.csp_info.aws.iops" is None - CSPVolume should have the minimum of 100
    if csp_volume.cspInfo.iops != vol_iops:
        validated = False
        logger.error(f"iops mismatch: payload {vol_info.csp_info.iops}  actual: {csp_volume.cspInfo.iops}")

    # NOTE Get ebs_volume from AWS for a few values?
    ebs_volume = aws.ebs.get_ebs_volume_by_id(volume_id=csp_volume.cspId)

    # multi attach - not in CSPVolume | Amazon EBS Multi-Attach enables you to attach a single Provisioned IOPS SSD (io1 or io2) volume
    if vol_info.csp_info.multiattach is not None:
        # explicit True/False
        if ebs_volume.multi_attach_enabled != vol_info.csp_info.multiattach:
            validated = False
            logger.error(
                f"multi_attach_enabled mismatch: payload {vol_info.csp_info.multiattach}  actual: {ebs_volume.multi_attach_enabled}"
            )

    # TODO
    # throughput_inMiBps - not in CSPVolume
    # encryption_keyARN (only if "isEncrypted == True") - not in CSPVolume

    if csp_volume.name != vol_info.name:
        validated = False
        logger.error(f"name mismatch: payload {vol_info.name}  actual: {csp_volume.name}")

    # TODO - add "instance_attachment_info" checks if it's provided
    # NOTE: API https://pages.github.hpe.com/cloud/storage-api/api-v1-index.html#post-/api/v1/csp-machine-instances/{id}/restore-volume
    # is currently not accepting "InstanceAttachmentInfo" in the payload: https://nimblejira.nimblestorage.com/browse/RP-7174

    return validated


def validate_single_volume_restore(
    context: Context,
    aws: AWS,
    volume_restore_payload: PostRestoreCspVolumeFromCspInstanceBackupModel,
    restore_task_id: str = None,
) -> bool:
    """Validate the Volume Restore payload matches a CSP Volume in DSCC

    Args:
        context (Context): The test context
        aws (AWS): The AWS Account to use to obtain EBS Volume data
        volume_restore_payload (PostRestoreCspVolumeFromCspInstanceBackupModel): The payload provided to the "restore_volume_from_ec2_backup_and_wait()" function.
        restore_task_id (str, optional): If provided, the AWS Volume ID can be pulled from the task logs.
          Can be helpful if there are many Volumes with the default restore name "Target volume name". Defaults to None.

    Returns:
        bool: True is returned if validation passes, False otherwise.
    """
    validated = False

    dscc_vol_name: str = None
    aws_vol_name: str = None

    if restore_task_id:
        # get AWS "vol-{name}" and DSCC "Name" from Task Log data
        aws_vol_name, dscc_vol_name = get_restored_asset_names_from_task(
            user=context.user, task_id=restore_task_id, asset_type=AssetType.CSP_VOLUME
        )
    else:
        # get TargetVolumeInfo.name for DSCC "Name"
        dscc_vol_name = volume_restore_payload.target_volume_info.name

    # if we have an AWS Name, then get from DSCC using it
    if aws_vol_name:
        csp_volume = IMS.get_csp_volume_by_ebs_volume_id(
            context=context, ebs_volume_id=aws_vol_name, account_id=context.csp_account_id_aws_one
        )
        # validate this CSP Volume
        validated = validate_volume_with_payload(
            aws=aws, volume_restore_payload=volume_restore_payload, csp_volume=csp_volume
        )
    else:
        # otherwise, get all volumes with DSCC Name
        csp_volumes = IMS.get_csp_volumes(context=context, filter=f"name eq '{dscc_vol_name}'")
        # loop through Volumes passing validation on the first matching all restore_payload fields
        for csp_volume in csp_volumes.items:
            if validate_volume_with_payload(
                aws=aws, volume_restore_payload=volume_restore_payload, csp_volume=csp_volume
            ):
                validated = True
                break

    return validated


def get_good_backup(backList: CSPBackupListModel) -> CSPBackupModel:
    """
    Return backup from csp backup list that has state and status ok.

    Args:
        backList (CSPBackupListModel): object that holds list of csp backup

    Returns:
        CSPBackupModel: csp backup object
    """
    # find a backup with 'state' and 'status' == 'OK'
    for backup in backList.items:
        if backup.state == "OK" and backup.status == "OK":
            return backup
    return None


def get_first_good_machine_instance_backup(
    context: Context, machine_instance_id: UUID, backup_type: CSPBackupType
) -> CSPBackupModel:
    """
    Return first backup from csp machine backup endpoint that has state and status ok.

    Args:
        context (Context): AWS protection Context
        machine_instance_id (UUID): csp Id of the machine instance
        backup_type (CSPBackupType): backup type from enum. example: HPE_CLOUD_BACKUP

    Returns:
        CSPBackupModel: object of csp backup
    """
    csp_machine_instance_backups: CSPBackupListModel = BS.get_csp_machine_instance_backups(
        context=context, machine_instance_id=machine_instance_id
    )
    logger.info(f"List of backups: {csp_machine_instance_backups}")
    item = next(
        filter(
            lambda item: item.backup_type == backup_type.value and item.state == "OK" and item.status == "OK",
            csp_machine_instance_backups.items,
        )
    )
    return item


def get_first_good_volume_backup(context: Context, volume_id: UUID, backup_type: CSPBackupType) -> CSPBackupModel:
    """
    Return first backup from csp volume backup endpoint that has state and status ok.

    Args:
        context (Context): AWS protection Context
        volume_id (UUID): csp Id of the volume
        backup_type (CSPBackupType): backup type from enum. example: HPE_CLOUD_BACKUP

    Returns:
        CSPBackupModel: object of csp backup
    """
    csp_volume_backups: CSPBackupListModel = BS.get_csp_volume_backups(context, volume_id)
    logger.info(f"List of backups: {csp_volume_backups}")
    item = next(
        filter(
            lambda item: item.backup_type == backup_type.value and item.state == "OK" and item.status == "OK",
            csp_volume_backups.items,
        )
    )
    return item


def restore_machine_instance_and_wait(
    context: Context,
    backup_id: UUID,
    restore_payload: PostRestoreCspMachineInstanceModel,
    wait: bool = True,
    status_code: requests.codes = requests.codes.accepted,
    error_expected: str = "",
) -> str:
    """
    Restore machine instance according to restore payload and wait to finish

    Args:
        context (Context): AWS protection Context
        backup_id (UUID): backup Id of the machine instance
        restore_payload (PostRestoreCspMachineInstanceModel): object generated from build_restore_machine_instance_payload()
        wait (bool, optional): wait for task to finish. Defaults to True.
        status_code (requests.codes): The expected status_code. Defaults to requests.codes.accepted
        error_expected (str): The expected error text. Defaults to "".

    Returns:
        str: task id
    """
    ec2_restore_task_id, error_message = context.data_protection_manager.restore_csp_machine_instance(
        backup_id=backup_id, ec2_restore_payload=restore_payload, status_code=status_code
    )
    logger.info(f"Restore TaskID: {ec2_restore_task_id} ErrorMessage: {error_message}")

    if wait and not error_message:
        ec2_restore_task_status: str = tasks.wait_for_task(ec2_restore_task_id, context.user, 3600)
        assert ec2_restore_task_status.upper() == TaskStatus.success.value
        logger.info(f"Restore task {ec2_restore_task_id} completed successfully")

    if error_expected:
        logger.info(f"task errors for restore(): {error_message}")
        assert error_expected in error_message, f"Expected error {error_expected} not found in {error_message}"

    return ec2_restore_task_id


def restore_volume_and_wait(context: Context, backup_id: UUID, restore_payload: PostRestoreCspVolumeModel) -> str:
    """
    Restore volume according to restore payload and wait to finish

    Args:
        context (Context): AWS protection Context
        backup_id (UUID): csp Id of the volume backup
        restore_payload (PostRestoreCspVolume): object generated from build_restore_volume_payload()

    Returns:
        str: task id
    """

    ebs_restore_task_id: str = context.data_protection_manager.restore_csp_volume(backup_id, restore_payload)
    # wait for task to complete. Note: the status is returned lowercase; TaskStatus enum is uppercase
    ebs_restore_task_status: str = tasks.wait_for_task(ebs_restore_task_id, context.user, 3600)
    assert ebs_restore_task_status.upper() == TaskStatus.success.value
    return ebs_restore_task_id


def restore_volume_from_ec2_backup_and_wait(
    context: Context,
    backup_id: UUID,
    restore_payload: PostRestoreCspVolumeFromCspInstanceBackupModel,
    wait: bool = True,
) -> str:
    """
    Restore volume from ec2 instance backup according to restore payload and wait to finish

    Args:
        context (Context): AWS protection Context
        backup_id (UUID): csp Id of the machine instance backup
        restore_payload (PostRestoreCspVolumeFromCspInstanceBackupModel): object generated from
            build_restore_volume_payload_from_ec2_backup()
        wait (bool): Wait for task to finish. Defaults to True.

    Returns:
        str: task id
    """

    ebs_restore_task_id: str = context.data_protection_manager.restore_csp_volume_from_ec2_backup(
        backup_id=backup_id, ebs_restore_payload=restore_payload
    )
    # wait for task to complete. Note: the status is returned lowercase; TaskStatus enum is uppercase
    if wait:
        ebs_restore_task_status: str = tasks.wait_for_task(ebs_restore_task_id, context.user, 3600)
        assert ebs_restore_task_status.upper() == TaskStatus.success.value
        logger.info(f"Restore task {ebs_restore_task_id} - completed successfully")
    return ebs_restore_task_id


def restore_csp_machine(
    context: Context,
    aws: AWS,
    csp_account: CSPAccountModel,
    csp_instance: CSPMachineInstanceModel,
    csp_machine_backup_id: str,
    name: str = "",
    block_device_mappings_payload: list[VolumeAttachmentInfoModel] = None,
    private_ip: str = None,
) -> CSPMachineInstanceModel:
    """
    Restore machine instance and wait to finish

    Args:
        context (Context):  AWS protection Context
        aws (AWS): aws session object
        csp_account (CSPAccountModel): csp account object
        csp_instance (CSPMachineInstanceModel): csp instance object that will be source of restore
        csp_machine_backup_id (str): csp backup id to restore
        name (str): restored ec2 instance name
        block_device_mappings (list[VolumeAttachmentInfoModel], optional): Partial Instance Restore(Selected Volumes).
            If None restore selected volume functionality will be not executed. Default to list().
        private_ip (str): private ip address

    Returns:
        CSPMachineInstanceModel: restored machine instance object
    """
    subnet_csp_id: str = IMS.get_subnet_csp_id(
        context=context,
        account_id=csp_instance.accountInfo.id,
        subnet_id=csp_instance.cspInfo.networkInfo.subnetInfo.id,
    )

    ec2_restore_payload = build_restore_machine_instance_payload(
        account_id=csp_instance.accountInfo.id,
        availability_zone=csp_instance.cspInfo.availabilityZone,
        region=csp_instance.cspInfo.cspRegion,
        instance_type=csp_instance.cspInfo.instanceType,
        operation_type=Ec2RestoreOperation.CREATE.value,
        key_pair=csp_instance.cspInfo.keyPairName,
        security_group=csp_instance.cspInfo.networkInfo.securityGroups[0].cspId,
        subnet_id=subnet_csp_id,
        disable_termination=False,
        terminate_original=False,
        block_device_mappings=block_device_mappings_payload,
        name=name,
        private_ip=private_ip,
        tags=csp_instance.cspInfo.cspTags,
    )

    logger.info(f"Restore payload:\n{ec2_restore_payload.to_json()}")

    logger.info(f"Restoring EC2 {csp_instance.id}, Backup ID = {csp_machine_backup_id}")
    restore_machine_instance_and_wait(
        context=context, backup_id=csp_machine_backup_id, restore_payload=ec2_restore_payload
    )
    logger.info(f"Success - EC2 restored from {csp_instance.id}")

    # Refreshing inventory to find the restored volume
    logger.info(f"Performing Account Inventory Refresh on {csp_account.name}, ID: {csp_account.id}")
    CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account.id)

    logger.info(f"Retrieving restore EC2 with name {name}")
    restored_csp_instance_filter = f"name eq '{name}'"
    restored_machine_instance: CSPMachineInstanceModel = IMS.get_csp_instances(
        context, filter=restored_csp_instance_filter
    ).items[0]
    logger.info(f"Restored EC2 is : {restored_machine_instance.id}")

    logger.info("Validating EC2 volume count")
    # Added msg_original_volume and msg_restored_ebs to avoid 120 character limit warning
    msg_original_ec2 = f"Original EC2 ID Volumes: {len(csp_instance.volumeAttachmentInfo)}"
    msg_transient_ec2_1_restored = f"Restored EC2 ID Volumes: {len(restored_machine_instance.volumeAttachmentInfo)}"
    expected_len = (
        len(block_device_mappings_payload) if block_device_mappings_payload else len(csp_instance.volumeAttachmentInfo)
    )
    assert expected_len == len(
        restored_machine_instance.volumeAttachmentInfo
    ), f"{msg_original_ec2}\n{block_device_mappings_payload=}\n{msg_transient_ec2_1_restored}"

    validate_instance_with_payload(context, aws, ec2_restore_payload, restored_machine_instance)

    return restored_machine_instance


def get_block_device_mappings(
    context: Context,
    machine_instance_id: str,
    backup_id: str,
) -> list[VolumeAttachmentInfoModel]:
    """
    Returns the block device mapping details of a specific Backup or CloudBackup for a given CSP machine instance

    Args:
        context:  context class from Medusa framework
        machine_instance_id (str): unique identifier of a CSP instance
        backup_id (str):  unique identifier of a CSP instance backup

    Returns:
        list[VolumeAttachmentInfo]: List of ec2 device mapping for backup
    """
    logger.info(f"Get block device mapping for ec2: {machine_instance_id} for backup id: {backup_id}")
    csp_backup = BS.get_csp_machine_instance_backup_by_id(context=context, backup_id=backup_id)
    assert csp_backup

    logger.info(f"Block device mapping: {csp_backup.volume_attachment_info}")
    return csp_backup.volume_attachment_info


def validate_selected_volume_restore(
    context: Context,
    aws: AWS,
    instance_restore_payload: PostRestoreCspMachineInstanceModel,
    restore_task_id: str = None,
) -> bool:
    validated = False

    dscc_inst_name: str = None
    aws_inst_name: str = None

    if restore_task_id:
        # get AWS "i-{name}" and DSCC "Name" from Task Log data
        aws_inst_name, dscc_inst_name = get_restored_asset_names_from_task(
            user=context.user, task_id=restore_task_id, asset_type=AssetType.CSP_MACHINE_INSTANCE
        )
    else:
        # get TargetMachineInstanceInfo.name for DSCC "Name"
        dscc_inst_name = instance_restore_payload.target_machine_instance_info.name

    # if we have an AWS Name, then get from DSCC using it
    if aws_inst_name:
        csp_instance = IMS.get_csp_instance_by_ec2_instance_id(
            context=context, ec2_instance_id=aws_inst_name, account_id=context.csp_account_id_aws_one
        )
        # validate this CSP Machine Instance
        validated = validate_instance_with_payload(
            context=context, aws=aws, instance_restore_payload=instance_restore_payload, csp_instance=csp_instance
        )
    else:
        # otherwise, get all instances with DSCC Name
        csp_instances = IMS.get_csp_instances(context=context, filter=f"name eq '{dscc_inst_name}'")
        # loop through Instances passing validation on the first matching all restore_payload fields
        for csp_instance in csp_instances.items:
            if validate_instance_with_payload(
                context=context, aws=aws, instance_restore_payload=instance_restore_payload, csp_instance=csp_instance
            ):
                validated = True
                break

    return validated


def build_restore_disk_payload(
    account_id: UUID,
    name: str,
    availability_zones: list,
    csp_region: AZRegion,
    csp_resource_group_id: str,
    size_in_gib: int,
    sku_name: str,
    csp_machine_instance_id: UUID = None,
    attachment_type: str = "ATTACH",
    delete_original_volume: bool = False,
    tags: Optional[list[CSPTag]] = None,
    lun: str = None,
) -> PostRestoreCspVolumeModel:
    """
    Build restore disk payload

    Args:
        account_id (UUID): csp Azure account id
        name: A Name for the restored disk.
        availability_zones (list): Azure availability zones of the restored disk.
        csp_region (AZRegion):  azure region. example: "AZRegion.WEST_US_2"
        csp_resource_group_id (str): CSP ID of the resource group under which the restored disk is to be created.
        size_in_gib (int): Size of the restored disk. This shouldn't be less than size of the backup.
        sku_name (str): Azure cloud service provider Stock Keeping Unit (SKU) name.
        csp_machine_instance_id (UUID, optional): CSP ID of the virtual machine to which the restored disk is to be attached.
            Defaults to None.
        attachment_type (str, optional): Specifies if the restored disk needs to replace an existing disk or
            if it needs to be attached without replacing any disk. In case of the former, source disk of
            the backup would be replaced. In case of the latter, the disk would be attached under the specified
            lun ID. Defaults to "ATTACH".
        delete_original_volume (bool, optional): Indicates whether a replaced disk needs to be deleted after
            the restore operation. Used only if attachmentType is "REPLACE". Defaults to False.
        tags (Optional[list[CSPTag]], optional): List of tags assigned to the restored disk. Defaults to None.
        lun (str, optional): The lun ID under which the restored disk is to be attached to
            the virtual machine. Needed if attachmentType is "ATTACH". Note that there shouldn't be any disk
            attached to the virtual machine under this lun ID. Otherwise, the operation would fail. Defaults to None.

    Returns:
       PostRestoreCspVolumeModel : restore volume payload that can be used in restore_volume_and_wait()
    """

    azure_disk: RestoreAzureDiskInfoModel = RestoreAzureDiskInfoModel(
        csp_region=csp_region,
        resource_group_id=csp_resource_group_id,
        size_inGiB=size_in_gib,
        sku_name=sku_name,
        csp_tags=tags,
        availability_zones=availability_zones,
    )
    target_volume_info: TargetVolumeInfoModel = TargetVolumeInfoModel(
        account_id=account_id, csp_info=azure_disk, name=name
    )
    restore_volume_payload = PostRestoreCspVolumeModel(target_volume_info=target_volume_info)
    attachment_info: InstanceAttachmentInfoModel = None
    # if a virtual machine ID is provided, then populate an InstanceAttachmentInfoModel object
    if csp_machine_instance_id:
        attachment_info = InstanceAttachmentInfoModel(
            machine_instance_id=csp_machine_instance_id,
            attachment_type=attachment_type,
            delete_original_volume=delete_original_volume,
            lun=lun,
        )

    if attachment_info:
        restore_volume_payload.instance_attachment_info.append(attachment_info)

    return restore_volume_payload
