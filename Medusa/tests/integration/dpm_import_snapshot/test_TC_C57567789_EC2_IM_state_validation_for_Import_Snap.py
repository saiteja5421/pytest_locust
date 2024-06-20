"""
C57567789  EC2 : IM state validation for Import Snap.
        STEPS                                                      Expected protection status of the asset
1. Create EC2 Instance and two AMIs                                            Unprotected
    Refresh Inventory
    Check the status of the asset
2. Import AMI image of the asset and                                           Lapsed
    Check the status of the asset
3. Create a protection policy and assign the policy                            Partial
    to the asset Check the status of the asset
4. Take Backup of the asset using a protection policy                          Protected
    Check the status of the asset
5. One more Import AMI image for the same asset                                Protected
    Check the status of the asset
6. Remove policy of the asset and check the status of the asset                Lapsed
7. Delete the backups of the asset and check the status of the asset           Unprotected
"""

from datetime import (
    datetime,
)
import logging
import time
import uuid
from lib.common.enums.aws_region_zone import (
    AWSRegionZone,
)
from lib.common.enums.task_status import (
    TaskStatus,
)
from lib.common.enums.backup_type import (
    BackupType,
)
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import (
    CSPBackupListModel,
    CSPBackupModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_payload_model import (
    PostImportSnapshotModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import CSPMachineInstanceModel
from lib.platform.aws_boto3.models.instance import (
    Tag,
)
from tests.e2e.aws_protection.context import (
    Context,
)
from tests.steps.aws_protection.assets.standard_asset_creation_steps import (
    random_ami_chooser,
)
from tests.steps.aws_protection.cloud_account_manager_steps import get_csp_account_by_csp_name
import tests.steps.aws_protection.common_steps as CommonSteps
import tests.steps.aws_protection.inventory_manager_steps as InvMgrSteps
import tests.steps.aws_protection.import_snapshot.csp_import_snapshot_common_steps as CSPImportSnapshotCommonSteps
from lib.dscc.backup_recovery.aws_protection.common.models.import_aws_assets import ImportAWSAssetsByRegion
from tests.steps.tasks import (
    tasks,
)
from utils.timeout_manager import (
    TimeoutManager,
)
from pytest import (
    fixture,
)
from lib.common.enums.asset_info_types import (
    AssetType,
)
from lib.common.enums.protection_summary import (
    ProtectionStatus,
)
import tests.steps.aws_protection.policy_manager_steps as PolicyMgrSteps
import tests.steps.aws_protection.backup_steps as BackupSteps
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    CSPTag,
)
from lib.dscc.settings.dual_auth.authorization.models.dual_auth_operation import (
    DualAuthOperationList,
)
from lib.dscc.settings.dual_auth.authorization.payload.patch_request_approve_deny import (
    PatchRequestApproveDeny,
)
from lib.common.enums.provided_users import (
    ProvidedUser,
)


logger = logging.getLogger()

AWS_EC2_INSTANCE = None
AWS_EC2_AMI1 = None
AWS_EC2_AMI2 = None
AWS_EC2_BACKUP_IMAGE = None
TAG_KEY: str = "Name"
EC2_MACHINE_INSTANCE_TAG_VALUE: str = "TC_C57567789_MACHINE_INSTANCE" + str(uuid.uuid4())
AMI_TAG1_VALUE: str = "TC_C57567789_AMI1" + str(uuid.uuid4())
AMI_TAG2_VALUE: str = "TC_C57567789_AMI2" + str(uuid.uuid4())
POLICY_NAME: str = "TC_C57567789-ec2-MACHINE-INSTANCE-test Protection Policy" + str(uuid.uuid4())
AMI1_NAME: str = "TC_C57567789_IMAGE1" + str(uuid.uuid4())
AMI2_NAME: str = "TC_C57567789_IMAGE2" + str(uuid.uuid4())
ec2_machine_instance_tag: Tag = Tag(
    Key=TAG_KEY,
    Value=EC2_MACHINE_INSTANCE_TAG_VALUE,
)
ec2_ami1_tag: Tag = Tag(
    Key=TAG_KEY,
    Value=AMI_TAG1_VALUE,
)
ec2_ami2_tag: Tag = Tag(
    Key=TAG_KEY,
    Value=AMI_TAG2_VALUE,
)
csp_ami1_tag: CSPTag = CSPTag(
    key=TAG_KEY,
    value=AMI_TAG1_VALUE,
)
csp_ami2_tag: CSPTag = CSPTag(
    key=TAG_KEY,
    value=AMI_TAG2_VALUE,
)


@fixture(scope="module")
def context():
    context = Context()
    global AWS_EC2_INSTANCE, AWS_EC2_AMI1, AWS_EC2_AMI2

    # region EC2 and AMI creation
    KEY_PAIR_NAME = context.key_pair_region_one
    logger.info(KEY_PAIR_NAME)

    CommonSteps.validate_key_pair(
        aws=context.aws_one,
        key_pair_name=KEY_PAIR_NAME,
    )
    logger.info(f"Created Key Pair {KEY_PAIR_NAME}")

    logger.info("Creating EC2 instance")
    AWS_EC2_INSTANCE = context.aws_one.ec2.create_ec2_instance(
        key_name=KEY_PAIR_NAME,
        image_id=random_ami_chooser(context.aws_one),
        availability_zone=context.aws_one.ec2.get_availability_zone(),
        tags=[ec2_machine_instance_tag],
    )[0]
    logger.info(f"Created EC2 instance {AWS_EC2_INSTANCE.id}")

    logger.info(f"Creating AMI {AMI1_NAME}")
    AWS_EC2_AMI1 = context.aws_one.ec2.create_ec2_image(
        instance_id=AWS_EC2_INSTANCE.id,
        image_name=AMI1_NAME,
    )
    logger.info(f"Created AMI is {AWS_EC2_AMI1}")

    logger.info(f"Creating tag {ec2_ami1_tag} for AMI {AWS_EC2_AMI1}")
    context.aws_one.ec2.set_ami_tags(
        ami_id=AWS_EC2_AMI1["ImageId"],
        tags_list=[ec2_ami1_tag],
    )

    time.sleep(TimeoutManager.create_ami_inbetween_timeout)

    logger.info(f"Creating AMI {AMI2_NAME}")
    AWS_EC2_AMI2 = context.aws_one.ec2.create_ec2_image(
        instance_id=AWS_EC2_INSTANCE.id,
        image_name=AMI2_NAME,
    )
    logger.info(f"Created AMI is {AWS_EC2_AMI2}")

    logger.info(f"Creating tag {ec2_ami2_tag} for AMI {AWS_EC2_AMI2}")
    context.aws_one.ec2.set_ami_tags(
        ami_id=AWS_EC2_AMI2["ImageId"],
        tags_list=[ec2_ami2_tag],
    )

    # endregion

    yield context

    # region setup teardown
    if AWS_EC2_INSTANCE:
        logger.info(f"Terminating EC2 {AWS_EC2_INSTANCE.id}")
        context.aws_one.ec2.terminate_ec2_instance(ec2_instance_id=AWS_EC2_INSTANCE.id)

    logger.info(f"Deleting key pair {KEY_PAIR_NAME}")
    context.aws_one.ec2.delete_key_pair(key_name=KEY_PAIR_NAME)

    if AWS_EC2_AMI1:
        logger.info(f"Deleting AMI {AWS_EC2_AMI1}")
        context.aws_one.ec2.delete_ami(image_id=AWS_EC2_AMI1["ImageId"])

    if AWS_EC2_AMI2:
        logger.info(f"Deleting AMI {AWS_EC2_AMI2}")
        context.aws_one.ec2.delete_ami(image_id=AWS_EC2_AMI2["ImageId"])

    if AWS_EC2_BACKUP_IMAGE:
        for image in AWS_EC2_BACKUP_IMAGE:
            logger.info(f"Deleting image {image.id}")
            context.aws_one.ec2.delete_ami(image_id=image.id)

    if context.protection_policy_id:
        logger.info(f"Deleting Protection Policy {context.protection_policy_id}, {POLICY_NAME} and Protection Jobs")
        PolicyMgrSteps.delete_protection_jobs_and_policy(
            context=context,
            protection_policy_name=POLICY_NAME,
        )

    # endregion


def test_TC_C57567789_EC2_IM_state_validation_for_Import_Snap(
    context: Context,
):
    global AWS_EC2_INSTANCE, AWS_EC2_AMI1, AWS_EC2_AMI2, AWS_EC2_BACKUP_IMAGE

    # region Fetching Account and refreshing inventory
    csp_account: CSPAccountModel = get_csp_account_by_csp_name(context, account_name=context.aws_one_account_name)

    logger.info(f"Refreshing inventory for account {csp_account.id}")
    CommonSteps.refresh_inventory_with_retry(
        context=context,
        account_id=csp_account.id,
    )
    logger.info(f"Inventory refreshed for account {csp_account.id}")
    # endregion

    # region Retrieving created CSP Instance from dscc and validating protection status before importing images

    logger.info(f"Fetching CSP Instance using AWS Instance ID {AWS_EC2_INSTANCE.id}")
    csp_machine_instance: CSPMachineInstanceModel = InvMgrSteps.get_csp_instance_by_ec2_instance_id(
        context=context,
        ec2_instance_id=AWS_EC2_INSTANCE.id,
    )
    logger.info(f"CSP Instance retrieved is{csp_machine_instance}")

    assert csp_machine_instance.protectionStatus == ProtectionStatus.UNPROTECTED.value
    logger.info(f"CSP Instance {csp_machine_instance.name} protection status is->UNPROTECTED")
    # endregion

    # region Call to Import Snapshot endpoint and task validation
    post_import_snapshot_region: PostImportSnapshotModel = PostImportSnapshotModel(
        aws_regions=[AWSRegionZone(context.aws_one_region_name)],
        expiration=datetime(
            2025,
            12,
            2,
            13,
            30,
            45,
        ),
        tags=[csp_ami1_tag],
        import_volume_snapshots=False,
        import_machine_instance_images=True,
    )

    logger.info(f"Importing image for region {context.aws_one_region_name}")
    task_id: str = CSPImportSnapshotCommonSteps.import_snapshots_and_amis(
        context=context,
        csp_account_id=csp_account.id,
        post_import_snapshot=post_import_snapshot_region,
        wait_for_task=True,
    )
    logger.info(f"Task ID from import image for region {context.aws_one_region_name} is {task_id}")

    expected_amis = ImportAWSAssetsByRegion(
        region=AWSRegionZone(context.aws_one_region_name), num_expected=1, asset_names=[AWS_EC2_AMI1["ImageId"]]
    )

    logger.info(f"Validating imported image count in {task_id} task logs")
    CSPImportSnapshotCommonSteps.validate_ami_count_in_task_logs(
        context=context,
        parent_task_id=task_id,
        expected_amis=[expected_amis],
    )
    # endregion

    # region Retrieving ec2 Instance from dscc and validating protection status after importing image1
    logger.info(f"Waiting for CSP machine instance {csp_machine_instance.id} protection status to change to 'LAPSED'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[],
        ec2_assets=[AWS_EC2_INSTANCE.id],
        expected_status=ProtectionStatus.LAPSED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP machine instance {csp_machine_instance.id} protection status changed to 'LAPSED'")
    # endregion

    # region Retrieving ec2 Instance backup, validating imported image count and validating imported ami/image tag
    logger.info(f"Retrieving EC2 Instance {csp_machine_instance.id} backups")
    csp_machine_instance_backups: CSPBackupListModel = BackupSteps.get_csp_machine_instance_backups(
        context=context, machine_instance_id=csp_machine_instance.id
    )
    assert (
        csp_machine_instance_backups.total == 1
    ), f"Imported image with tag {ec2_ami1_tag} is not listed against CSP Machine Instance {csp_machine_instance.id}"
    logger.info(f"CSP machine instance imported image are {csp_machine_instance_backups.items}")

    csp_machine_instance_backup: CSPBackupModel = csp_machine_instance_backups.items[0]

    logger.info("Validating imported image tag in DSCC")
    assert csp_machine_instance_backup.name == ec2_ami1_tag.Value
    # endregion

    # region Create Protection Policy for Backup (AWS)
    PolicyMgrSteps.delete_protection_jobs_and_policy(
        context=context,
        protection_policy_name=POLICY_NAME,
    )
    context.protection_policy_id = PolicyMgrSteps.create_protection_policy(
        context=context,
        name=POLICY_NAME,
        backup_only=True,
    )
    logger.info(f"Protection Policy created, Name: {POLICY_NAME}, ID: {context.protection_policy_id}")
    # endregion

    # region Assign the Protection Policy to  ec2 Instance
    logger.info(f"Assigning Policy {context.protection_policy_id} to CSP Instance {csp_machine_instance.id}")
    PolicyMgrSteps.create_protection_job_for_asset(
        context=context,
        asset_id=csp_machine_instance.id,
        asset_type=AssetType.CSP_MACHINE_INSTANCE,
        protection_policy_id=context.protection_policy_id,
    )
    logger.info(f"CSP machine instance {csp_machine_instance.id} protected by policy: {context.protection_policy_id}")
    # endregion

    # region Retrieving ec2 Instance from dscc and validating protection status after assigning protection policy
    logger.info(f"Waiting for CSP Machine Instance{csp_machine_instance.id} status to change to 'Partial'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[],
        ec2_assets=[AWS_EC2_INSTANCE.id],
        expected_status=ProtectionStatus.PARTIAL,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Machine Instance {csp_machine_instance.id}status changed to 'Partial'")
    # endregion

    # region run backup for the EC2 Machine Instance asset
    BackupSteps.run_backup(
        context=context,
        asset_id=csp_machine_instance.id,
        backup_types=[BackupType.BACKUP],
    )
    # endregion

    # region Retrieving ec2 Instance backups, validating backup count and validating imported ami tag
    logger.info(f"Retrieving CSP Machine instance {csp_machine_instance.id} backups")
    csp_machine_instance_backups: CSPBackupListModel = BackupSteps.get_csp_machine_instance_backups(
        context=context, machine_instance_id=csp_machine_instance.id
    )
    assert csp_machine_instance_backups.total == 2, f"Backup failed for EC2 Instance {csp_machine_instance.id}"
    logger.info(f"CSP machine instance Backups are {csp_machine_instance_backups.items}")

    csp_machine_instance_backup1: CSPBackupModel = csp_machine_instance_backups.items[0]
    csp_machine_instance_backup2: CSPBackupModel = csp_machine_instance_backups.items[1]

    # Retrieving amis created on aws after policy run, using dscc "csp machine instance backup name" for cleanup
    AWS_EC2_BACKUP_IMAGE = context.aws_one.ec2.filter_ec2_images_by_tag(
        tag_name="Name",
        tag_values=[csp_machine_instance_backup2.name],
    )

    assert csp_machine_instance_backup1.name == ec2_ami1_tag.Value
    # endregion

    # region Retrieving ec2 Instance from dscc and validating protection status after running protection job
    logger.info(f"Waiting for CSP Machine Instance{csp_machine_instance.id} status to change to 'Protected'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[],
        ec2_assets=[AWS_EC2_INSTANCE.id],
        expected_status=ProtectionStatus.PROTECTED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Machine Instance {csp_machine_instance.id}status changed to 'Protected'")
    # endregion

    # region Call to Import Snapshot endpoint again for image2 of same EC2 asset and task validation
    post_import_snapshot_region: PostImportSnapshotModel = PostImportSnapshotModel(
        aws_regions=[AWSRegionZone(context.aws_one_region_name)],
        expiration=datetime(
            2025,
            12,
            2,
            13,
            30,
            45,
        ),
        import_tags=[csp_ami2_tag],
        import_volume_snapshots=False,
        import_machine_instance_images=True,
    )

    logger.info(f"Importing image for region {context.aws_one_region_name}")
    task_id: str = CSPImportSnapshotCommonSteps.import_snapshots_and_amis(
        context=context,
        csp_account_id=csp_account.id,
        post_import_snapshot=post_import_snapshot_region,
        wait_for_task=True,
    )
    logger.info(f"Task ID from import image for region {context.aws_one_region_name} is {task_id}")

    expected_amis = ImportAWSAssetsByRegion(
        region=AWSRegionZone(context.aws_one_region_name), num_expected=1, asset_names=[AWS_EC2_AMI2["ImageId"]]
    )

    logger.info(f"Validating imported image count in {task_id} task logs")
    CSPImportSnapshotCommonSteps.validate_ami_count_in_task_logs(
        context=context,
        parent_task_id=task_id,
        expected_amis=[expected_amis],
    )
    # endregion

    # region Retrieving ec2 Instance from dscc and validating protection status after repeated importing of image
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[],
        ec2_assets=[AWS_EC2_INSTANCE.id],
        expected_status=ProtectionStatus.PROTECTED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Machine Instance {csp_machine_instance.id}status is 'Protected'")
    # endregion

    # region Retrieving ec2 Instance from dscc and validating backup count after import image ->backup->import image
    logger.info(f"Retrieving CSP Machine instance {csp_machine_instance.id} backups")
    csp_machine_instance_backups: CSPBackupListModel = BackupSteps.get_csp_machine_instance_backups(
        context=context, machine_instance_id=csp_machine_instance.id
    )
    assert (
        csp_machine_instance_backups.total == 3
    ), f"Imported image with tag {ec2_ami1_tag} is not listed against CSP Machine Instance {csp_machine_instance.id}"
    logger.info(f"CSP Machine Instance Backups are {csp_machine_instance_backups.items}")

    csp_machine_instance_backup1: CSPBackupModel = csp_machine_instance_backups.items[0]
    csp_machine_instance_backup2: CSPBackupModel = csp_machine_instance_backups.items[1]
    csp_machine_instance_backup3: CSPBackupModel = csp_machine_instance_backups.items[2]

    assert csp_machine_instance_backup1.name == ec2_ami1_tag.Value
    assert csp_machine_instance_backup2.name == ec2_ami2_tag.Value
    # endregion

    # region deleting protection jobs and policy and validating protection status of the asset
    logger.info(f"Deleting Protection Policy {context.protection_policy_id}, {POLICY_NAME} and Protection Jobs")
    PolicyMgrSteps.delete_protection_jobs_and_policy(
        context=context,
        protection_policy_name=POLICY_NAME,
    )

    logger.info(f"Waiting for CSP Machine Instance {csp_machine_instance.id} protection status to change to 'LAPSED'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[],
        ec2_assets=[AWS_EC2_INSTANCE.id],
        expected_status=ProtectionStatus.LAPSED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Machine Instance {csp_machine_instance.id} protection status changed to 'LAPSED'")
    # endregion

    # region deleting backups of the Ec2 machine instance on DSCC and validating protection status of the asset

    # Deleting csp_machine_instance_backup1-Imported image1
    logger.info(f"Deleting imported image->{csp_machine_instance_backup1.name}")

    task_id = BackupSteps.delete_csp_machine_instance_backup_by_id(
        context=context,
        machine_instance_id=csp_machine_instance.id,
        backup_id=csp_machine_instance_backup1.id,
    )

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    context = Context(test_provided_user=ProvidedUser.user_two)

    auth_pending: DualAuthOperationList = context.dual_auth_manager.get_dual_auth_operations(request_state="Pending")

    dual_auth_operation_id = None

    for dual_auth_operation in auth_pending.items:
        if dual_auth_operation.name.__contains__(csp_machine_instance_backup1.id):
            dual_auth_operation_id = dual_auth_operation.id

    approval = PatchRequestApproveDeny(checked_status="Approved")

    context.dual_auth_manager.patch_request_approve_deny(
        id=dual_auth_operation_id,
        request_payload=approval,
    )

    context = Context()

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    status: str = tasks.wait_for_task(
        task_id,
        context.user,
        TimeoutManager.delete_backup_timeout,
    )

    assert (
        status.upper() == TaskStatus.success.value
    ), f"Error/permission issue in Deletion of imported image-{csp_machine_instance_backup1.name}"
    logger.info(f"Deletion of imported image-{csp_machine_instance_backup1.name}->success")

    AWS_EC2_AMI1 = None

    # Deleting csp_machine_instance_backup2-Imported image 2
    logger.info(f"Deleting imported image->{csp_machine_instance_backup2.name}")

    task_id = BackupSteps.delete_csp_machine_instance_backup_by_id(
        context=context,
        machine_instance_id=csp_machine_instance.id,
        backup_id=csp_machine_instance_backup2.id,
    )

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    context = Context(test_provided_user=ProvidedUser.user_two)

    auth_pending: DualAuthOperationList = context.dual_auth_manager.get_dual_auth_operations(request_state="Pending")

    dual_auth_operation_id = None

    for dual_auth_operation in auth_pending.items:
        if dual_auth_operation.name.__contains__(csp_machine_instance_backup2.id):
            dual_auth_operation_id = dual_auth_operation.id

    approval = PatchRequestApproveDeny(checked_status="Approved")

    context.dual_auth_manager.patch_request_approve_deny(
        id=dual_auth_operation_id,
        request_payload=approval,
    )

    context = Context()

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    status: str = tasks.wait_for_task(
        task_id,
        context.user,
        TimeoutManager.delete_backup_timeout,
    )

    assert (
        status.upper() == TaskStatus.success.value
    ), f"Error/permission issue in Deletion of imported image-{csp_machine_instance_backup2.name}"
    logger.info(f"Deletion of imported image-{csp_machine_instance_backup2.name}->success")

    AWS_EC2_AMI2 = None

    # Deleting csp_machine_instance_backup3-image/ami on aws created during protection policy run of EC2 Instance.
    logger.info(f"Deleting backup->{csp_machine_instance_backup3.name}")

    task_id = BackupSteps.delete_csp_machine_instance_backup_by_id(
        context=context,
        machine_instance_id=csp_machine_instance.id,
        backup_id=csp_machine_instance_backup3.id,
    )

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    context = Context(test_provided_user=ProvidedUser.user_two)

    auth_pending: DualAuthOperationList = context.dual_auth_manager.get_dual_auth_operations(request_state="Pending")

    dual_auth_operation_id = None

    for dual_auth_operation in auth_pending.items:
        if dual_auth_operation.name.__contains__(csp_machine_instance_backup3.id):
            dual_auth_operation_id = dual_auth_operation.id

    approval = PatchRequestApproveDeny(checked_status="Approved")

    context.dual_auth_manager.patch_request_approve_deny(
        id=dual_auth_operation_id,
        request_payload=approval,
    )

    context = Context()

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    status: str = tasks.wait_for_task(
        task_id,
        context.user,
        TimeoutManager.delete_backup_timeout,
    )

    assert (
        status.upper() == TaskStatus.success.value
    ), f"Error/permission issue in Deletion of backup-{csp_machine_instance_backup3.name}"
    logger.info(f"Deletion of backup-{csp_machine_instance_backup3.name}->success")

    AWS_EC2_BACKUP_IMAGE = None

    # validation of protection status of EC2 asset in DSCC after deleting all the backups
    logger.info(f"Waiting for CSP Machine Instance{csp_machine_instance.id} status to change to 'UNPROTECTED'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[],
        ec2_assets=[AWS_EC2_INSTANCE.id],
        expected_status=ProtectionStatus.UNPROTECTED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Machine Instance {csp_machine_instance.id}status changed to 'UNPROTECTED'")
    # endregion
