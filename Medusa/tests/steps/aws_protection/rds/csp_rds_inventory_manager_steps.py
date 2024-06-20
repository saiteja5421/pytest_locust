import logging
import time
import requests
from waiting import TimeoutExpired, wait
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_instance_model import (
    CSPRDSInstanceListModel,
    CSPRDSInstanceModel,
)
from utils.timeout_manager import TimeoutManager

# Internal libraries
from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.db_engine import DBEngine
from lib.common.enums.protection_summary import ProtectionStatus
from lib.common.enums.task_status import TaskStatus
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSProtectionJobInfo
from lib.platform.aws_boto3.aws_factory import AWS

# Steps
from tests.e2e.aws_protection.context import Context
from tests.steps.tasks import tasks
import tests.steps.aws_protection.common_steps as CommonSteps

"""
This file contains all the functions for the RDS inventory management

Below are the foolowing Region categories of this file:
-   RDS Inventory/Instance Refresh
-   RDS Protection Jobs & Protection Status
-   CSP/AWS RDS Instance & Info

"""

logger = logging.getLogger()


# region RDS Inventory/Instance Refresh


def perform_rds_inventory_refresh(context: Context, csp_account_id: str, wait_for_task: bool = True) -> str:
    """
    Args:
        context (Context): Context object
        csp_account_id (str): csp account uuid
        wait_for_task (bool, optional): Boolean value to wait of the task. Defaults to True.

    Returns:
        str: The task ID for the RDS inventory request in DSCC
    """
    logger.info(f"Refreshing inventory for RDS account {csp_account_id}")
    task_id = context.rds_inventory_manager.refresh_rds_account(csp_account_id=csp_account_id)

    if wait_for_task:
        logger.info(f"Waiting for inventory refresh for RDS account {csp_account_id} to complete")
        refresh_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.task_timeout,
        )
        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"Account {csp_account_id} inventory refresh failure, refresh_task_status={refresh_task_status}"

    return task_id


def perform_rds_inventory_refresh_with_retry(
    context: Context,
    csp_account_id: str,
    retry_count: int = 5,
) -> str:
    """
    Args:
        context (Context): Context object
        csp_account_id (str): csp account uuid
        retry_count: Count for retrying RDS Account refresh

    Returns:
        str: The task ID for the RDS inventory request in DSCC
    """
    refresh_task_id: str = None

    logger.info(f"Refreshing inventory for RDS account {csp_account_id}")
    for i in range(retry_count + 1):
        status_code, refresh_task_id = context.rds_inventory_manager.refresh_rds_account_status_code(
            csp_account_id=csp_account_id
        )
        if status_code != requests.codes.accepted and (i < retry_count):
            logger.warn(f"RDS Inventory refresh retry required, status_code = {status_code}")
            time.sleep(60)
        elif status_code == requests.codes.accepted and (i < retry_count):
            logger.info(f"Waiting for inventory refresh for RDS account {csp_account_id} to complete")
            refresh_task_status: str = tasks.wait_for_task(
                task_id=refresh_task_id,
                user=context.user,
                timeout=TimeoutManager.standard_task_timeout,
            )
            assert (
                refresh_task_status.upper() == TaskStatus.success.value
            ), f"RDS Account {csp_account_id} inventory refresh failure, refresh_task_status={refresh_task_status}"
            break

    return refresh_task_id


def get_csp_rds_instances(
    context: Context,
    filter: str = "",
    expected_status_code: int = requests.codes.ok,
) -> CSPRDSInstanceListModel:
    """Returns a list of CSP RDS instances

    Args:
        context (Context): Context object
        filter (str, optional): Used to filter the set of resources returned in the response.
        “eq” : Is a property equal to value. Valid for number, boolean and string properties.
            Filters are supported on following attributes:
            - accountId
            - name
            - protectionStatus
        expected_status_code (int, optional): Status code expected when trying to retrieve RDS instances.
        Defaults to 'requests.codes.ok'

    Returns:
        CSPRDSInstanceListModel: list of CSP RDS instances
    """
    csp_rds_instances: CSPRDSInstanceListModel = context.rds_inventory_manager.get_csp_rds_instances(
        filter=filter,
        expected_status_code=expected_status_code,
    )
    return csp_rds_instances


