"""
This file contains functions related to restore RDS instance activity
"""

import logging
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_model import (
    CSPRDSInstanceBackupListModel,
    CSPRDSInstanceBackupModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_restore_payload_model import (
    PostRestoreCspRdsInstanceModel,
)
from utils.timeout_manager import TimeoutManager

from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.backup_state import BackupState
from lib.common.enums.status import Status
from lib.common.enums.task_status import TaskStatus
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSDBConnection
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.rds.aws_rds_steps import establish_and_validate_db_connection
from tests.steps.tasks import tasks


logger = logging.getLogger()


def restore_rds_instance(
    context: Context,
    csp_rds_instance_id: str,
    backup_id: str,
    database_identifier: str,
    wait_for_task: bool = True,
) -> str:
    """Function restore provided backup copy for a given RDS instance.

    Args:
        context (Context): The test context
        csp_rds_instance_id (str): csp rds instance id
        backup_id (str): native or cloud snapshot backup id
        database_identifier (str): name to set for the newly restored RDS instance.
        wait_for_task (bool, optional): Indicate wait for the restore activity to complete or not. Defaults to True.

    Returns:
        str: The task ID for the restore RDS instance workflow
    """
    logger.info(f"RDS restore for rds_id: {csp_rds_instance_id}, backup_id: {backup_id}")
    restore_timeout = TimeoutManager.restore_rds_backup_timeout
    payload = PostRestoreCspRdsInstanceModel(database_identifier=database_identifier)
    task_id = context.rds_data_protection_manager.restore_csp_rds_instance(
        backup_id=backup_id, rds_restore_payload=payload
    )
    if wait_for_task:
        logger.info(f"Wait {restore_timeout} seconds for RDS restore task")
        task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=restore_timeout,
        )
        assert (
            task_status.lower() == TaskStatus.success.value.lower()
        ), f"RDS restore task {task_id} failed with status {task_status}"
    logger.info("RDS restore task completed successfully")
    return task_id


def validate_rds_instance_after_restore(rds_db_connection: RDSDBConnection, checksum: dict) -> bool:
    """Function to validate the checksum in the restored RDS instance against checksum calculated prior to backup.

    Args:
        rds_db_connection (RDSDBConnection): RDS DB Connection Object
        checksum (dict) : dict

    Returns: bool, True when rds instance validation is successful, False otherwise.
    """
    result = True

    # Validate DB Connection
    db = establish_and_validate_db_connection(rds_db_connection=rds_db_connection)

    for table_name, checksum in checksum.items():
        restore_checksum = db.generate_checksum(table_name=table_name, db_name=rds_db_connection.db_name)
        if restore_checksum != checksum:
            logger.error(
                f"For table {table_name} restore checksum {restore_checksum} does not match backup checksum {checksum}"
            )
            result = False
    return result


def get_first_good_rds_instance_backup(
    context: Context, csp_rds_instance_id: str, backup_type: CSPBackupType
) -> CSPRDSInstanceBackupModel:
    """Return the first CSPRDSInstanceBackup of the type specified that has OK state and ACTIVE status.

    Args:
        context (Context): The test context
        csp_rds_instance_id (str): The CSP RDS Instance ID
        backup_type (CSPBackupType): The CSPBackupType to filter on

    Returns:
        CSPRDSInstanceBackupModel: A good RDS Backup if found, None otherwise
    """
    csp_rds_instance_backups: CSPRDSInstanceBackupListModel = (
        context.rds_data_protection_manager.get_csp_rds_instance_backups(csp_rds_id=csp_rds_instance_id)
    )

    item = None

    try:
        item = next(
            filter(
                lambda item: item.backup_type == backup_type
                and item.state == BackupState.OK
                and item.status == Status.ACTIVE,
                csp_rds_instance_backups.items,
            )
        )
        logger.info("Found a suitable RDS Backup")
    except StopIteration:
        logger.info("Did not find a suitable RDS Backup")

    return item
