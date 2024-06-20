import logging


from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.csp_protection_job_type import CSPProtectionJobType
from lib.common.enums.kafka_inventory_asset_type import KafkaInventoryAssetType
from lib.common.enums.backup_kafka_event_status import BackupKafkaEventStatus
from lib.common.enums.kafka_backup_type import KafkaBackupType
from lib.common.enums.protection_summary import ProtectionStatus
from lib.common.enums.protection_types import ProtectionType

from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.protection_job_steps import KafkaProtectionJob
from tests.steps.aws_protection.backup_steps import KafkaBackupNotifier
from tests.steps.aws_protection.inventory_manager_steps import wait_for_asset_protection_status

logger = logging.getLogger()


def apply_asset_protection_status(
    context: Context,
    customer_id: str,
    asset_type: AssetType,
    asset_id: str,
    csp_asset_id: str,
    protection_status: ProtectionStatus,
    account_id: str = None,
    wait: bool = True,
) -> tuple[KafkaProtectionJob, KafkaBackupNotifier]:
    """This method will set the requested protection status for an asset
    Args:
        context (Context): aws connection context
        customer_id (str): customer Id
        asset_type (AssetType): Asset Type
        asset_id (str): AWS asset asset Id
        csp_asset_id (str): CSP Id of an asset
        protection_status (ProtectionStatus): Protection Status of asset
        account_id (str): CSP account id
        wait (bool) : Wait for status reflect in asset. Set to True as default

    Returns:
        KafkaProtectionJob, KafkaBackupNotifier: Protection Job, Backup
    """
    if asset_type == AssetType.CSP_VOLUME:
        backup_asset_type = KafkaInventoryAssetType.ASSET_TYPE_VOLUME
    elif asset_type == AssetType.CSP_MACHINE_INSTANCE:
        backup_asset_type = KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE

    job = create_protection_job(
        context=context,
        customer_id=customer_id,
        asset_type=asset_type,
        csp_asset_id=csp_asset_id,
    )
    backup = KafkaBackupNotifier(
        context=context,
        customer_id=customer_id,
        backup_type=KafkaBackupType.BACKUP_TYPE_CLOUDBACKUP,
        asset_id=csp_asset_id,
        asset_type=backup_asset_type,
        protection_job_id=job.get_protection_job_id(),
        schedule_id=job.get_schedule_id(),
    )
    if protection_status == ProtectionStatus.LAPSED:
        backup.create(
            event_status=BackupKafkaEventStatus.SUCCESS,
        )
        job.delete()
    elif protection_status == ProtectionStatus.PAUSED:
        backup.create(
            event_status=BackupKafkaEventStatus.SUCCESS,
        )
        job.suspend()
    elif protection_status == ProtectionStatus.PROTECTED:
        backup.create(
            event_status=BackupKafkaEventStatus.SUCCESS,
        )
    elif protection_status == ProtectionStatus.PENDING:
        backup = None

    if wait:
        wait_for_asset_protection_status(
            context=context,
            asset_id=asset_id,
            expected_status=protection_status,
            asset_type=asset_type,
            account_id=account_id,
        )
    return job, backup


def create_protection_job(
    context: Context,
    customer_id: str,
    asset_type: AssetType,
    csp_asset_id: str,
    protection_type: ProtectionType = ProtectionType.CLOUD_BACKUP,
) -> KafkaProtectionJob:
    """This method will set the protection job for an asset
    Args:
        context (Context): aws connection context
        customer_id (str): customer Id
        asset_type (AssetType): Asset Type
        asset_id (str): AWS asset asset Id
        csp_asset_id (str): CSP Id of an asset
        protection_type (ProtectionType): Protection Type. Set to Cloud Backup as default

    Returns:
        KafkaProtectionJob: Protection Job
    """
    if asset_type == AssetType.CSP_VOLUME:
        asset_job_type = CSPProtectionJobType.CSP_VOLUME_PROT_JOB
    elif asset_type == AssetType.CSP_MACHINE_INSTANCE:
        asset_job_type = CSPProtectionJobType.CSP_MACHINE_INSTANCE_PROT_JOB

    job = KafkaProtectionJob(
        context=context,
        customer_id=customer_id,
        csp_asset_id=csp_asset_id,
        asset_type=asset_job_type,
        protection_type=protection_type,
    )
    job.create(
        wait_for_complete=True,
    )
    return job