def get_csp_rds_instance_by_id(context: Context, csp_rds_instance_id: str) -> CSPRDSInstanceModel:
    """Returns RDS Instance by its CSP ID

    Args:
        context (Context): Context object
        csp_rds_instance_id (str): RDS Instance's CSP ID

    Returns:
        _type_: CSPRDSInstanceModel
    """
    csp_rds_instance: CSPRDSInstanceModel = context.rds_inventory_manager.get_csp_rds_instance_by_id(
        csp_rds_instance_id=csp_rds_instance_id
    )
    return csp_rds_instance


def perform_rds_instance_refresh(context: Context, csp_rds_instance_id: str, wait_for_task: bool = True) -> str:
    """
    Args:
        context (Context): Context object
        csp_rds_instance_id (str): Unique identifier (UUID) of a CSP RDS instance
        wait_for_task (bool, optional): Boolean value to wait of the task. Defaults to True.

    Returns:
        str: The task ID for the RDS inventory request in DSCC
    """
    logger.info(f"Refreshing RDS instance {csp_rds_instance_id}")
    task_id = context.rds_inventory_manager.refresh_rds_instance(csp_rds_instance_id=csp_rds_instance_id)

    if wait_for_task:
        logger.info(f"Waiting for RDS instance refresh {csp_rds_instance_id} to complete")
        refresh_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.task_timeout,
        )

        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"RDS instance {csp_rds_instance_id} refresh failed, refresh_task_status={refresh_task_status}"

    return task_id


# endregion

# region RDS Protection Jobs & Protection Status


def get_rds_protection_status(context: Context, csp_rds_instance_id: str) -> str:
    """Function returns protection status of an RDS instance.

    Args:
        context (Context): Context object
        csp_rds_instance_id (str): csp rds instance id

    Returns:
        str: The protection status of an RDS instance
    """
    csp_rds_instance_protection_status: str = None
    csp_rds_instance: CSPRDSInstanceModel = context.rds_inventory_manager.get_csp_rds_instance_by_id(
        csp_rds_instance_id=csp_rds_instance_id
    )

    logger.info(f"CSP RDS Instance = {csp_rds_instance}")

    if csp_rds_instance:
        csp_rds_instance_protection_status = csp_rds_instance.protection_status
        logger.info(f"CSP RDS Instance Protection Status = {csp_rds_instance_protection_status}")

    return csp_rds_instance_protection_status


def wait_for_rds_protection_status(
    context: Context,
    csp_rds_instance_id: str,
    expected_status: ProtectionStatus,
):
    def _wait_for_protection_job():
        csp_rds_instance: CSPRDSInstanceModel = context.rds_inventory_manager.get_csp_rds_instance_by_id(
            csp_rds_instance_id=csp_rds_instance_id
        )
        return csp_rds_instance.protection_status == expected_status.value

    # wait for job completion
    try:
        wait(_wait_for_protection_job, timeout_seconds=240, sleep_seconds=10)
    except TimeoutExpired:
        assert (
            False
        ), f"wait_for_asset_protection_status timeout, asset={csp_rds_instance_id}, expected_status={expected_status}"


def get_rds_instance_protection_jobs(context: Context, csp_rds_instance_id: str) -> list[RDSProtectionJobInfo]:
    """Get the Protection Jobs for the RDS Instance

    Args:
        context (Context): The test context
        csp_rds_instance_id (str): The CSP RDS Instance ID

    Returns:
        list[RDSProtectionJobInfo]: A list of RDSProtectionJobInfo for the RDS Instance
    """
    rds_instance = context.rds_inventory_manager.get_csp_rds_instance_by_id(csp_rds_instance_id=csp_rds_instance_id)
    return rds_instance.protection_job_info


def wait_for_rds_protection_job_assignment(context: Context, csp_rds_instance_id: str):
    """
    RDS standard asset has had a Protection Policy assigned.
    Wait for the asset to reflect that it now has a Protection Job.
    """
    rds_instance_lambda = lambda x: len(get_rds_instance_protection_jobs(context=context, csp_rds_instance_id=x)) > 0

    CommonSteps.wait_for_condition(
        lambda: rds_instance_lambda(x=csp_rds_instance_id),
        error_msg=f"RDS Instance {csp_rds_instance_id} does not claim to have a protection job",
    )


