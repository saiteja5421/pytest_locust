"""
C57567788  EBS : IM state validation for Import Snap
        STEPS                                             Expected protection status of the asset
1. Create EBS volume and two snapshots                              Unprotected
    Refresh Inventory
    Check the status of the asset
2. Import snap of the asset and Check the                            Lapsed
    status of the asset
3. Create a protection policy and assign the policy                  Partial
    to the asset Check the status of the asset
4. Take Backup of the asset using a protection policy                Protected
    Check the status of the asset
5. One more Import snap for the same asset                           Protected
    Check the status of the asset
6. Remove policy of the asset and check the                          Lapsed
    status of the asset
7. Delete the backups of the asset and                               Unprotected
    check the status of the asset
"""

from datetime import datetime
import time
import logging
import uuid
from pytest import fixture
from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.ebs_volume_type import EBSVolumeType
from lib.common.enums.task_status import TaskStatus
from lib.common.enums.backup_type import BackupType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import (
    CSPBackupListModel,
    CSPBackupModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_payload_model import (
    PostImportSnapshotModel,
)
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import CSPVolumeModel
from lib.platform.aws_boto3.models.instance import Tag
from lib.dscc.backup_recovery.aws_protection.common.models.import_aws_assets import ImportAWSAssetsByRegion
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.cloud_account_manager_steps import get_csp_account_by_csp_name
import tests.steps.aws_protection.common_steps as CommonSteps
import tests.steps.aws_protection.inventory_manager_steps as InvMgrSteps
import tests.steps.aws_protection.import_snapshot.csp_import_snapshot_common_steps as CSPImportSnapshotCommonSteps
from tests.steps.tasks import tasks
from utils.timeout_manager import TimeoutManager
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.protection_summary import ProtectionStatus
import tests.steps.aws_protection.policy_manager_steps as PolicyMgrSteps
import tests.steps.aws_protection.backup_steps as BackupSteps
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from lib.dscc.settings.dual_auth.authorization.models.dual_auth_operation import (
    DualAuthOperationList,
)
from lib.dscc.settings.dual_auth.authorization.payload.patch_request_approve_deny import (
    PatchRequestApproveDeny,
)
from lib.common.enums.provided_users import ProvidedUser

logger = logging.getLogger()
AWS_EBS_VOLUME = None
AWS_EBS_SNAPSHOT1 = None
AWS_EBS_SNAPSHOT2 = None
AWS_EBS_BACKUP_SNAPSHOT = None
TAG_KEY: str = "Name"
VOL_TAG_VALUE: str = "TC_C57567788_VOL" + str(uuid.uuid4())
SNAPSHOT1_TAG_VALUE: str = "TC_C57567788_S1" + str(uuid.uuid4())
SNAPSHOT2_TAG_VALUE: str = "TC_C57567788_S2" + str(uuid.uuid4())
POLICY_NAME: str = "TC_C57567788_VOL-ebs-test Protection Policy" + str(uuid.uuid4())
ebs_snapshot1_tag: Tag = Tag(Key=TAG_KEY, Value=SNAPSHOT1_TAG_VALUE)
ebs_snapshot2_tag: Tag = Tag(Key=TAG_KEY, Value=SNAPSHOT2_TAG_VALUE)
ebs_volume_tag: Tag = Tag(Key=TAG_KEY, Value=VOL_TAG_VALUE)
csp_snapshot1_tag: CSPTag = CSPTag(key=TAG_KEY, value=SNAPSHOT1_TAG_VALUE)
csp_snapshot2_tag: CSPTag = CSPTag(key=TAG_KEY, value=SNAPSHOT2_TAG_VALUE)


@fixture(scope="module")
def context():
    context = Context()
    global AWS_EBS_VOLUME, AWS_EBS_SNAPSHOT1, AWS_EBS_SNAPSHOT2

    # region EBS and snapshot creation
    logger.info("Creating EBS volume")
    AWS_EBS_VOLUME = context.aws_one.ebs.create_ebs_volume(
        availability_zone=context.aws_one.ec2.get_availability_zone(),
        size=1,
        volume_type=EBSVolumeType.GP2.value,
        tags=[ebs_volume_tag],
    )
    logger.info(f"Created EBS volume {AWS_EBS_VOLUME.id}")

    logger.info(f"Creating Snapshot1 for EBS Volume {AWS_EBS_VOLUME}")

    AWS_EBS_SNAPSHOT1 = context.aws_one.ebs.create_ebs_volume_snapshot(
        volume_id=AWS_EBS_VOLUME.id, description="EBS-Import-Snapshot1"
    )
    logger.info(f"Created snapshot {AWS_EBS_SNAPSHOT1}")

    logger.info(f"Creating Name tag for snapshot {AWS_EBS_SNAPSHOT1}")
    context.aws_one.ebs.set_snapshot_tags(snapshot_id=AWS_EBS_SNAPSHOT1.id, tags_list=[ebs_snapshot1_tag])

    time.sleep(TimeoutManager.create_snaphots_inbetween_timeout)

    logger.info(f"Creating Snapshot2 for EBS Volume {AWS_EBS_VOLUME}")
    AWS_EBS_SNAPSHOT2 = context.aws_one.ebs.create_ebs_volume_snapshot(
        volume_id=AWS_EBS_VOLUME.id, description="EBS-Import-Snapshot2"
    )
    logger.info(f"Created snapshot {AWS_EBS_SNAPSHOT2}")

    logger.info(f"Creating Name tag for snapshot {AWS_EBS_SNAPSHOT2}")
    context.aws_one.ebs.set_snapshot_tags(snapshot_id=AWS_EBS_SNAPSHOT2.id, tags_list=[ebs_snapshot2_tag])
    # endregion

    yield context

    # region setup teardown
    if AWS_EBS_VOLUME:
        logger.info(f"Deleting volume {AWS_EBS_VOLUME.id}")
        context.aws_one.ebs.delete_volume(volume_id=AWS_EBS_VOLUME.id)

    if AWS_EBS_SNAPSHOT1:
        logger.info(f"Deleting Snapshot {AWS_EBS_SNAPSHOT1.id}")
        context.aws_one.ebs.delete_snapshot(snapshot_id=AWS_EBS_SNAPSHOT1.id)

    if AWS_EBS_SNAPSHOT2:
        logger.info(f"Deleting Snapshot {AWS_EBS_SNAPSHOT2.id}")
        context.aws_one.ebs.delete_snapshot(snapshot_id=AWS_EBS_SNAPSHOT2.id)

    if AWS_EBS_BACKUP_SNAPSHOT:
        for snapshot in AWS_EBS_BACKUP_SNAPSHOT:
            logger.info(f"Deleting Snapshot {snapshot.id}")
            context.aws_one.ebs.delete_snapshot(snapshot_id=snapshot.id)

    if context.protection_policy_id:
        logger.info(f"Deleting Protection Policy {context.protection_policy_id}, {POLICY_NAME} and Protection Jobs")
        PolicyMgrSteps.delete_protection_jobs_and_policy(context=context, protection_policy_name=POLICY_NAME)
    # endregion


def test_TC_C57567788_EBS_IM_state_validation_for_Import_Snap(context: Context):
    global AWS_EBS_VOLUME, AWS_EBS_SNAPSHOT1, AWS_EBS_SNAPSHOT2, AWS_EBS_BACKUP_SNAPSHOT

    # region Fetching csp Account and refreshing inventory
    csp_account: CSPAccountModel = get_csp_account_by_csp_name(context, account_name=context.aws_one_account_name)

    logger.info(f"Refreshing inventory for account {csp_account.id}")
    CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account.id)
    logger.info(f"Inventory refreshed for account {csp_account.id}")
    # endregion

    # region Retrieving EBS volume from dscc and validating protection status before importing snapshots
    logger.info(f"Retrieving EBS Volume {AWS_EBS_VOLUME.id} from DSCC")
    csp_volume: CSPVolumeModel = InvMgrSteps.get_csp_volume_by_ebs_volume_id(
        context=context, ebs_volume_id=AWS_EBS_VOLUME.id, account_id=csp_account.id
    )

    logger.info(f"CSP Volume retrieved is {csp_volume}")

    assert csp_volume.protectionStatus == ProtectionStatus.UNPROTECTED.value
    logger.info(f"CSP Volume {csp_volume.name} protection status is->UNPROTECTED")
    # endregion

    # region Call to Import Snapshot endpoint and task validation
    post_import_snapshot_region: PostImportSnapshotModel = PostImportSnapshotModel(
        aws_regions=[AWSRegionZone(context.aws_one_region_name)],
        expiration=datetime(2025, 12, 2, 13, 30, 45),
        import_tags=[csp_snapshot1_tag],
        import_volume_snapshots=True,
        import_machine_instance_images=False,
    )

    logger.info(f"Importing snapshot for region {context.aws_one_region_name}")
    task_id: str = CSPImportSnapshotCommonSteps.import_snapshots_and_amis(
        context=context,
        csp_account_id=csp_account.id,
        post_import_snapshot=post_import_snapshot_region,
        wait_for_task=True,
    )
    logger.info(f"Task ID from import snapshot for region {context.aws_one_region_name} is {task_id}")

    expected_snapshots = ImportAWSAssetsByRegion(
        region=AWSRegionZone(context.aws_one_region_name), num_expected=1, asset_names=[AWS_EBS_SNAPSHOT1.id]
    )

    logger.info(f"Validating imported snapshot count in {task_id} task logs")
    CSPImportSnapshotCommonSteps.validate_snapshot_count_in_task_logs(
        context=context,
        parent_task_id=task_id,
        expected_snapshots=[expected_snapshots],
    )
    # endregion

    # region Retrieving EBS volume from dscc and validating protection status after import-snapshot of snapshot1
    logger.info(f"Waiting for CSP Volume {csp_volume.id} protection status to change to 'LAPSED'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[AWS_EBS_VOLUME.id],
        ec2_assets=[],
        expected_status=ProtectionStatus.LAPSED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Volume {csp_volume.id} protection status changed to 'LAPSED'")
    # endregion

    # region Retrieving csp volume backup and validating imported snapshot count and validating imported snapshot tag
    logger.info(f"Retrieving CSP Volume {csp_volume.id} backups")
    csp_volume_backups: CSPBackupListModel = BackupSteps.get_csp_volume_backups(
        context=context, volume_id=csp_volume.id
    )
    assert (
        csp_volume_backups.total == 1
    ), f"Import snapshot failure for {csp_volume.id} with snapshot tag{csp_snapshot1_tag}"
    logger.info(f"CSP Volume Backups are {csp_volume_backups.items}")

    csp_volume_backup: CSPBackupModel = csp_volume_backups.items[0]
    logger.info("Validating imported snapshot tag in DSCC")
    assert csp_volume_backup.name == ebs_snapshot1_tag.Value
    # endregion

    # region Create Protection Policy for Backup (AWS)
    PolicyMgrSteps.delete_protection_jobs_and_policy(context=context, protection_policy_name=POLICY_NAME)
    context.protection_policy_id = PolicyMgrSteps.create_protection_policy(
        context=context, name=POLICY_NAME, backup_only=True
    )
    logger.info(f"Protection Policy created, Name: {POLICY_NAME}, ID: {context.protection_policy_id}")
    # endregion

    # region Assign the Protection Policy to  EBS Volume
    PolicyMgrSteps.create_protection_job_for_asset(
        context=context,
        asset_id=csp_volume.id,
        asset_type=AssetType.CSP_VOLUME,
        protection_policy_id=context.protection_policy_id,
    )
    logger.info(f"csp_volume {csp_volume.id} protected by policy: {context.protection_policy_id}")
    # endregion

    # region Retrieving EBS volume from dscc and validating protection status after assigning protection policy
    logger.info(f"Waiting for CSP Volume {csp_volume.id} status to change to 'PARTIAL'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[AWS_EBS_VOLUME.id],
        ec2_assets=[],
        expected_status=ProtectionStatus.PARTIAL,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Volume {csp_volume.id} status changed to 'PARTIAL'")
    # endregion

    # region run backup for the EBS volume asset
    BackupSteps.run_backup(context=context, asset_id=csp_volume.id, backup_types=[BackupType.BACKUP])
    # endregion

    # region Retrieving csp volume backups and validating backup count
    logger.info(f"Retrieving CSP Volume {csp_volume.id} backups")
    csp_volume_backups: CSPBackupListModel = BackupSteps.get_csp_volume_backups(
        context=context, volume_id=csp_volume.id
    )
    assert csp_volume_backups.total == 2, f"Backup failed for volume {csp_volume.id}"
    logger.info(f"CSP Volume Backups are {csp_volume_backups.items}")

    csp_volume_backup1: CSPBackupModel = csp_volume_backups.items[0]
    csp_volume_backup2: CSPBackupModel = csp_volume_backups.items[1]

    # Retrieving Backup snapshot created on aws after policy run, using dscc volume backup name for cleanup
    AWS_EBS_BACKUP_SNAPSHOT = context.aws_one.ebs.filter_ebs_snapshots_by_tag(
        tag_name="Name", tag_values=[csp_volume_backup2.name]
    )
    assert csp_volume_backup1.name == ebs_snapshot1_tag.Value

    # endregion

    # region Retrieving EBS volume and validating protection status after running protection job
    logger.info(f"Waiting for CSP Volume {csp_volume.id} protection status to change to 'PROTECTED'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[AWS_EBS_VOLUME.id],
        ec2_assets=[],
        expected_status=ProtectionStatus.PROTECTED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Volume {csp_volume.id} protection status changed to 'PROTECTED'")
    # endregion

    # region Call to Import Snapshot endpoint again for another snapshot2 of same EBS asset and task validation
    post_import_snapshot_region: PostImportSnapshotModel = PostImportSnapshotModel(
        aws_regions=[AWSRegionZone(context.aws_one_region_name)],
        expiration=datetime(2025, 12, 2, 13, 30, 45),
        import_tags=[csp_snapshot2_tag],
        import_volume_snapshots=True,
        import_machine_instance_images=False,
    )

    logger.info(f"Importing snapshot for region {context.aws_one_region_name}")
    task_id: str = CSPImportSnapshotCommonSteps.import_snapshots_and_amis(
        context=context,
        csp_account_id=csp_account.id,
        post_import_snapshot=post_import_snapshot_region,
        wait_for_task=True,
    )
    logger.info(f"Task ID from import snapshot for region {context.aws_one_region_name} is {task_id}")

    expected_snapshots = ImportAWSAssetsByRegion(
        region=AWSRegionZone(context.aws_one_region_name), num_expected=1, asset_names=[AWS_EBS_SNAPSHOT2.id]
    )

    logger.info(f"Validating imported snapshot count in {task_id} task logs")
    CSPImportSnapshotCommonSteps.validate_snapshot_count_in_task_logs(
        context=context,
        parent_task_id=task_id,
        expected_snapshots=[expected_snapshots],
    )
    # endregion

    # region Retrieving  EBS volume from dscc and validating protection status after repeated import-snapshot
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[AWS_EBS_VOLUME.id],
        ec2_assets=[],
        expected_status=ProtectionStatus.PROTECTED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Volume {csp_volume.id} protection status is 'PROTECTED'")
    # endregion

    # region Retrieving csp volume backup and validating backup count after import snapshot->backup->import snapshot
    logger.info(f"Retrieving CSP Volume {csp_volume.id} backups")
    csp_volume_backups: CSPBackupListModel = BackupSteps.get_csp_volume_backups(
        context=context, volume_id=csp_volume.id
    )
    assert (
        csp_volume_backups.total == 3
    ), f"Import snapshot failure for {csp_volume.id} with snapshot tag{csp_snapshot2_tag}"
    logger.info(f"CSP Volume Backups are {csp_volume_backups.items}")

    csp_volume_backup1: CSPBackupModel = csp_volume_backups.items[0]
    csp_volume_backup2: CSPBackupModel = csp_volume_backups.items[1]
    csp_volume_backup3: CSPBackupModel = csp_volume_backups.items[2]

    assert csp_volume_backup1.name == ebs_snapshot1_tag.Value
    assert csp_volume_backup2.name == ebs_snapshot2_tag.Value
    # endregion

    # region deleting ptotection jobs and policy and validating protection status of the asset
    logger.info(f"Deleting Protection Policy {context.protection_policy_id}, {POLICY_NAME} and Protection Jobs")
    PolicyMgrSteps.delete_protection_jobs_and_policy(context=context, protection_policy_name=POLICY_NAME)
    logger.info(f"Waiting for CSP Volume {csp_volume.id} protection status to change to 'LAPSED'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[AWS_EBS_VOLUME.id],
        ec2_assets=[],
        expected_status=ProtectionStatus.LAPSED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Volume {csp_volume.id} protection status changed to 'LAPSED'")
    # endregion

    # region deleting backups of the EBS volume on DSCC and validating protection status of the asset

    # Deleting csp_volume_backup1-Imported snapshot1
    logger.info(f"Deleting imported snapshot->{csp_volume_backup1.name}")

    task_id = BackupSteps.delete_csp_volume_backup_by_id(
        context=context,
        volume_id=csp_volume.id,
        backup_id=csp_volume_backup1.id,
    )

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    context = Context(test_provided_user=ProvidedUser.user_two)

    auth_pending: DualAuthOperationList = context.dual_auth_manager.get_dual_auth_operations(request_state="Pending")

    dual_auth_operation_id = None

    for dual_auth_operation in auth_pending.items:
        if dual_auth_operation.name.__contains__(csp_volume_backup1.id):
            dual_auth_operation_id = dual_auth_operation.id

    approval = PatchRequestApproveDeny(checked_status="Approved")

    context.dual_auth_manager.patch_request_approve_deny(id=dual_auth_operation_id, request_payload=approval)

    context = Context()

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.delete_backup_timeout)

    assert (
        status.upper() == TaskStatus.success.value
    ), f"Error/permission issue in Deletion of imported snapshot-{csp_volume_backup1.name}"
    logger.info(f"Deletion of imported snapshot-{csp_volume_backup1.name}->success")

    AWS_EBS_SNAPSHOT1 = None

    # Deleting csp_volume_backup2-Imported snapshot2
    logger.info(f"Deleting imported snapshot->{csp_volume_backup2.name}")

    task_id = BackupSteps.delete_csp_volume_backup_by_id(
        context=context,
        volume_id=csp_volume.id,
        backup_id=csp_volume_backup2.id,
    )

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    context = Context(test_provided_user=ProvidedUser.user_two)

    auth_pending: DualAuthOperationList = context.dual_auth_manager.get_dual_auth_operations(request_state="Pending")

    dual_auth_operation_id = None

    for dual_auth_operation in auth_pending.items:
        if dual_auth_operation.name.__contains__(csp_volume_backup2.id):
            dual_auth_operation_id = dual_auth_operation.id

    approval = PatchRequestApproveDeny(checked_status="Approved")

    context.dual_auth_manager.patch_request_approve_deny(id=dual_auth_operation_id, request_payload=approval)

    context = Context()

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.delete_backup_timeout)

    assert (
        status.upper() == TaskStatus.success.value
    ), f"Error/permission issue in Deletion of imported snapshot-{csp_volume_backup2.name}"
    logger.info(f"Deletion of imported snapshot-{csp_volume_backup2.name}->success")

    AWS_EBS_SNAPSHOT2 = None

    # Deleting csp_volume_backup3-snaphot on aws created during protection policy run of EBS volume.
    logger.info(f"Deleting backup->{csp_volume_backup3.name}")

    task_id = BackupSteps.delete_csp_volume_backup_by_id(
        context=context,
        volume_id=csp_volume.id,
        backup_id=csp_volume_backup3.id,
    )

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    context = Context(test_provided_user=ProvidedUser.user_two)

    auth_pending: DualAuthOperationList = context.dual_auth_manager.get_dual_auth_operations(request_state="Pending")

    dual_auth_operation_id = None

    for dual_auth_operation in auth_pending.items:
        if dual_auth_operation.name.__contains__(csp_volume_backup3.id):
            dual_auth_operation_id = dual_auth_operation.id

    approval = PatchRequestApproveDeny(checked_status="Approved")

    context.dual_auth_manager.patch_request_approve_deny(id=dual_auth_operation_id, request_payload=approval)

    context = Context()

    time.sleep(TimeoutManager.dual_auth_task_inbetween_timeout)

    status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.delete_backup_timeout)

    assert (
        status.upper() == TaskStatus.success.value
    ), f"Error/permission issue in Deletion of backup-{csp_volume_backup3.name}"
    logger.info(f"Deletion of backup-{csp_volume_backup3.name}->success")

    AWS_EBS_BACKUP_SNAPSHOT = None

    # validation of protection status of EBS asset in DSCC after deleting all the backups
    logger.info(f"Waiting for CSP Volume {csp_volume.id} protection status to change to 'UNPROTECTED'")
    InvMgrSteps.wait_for_asset_protection_status_for_assets(
        context=context,
        volume_assets=[AWS_EBS_VOLUME.id],
        ec2_assets=[],
        expected_status=ProtectionStatus.UNPROTECTED,
        account_id=csp_account.id,
    )
    logger.info(f"CSP Volume {csp_volume.id} protection status changed to 'UNPROTECTED'")
    # endregion