def wait_for_rds_protection_job_unassignment(context: Context, csp_rds_instance_id: str):
    """
    RDS standard asset has had Protection Policies un-assigned.
    Wait for the asset to reflect that it no longer has a Protection Job.
    """
    rds_instance_lambda = lambda x: len(get_rds_instance_protection_jobs(context=context, csp_rds_instance_id=x)) == 0

    CommonSteps.wait_for_condition(
        lambda: rds_instance_lambda(x=csp_rds_instance_id),
        error_msg=f"RDS Instance {csp_rds_instance_id} still claims to be protected",
    )


# endregion

# region CSP/AWS RDS Instance & Info


def get_list_of_rds_instances_by_region(
    context: Context,
    csp_account_id: str,
    region: AWSRegionZone,
) -> list[CSPRDSInstanceModel]:
    """
    Args:
        context (Context): Context object
        csp_account_id (str): csp account uuid
        region (AWSRegionZone): AWS region to filter the RDS instances

    Returns:
        list[CSPRDSInstanceModel]: List of csp rds instances belonging to the provided account and region.
    """
    # use filter query to retrieve the list of csp instances based on region.
    # NOTE: Natesh said that for the first release 'filter' will not be supported for this endpoint :( -_-
    # NOTE: The return type can be changed to CSPRDSInstanceList once the filters are supported

    csp_rds_instances: CSPRDSInstanceListModel = context.rds_inventory_manager.get_csp_rds_instances()

    csp_rds_instances_filtered_by_region: list[CSPRDSInstanceModel] = list(
        filter(
            lambda csp_rds_instance: csp_rds_instance.csp_info.csp_region == region.value
            and csp_rds_instance.account_info.id == csp_account_id,
            csp_rds_instances.items,
        )
    )

    logger.info(f"RDS Instances in region {region.value} are {csp_rds_instances_filtered_by_region}")

    return csp_rds_instances_filtered_by_region


def get_db_identifier_using_csp_rds_instance_id(context: Context, csp_rds_instance_id: str) -> str:
    """
    Args:
        context (Context): Context object
        csp_rds_instance_id (str): csp rds instance uuid

    Returns:
        str: The user defined name (db identifier) for the given rds instance
    """
    csp_rds_instance_identified: str = None
    csp_rds_instance: CSPRDSInstanceModel = context.rds_inventory_manager.get_csp_rds_instance_by_id(
        csp_rds_instance_id=csp_rds_instance_id
    )

    logger.info(f"CSP RDS Instance = {csp_rds_instance}")

    if csp_rds_instance:
        csp_rds_instance_identified = csp_rds_instance.csp_info.identifier
        logger.info(f"CSP RDS Instance Identifier = {csp_rds_instance_identified}")

    return csp_rds_instance_identified


def get_csp_rds_instance_using_db_identifier(
    context: Context, db_identifier: str, region: str, state: str = "OK"
) -> CSPRDSInstanceModel:
    """
    Args:
        context (Context): Context object
        db_identifier (str): User defined name for the RDS instance in AWS console
        region (str): Region of the DB Instance

    Returns:
        CSPRDSInstanceModel: The csp rds instance uuid for the given db identifier.
    """
    # NOTE: Updated the method to return the CPSRDSInstance as the rds_instance_id in itself did not seem very useful
    # NOTE: Add filter to parse through region, you can have the same DB Identifier in multiple regions
    csp_rds_instances: CSPRDSInstanceListModel = context.rds_inventory_manager.get_csp_rds_instances()

    csp_rds_instances = list(
        filter(
            lambda csp_rds_instance: (
                (csp_rds_instance.csp_info.identifier == db_identifier)
                and (csp_rds_instance.csp_info.csp_region == region)
                and (csp_rds_instance.state == state)
            ),
            csp_rds_instances.items,
        )
    )

    assert len(csp_rds_instances) == 1, f"RDS instances not found {csp_rds_instances}"
    logger.info(f"CSP RDS Instance with identifier {db_identifier} in region {region} is {csp_rds_instances[0]}")

    return csp_rds_instances[0]


def get_rds_engine_name(context: Context, csp_rds_instance_id: str) -> str:
    """
    Args:
        context (Context): Context object
        csp_rds_instance_id (str): csp rds instance uuid

    Returns:
        str: The name of the RDS engine.
        eg. MySQL, MariaDB, Postgres.
    """
    csp_rds_instance_engine: str = None
    csp_rds_instance: CSPRDSInstanceModel = context.rds_inventory_manager.get_csp_rds_instance_by_id(
        csp_rds_instance_id=csp_rds_instance_id
    )

    logger.info(f"CSP RDS Instance = {csp_rds_instance}")

    if csp_rds_instance:
        csp_rds_instance_engine = csp_rds_instance.csp_info.engine
        logger.info(f"CSP RDS Instance Engine = {csp_rds_instance_engine}")

    return csp_rds_instance_engine


def get_csp_rds_instance_status(context: Context, csp_rds_instance_id: str) -> str:
    """
    Args:
        context (Context): Context object
        csp_rds_instance_id (str): csp rds instance uuid

    Returns:
        str: The current status of the RDS instance.
    """
    csp_rds_instance_state: str = None
    csp_rds_instance: CSPRDSInstanceModel = context.rds_inventory_manager.get_csp_rds_instance_by_id(
        csp_rds_instance_id=csp_rds_instance_id
    )

    logger.info(f"CSP RDS Instance = {csp_rds_instance}")

    if csp_rds_instance:
        csp_rds_instance_state = csp_rds_instance.state
        logger.info(f"CSP RDS Instance State = {csp_rds_instance_state}")

    return csp_rds_instance_state


def get_list_of_csp_rds_instances_by_db_engine(
    context: Context,
    csp_account_id: str,
    db_engine: DBEngine,
) -> list[CSPRDSInstanceModel]:
    """
    Args:
        context (Context): Context object
        csp_account_id (str): Account ID from which the RDS instances need to be fetched
        engine (DBEngine): RDS engine name to filter the RDS inventory

    Returns:
        list[CSPRDSInstanceModel]: List of csp rds instance with the same RDS engine
    """
    # use filter query to retrieve the list of instances by engine if REST api supports.
    # NOTE: Natesh said that for the first release 'filter' will not be supported for this endpoint :( -_-
    # NOTE: The return type can be changed to CSPRDSInstanceList once the filters are supported

    csp_rds_instances: CSPRDSInstanceListModel = context.rds_inventory_manager.get_csp_rds_instances()

    csp_rds_instances_filtered_by_engine: list[CSPRDSInstanceModel] = list(
        filter(
            lambda csp_rds_instance: csp_rds_instance.csp_info.engine == db_engine.value
            and csp_rds_instance.account_info.id == csp_account_id,
            csp_rds_instances.items,
        )
    )

    logger.info(f"RDS Instances with engine {db_engine.value} are {csp_rds_instances_filtered_by_engine}")

    return csp_rds_instances_filtered_by_engine


def compare_aws_and_dscc_assets(context: Context, aws: AWS, csp_account_id: str):
    # AWS RDS Instances
    aws_rds_instance_list = aws.rds.get_all_db_instances()
    # DSCC RDS Instances
    atlantia_rds_instance_list: CSPRDSInstanceListModel = context.rds_inventory_manager.get_csp_rds_instances()

    # DSCC RDS ID List
    atlantia_rds_list = [
        item.csp_info.identifier
        for item in atlantia_rds_instance_list.items
        if item.account_info.id == csp_account_id and context.aws_one_region_name in item.csp_info.csp_region
    ]
    logger.info(f"RDS DB in DSCC: {atlantia_rds_list} for region: {context.aws_one_region_name}")

    # Assert AWS ID is present in DSCC ID List
    for aws_item in aws_rds_instance_list:
        db_id = aws_item["DBInstanceIdentifier"]
        logger.info(f"AWS RDS ID = {db_id}")
        assert db_id in atlantia_rds_list


# endregion


def get_csp_rds_instance_by_tag(context: Context, tag: CSPTag) -> list[CSPRDSInstanceModel]:
    """Returns a list of RDS instances by tag

    Args:
        context (Context): Context object
        tag (CSPTag): CSP Tag by which RDS instances should be searched for

    Returns:
        Union[list[CSPRDSInstanceModel], None]: List of RDS instances if found, else None
    """
    csp_rds_instances = context.rds_inventory_manager.get_csp_rds_instances()
    return [
        csp_rds_instance for csp_rds_instance in csp_rds_instances.items if tag in csp_rds_instance.csp_info.csp_tags
    ]
