"""
This Module contains steps Related to B&R Dashboard. This includes:
    Getting and validating inventory assets summary.
    Getting and validating protection summary.
    Everything that is related to dashboard UI page.
"""

import logging
from typing import Union
from waiting import wait, TimeoutExpired
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.app_type import AppType
from lib.common.enums.csp_type import CspType
from lib.common.enums.dashboard_backup_type import BackupType
from lib.common.enums.dashboard_resource_type import DashboardResourceType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_instance_model import CSPRDSInstanceListModel
from lib.dscc.backup_recovery.aws_protection.dashboard.domain_models.dashboard_and_reporting_model import (
    AWSInfoModel,
    CountModel,
    AzureVMDiskCountModel,
)
import tests.steps.aws_protection.cloud_account_manager_steps as CAMS
import tests.steps.aws_protection.common_steps as CommonSteps
from tests.e2e.aws_protection.context import Context
from lib.common.enums.compare_condition import CompareCondition
from lib.common.enums.protection_summary import ProtectionStatus
from lib.common.enums.protection_job_status import ProtectionJobStatus
import lib.dscc.backup_recovery.aws_protection.dashboard.domain_models.dashboard_and_reporting_model as Dashboard
import tests.steps.aws_protection.rds.csp_rds_inventory_manager_steps as CSPRDSInvMgrSteps
from tests.e2e.azure_protection.azure_context import AzureContext

logger = logging.getLogger()
config = ConfigManager.get_config()


def get_sync_summary(context: Union[Context, AzureContext], account_id: str):
    """
    Get summary and sync aws accounts, ec2 and ebs assets from dashboard endpoint.
    Endpoint will be called to the point that assets list and dashboard counts will be in sync.

    Args:
        context (Context|AzureContext): AWS/Azure protection test Context
        account_id (str): csp AWS account id

    Returns:
        Summary: tuple(aws_list_count_before, ec2_list_count_before, ebs_list_count_before, inventory_summary_after)
                 aws_list_count_before: account count from inventory list endpoint
                 ec2_list_count_before: ec2 count from inventory list endpoint
                 ebs_list_count_before: ebs count from inventory list endpoint
                 inventory_summary_after: summary from dashboard endpoint
    """

    def _get_summary():
        CommonSteps.refresh_inventory_with_retry(context, account_id)
        inventory_summary_before = get_inventory_summary(context)
        aws_list_count_before = CAMS.get_csp_accounts(context).total
        logger.info(f"aws list accounts before: {aws_list_count_before}")
        ec2_list_count_before = context.inventory_manager.get_csp_machine_instances().total
        logger.info(f"ec2 list accounts before: {ec2_list_count_before}")
        ebs_list_count_before = context.inventory_manager.get_csp_volumes().total
        logger.info(f"ebs list accounts before: {ebs_list_count_before}")

        # TODO
        # Add before and after count for Azure VM and Disks

        # in case of flakiness, only reasonable way is to wait here for 5 minutes for dashboard refresh
        inventory_summary_after = get_inventory_summary(context)
        if inventory_summary_before == inventory_summary_after:
            return (aws_list_count_before, ec2_list_count_before, ebs_list_count_before, inventory_summary_after)

    try:
        summary = wait(_get_summary, timeout_seconds=600, sleep_seconds=15)
        return summary
    except TimeoutExpired as e:
        actual_count = get_inventory_summary(context)
        raise AssertionError(f"Summary: {actual_count}, {e}")


def validate_inventory_summary_dashboard_change(
    context: Union[Context, AzureContext],
    initial_dashboard_count: int,
    resource_type: DashboardResourceType,
    condition: CompareCondition,
) -> bool:
    """
    Validate if dashboard counts are correctly increase or decrease.

    Args:
        context (Context|AzureContext): AWS/Azure protection test Context
        initial_dashboard_count (int): asset count from dashboard endpoint that will be compared according to condition
        resource_type (DashboardResourceType): type of asset, example: ec2, ebs, vms ...
        condition (CompareCondition): Compare condition greater, equal or less.

    Returns:
        validation (bool): True if validate is successful, False otherwise
    """

    def _check_summary():
        current_dashboard_count = list(get_inventory_summary(context).to_dict()[resource_type.value].values())[0]

        logger.info(f"params: {resource_type.value}, {initial_dashboard_count=}")
        logger.info(f"Condition {condition.name}, {current_dashboard_count=},{initial_dashboard_count=}")

        # the "condition" reads left->right
        result_list_diff = condition.value(current_dashboard_count, initial_dashboard_count)
        return result_list_diff

    try:
        wait(_check_summary, timeout_seconds=600, sleep_seconds=60)
    except TimeoutExpired as e:
        actual_count = get_inventory_summary(context)
        raise AssertionError(f"{e} | {resource_type} count expected is different {actual_count}")


def validate_inventory_summary_dashboard(
    context: Union[Context, AzureContext],
    csp_account_id: str,
    dashboard_count_before: int,
    resource_type: DashboardResourceType,
    condition: CompareCondition,
    refresh_inventory: bool = True,
    list_items_count_before: int = -1,
) -> bool:
    """
    Validate if dashboard counts are correctly increase or decrease.

    Args:
        context (Context|AzureContext): AWS/Azure protection test Context
        csp_account_id (str): csp AWS account id
        dashboard_count_before (int): asset count from dashboard endpoint that will be compared according to condition
        resource_type (DashboardResourceType): type of asset, example: ec2, ebs, vms ...
        condition (CompareCondition): Compare condition greater, equal or less.
        refresh_inventory (bool, optional): Refresh aws assets inventory before reading count. Defaults to True.
        list_items_count_before (int, optional): If specified then it will be taken into calculations of expected
            result. Defaults to -1, means do not take it to calculation. Use if dashboard is miscounted with the lists.

    Returns:
        bool: validate successful -> True
    """

    def _check_summary():
        list_items_count_current = 0
        if resource_type == DashboardResourceType.AWS_ACCOUNTS and list_items_count_before > -1:
            list_items_count_current = CAMS.get_csp_accounts(context).total

        if resource_type == DashboardResourceType.AWS_VMS and list_items_count_before > -1:
            CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account_id)
            list_items_count_current = context.inventory_manager.get_csp_machine_instances().total

        if resource_type == DashboardResourceType.AWS_VOLUMES and list_items_count_before > -1:
            CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account_id)
            list_items_count_current = context.inventory_manager.get_csp_volumes().total

        if resource_type == DashboardResourceType.VCENTER_VMS and list_items_count_before > -1:
            list_items_count_current = context.hypervisor_manager.get_vms().json().get("total")

        if resource_type == DashboardResourceType.RDS and list_items_count_before > -1:
            list_items_count_current = CSPRDSInvMgrSteps.get_csp_rds_instances(context=context).total

        expected_dashboard_count = dashboard_count_before
        if list_items_count_before > -1:
            expected_dashboard_count = dashboard_count_before + (list_items_count_current - list_items_count_before)

        current_dashboard_count = list(get_inventory_summary(context).to_dict()[resource_type.value].values())[0]

        logger.info(
            f"params: {resource_type.value}, {dashboard_count_before=}, \
                {list_items_count_current=},{list_items_count_before=}"
        )
        logger.info(f"Condition {condition.name}, {expected_dashboard_count=},{current_dashboard_count=}")
        result_list_diff = condition.value(expected_dashboard_count, current_dashboard_count)
        result_current_status = condition.value(list_items_count_current, current_dashboard_count)
        return True if result_list_diff or result_current_status else False

    if refresh_inventory:
        CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account_id)

    try:
        wait(_check_summary, timeout_seconds=600, sleep_seconds=120)
    except TimeoutExpired as e:
        actual_count = get_inventory_summary(context)
        raise AssertionError(f"{e} | {resource_type} count expected is different {actual_count}")


def get_protections_summary_for_account(
    context: Union[Context, AzureContext], csp_account_id: str, csp_type: CspType = CspType.AWS
) -> Union[Dashboard.AWSInfoModel, Dashboard.AzureInfoModel]:
    """
    Get AWSInfo or AzureInfo object with protection statuses.

    Args:
        context (Context|AzureContext): AWS or Azure protection test Context
        csp_account_id (str): csp AWS account id
        csp_type (CspType): CspType enum for AWS, Azure. Defaults to AWS.

    Returns:
        Dashboard.AWSInfoModel or Dashboard.AzureInfoModel: object that holds protection statuses from dashboard with count.
    """
    logger.info(f"Getting protection summary for account: {csp_account_id}")
    summary = context.dashboard_manager.get_protections_summary()

    if csp_type.value == "AWS":
        logger.info(f"Protection summary has {len(summary.csp_accounts.aws_info)} CSPAccounts")
        aws_info = [aws_account for aws_account in summary.csp_accounts.aws_info if aws_account.id == csp_account_id]
        # NOTE: a fresh account, or cleaned from assets will not have a dashboard entry
        aws_info = aws_info[0] if aws_info else AWSInfoModel()
        logger.info(f"Returning AWSInfo: {aws_info}")
        return aws_info

    # TODO
    # Add similarly for Azure depending on test case


def get_protection_summary_count_by_status(
    csp_info: Union[Dashboard.AWSInfoModel, Dashboard.AzureInfoModel], protection_status: ProtectionStatus
) -> Union[CountModel, AzureVMDiskCountModel]:
    """
    Get summary count from AWSInfo/AzureInfo object for specific protection status. It is not calling endpoint.

    Args:
        csp_info (Dashboard.AWSInfoModel or Dashboard.AzureInfoModel): object that holds protection statuses from dashboard with count.
            Can be acquired from get_protections_summary_for_account()
        protection_status (ProtectionStatus): protection statuses like pending, partial ...

    Returns:
        CountModel|AzureVMDiskCountModel: AWS or Azure object that holds machines,volumes or disks,vms count
    """
    count = None
    if protection_status == ProtectionStatus.PENDING:
        count = csp_info.pending
    elif protection_status == ProtectionStatus.PARTIAL:
        count = csp_info.partial
    elif protection_status == ProtectionStatus.PROTECTED:
        count = csp_info.protected
    elif protection_status == ProtectionStatus.LAPSED:
        count = csp_info.lapsed
    elif protection_status == ProtectionStatus.PAUSED:
        count = csp_info.paused
    else:
        count = csp_info.unprotected

    return count


def log_account_inventory_and_dashboard_counts(context: Union[Context, AzureContext], csp_account_name: str):
    """
    Perform Inventory and Dashboard count logging

    Args:
        context (Context|AzureContext): AWS/Azure protection test Context
        csp_account_name (str): csp aws account name. example context.sanity_account_name
    """
    # get Inventory items for account
    csp_account = CAMS.get_csp_account_by_csp_name(context, account_name=csp_account_name, is_found_assert=False)
    if not csp_account:
        logger.info(f"Did not find csp_account: '{csp_account_name}', skipping asset counts")
        return

    logger.info(f"Logging Inventory and Dashboard asset counts for account: {csp_account_name}")
    CommonSteps.refresh_inventory_with_retry(context=context, account_id=csp_account.id)
    logger.info(f"Inventory refreshed for account: {csp_account.id}")

    # get only the Machines and Volumes for this account
    filter = f"accountInfo/id eq {csp_account.id}"
    csp_machine_list = context.inventory_manager.get_csp_machine_instances(filter=filter).items
    csp_volume_list = context.inventory_manager.get_csp_volumes(filter=filter).items

    logger.info("Inventory")
    # logger.info count in each ProtectionState
    for protection_status in ProtectionStatus:
        # get all Machines and Volumes from Inventory that have this ProtectionStatus
        csp_machines = [
            csp_machine for csp_machine in csp_machine_list if csp_machine.protectionStatus == protection_status.name
        ]
        csp_volumes = [
            csp_volumes for csp_volumes in csp_volume_list if csp_volumes.protectionStatus == protection_status.name
        ]
        logger.info(
            f"ProtectionStatus: {protection_status.value:<15} Machines: {len(csp_machines):<5} \
                Volumes: {len(csp_volumes):<5}"
        )

    logger.info(f"Inventory total Machine count: {len(csp_machine_list)}")
    logger.info(f"Inventory total Volume count:  {len(csp_volume_list)}")

    logger.info("---")

    logger.info("Dashboard")
    # get Dashboard counts for account
    csp_info = get_protections_summary_for_account(context=context, csp_account_id=csp_account.id)
    machine_total = 0
    volume_total = 0
    # logger.info dashboard counts
    for protection_status in ProtectionStatus:
        status_count = get_protection_summary_count_by_status(csp_info=csp_info, protection_status=protection_status)
        logger.info(
            f"ProtectionStatus: {protection_status.value:<15} Machines: {status_count.machines:<5}\
                  Volumes: {status_count.volumes:<5}"
        )
        machine_total += status_count.machines
        volume_total += status_count.volumes

    logger.info(f"Dashboard total Machine count: {machine_total}")
    logger.info(f"Dashboard total Volume count:  {volume_total}")


def log_inventory_and_dashboard_counts(context: Context):
    """
    Perform Inventory and Dashboard count logging for both "context.aws_one_account_name" and
    "context.aws_two_account_name"

    Args:
        context (Context): AWS protection test Context
    """
    log_account_inventory_and_dashboard_counts(context=context, csp_account_name=context.aws_one_account_name)
    log_account_inventory_and_dashboard_counts(context=context, csp_account_name=context.aws_two_account_name)


def validate_rds_dashboard_protection_summary(
    context: Context,
    csp_account: CSPAccountModel,
    protection_status: ProtectionStatus,
    condition: CompareCondition,
    current_dashboard_value: int = 0,
):
    """Validates CSP RDS dashboard protection summary count based on the 'condition' provided

    Args:
        context (Context): Context object
        csp_account (CSPAccountModel): CSPAccountModel object
        protection_status (ProtectionStatus): Protection Status of RDS to be validated
        condition (CompareCondition): Condition to be used to validate the protection_status
        current_dashboard_value (int): The current value for the Dashboard, to add onto the expected value to find in the Dashboard
    """
    instances_filter: str = (
        f"accountInfo/id eq '{csp_account.id}' and protectionStatus eq '{protection_status.value.upper()}'"
    )
    logger.info(f"Fetching {protection_status.value} RDS instances")
    csp_rds_instances: CSPRDSInstanceListModel = CSPRDSInvMgrSteps.get_csp_rds_instances(
        context=context,
        filter=instances_filter,
    )
    logger.info(f"{protection_status.value} RDS instances = {csp_rds_instances}")

    logger.info(f"Fetching Dashboard Protection Summary for account {csp_account.id}")
    aws_info: AWSInfoModel = get_protections_summary_for_account(
        context=context,
        csp_account_id=csp_account.id,
    )
    logger.info(f"Protection Summary for account {csp_account.id} is {aws_info}")
    logger.info(f"{protection_status.value} RDS instances count = {csp_rds_instances.total}")

    wait_for_rds_protection_summary_change(
        context,
        csp_account=csp_account,
        protection_status=protection_status,
        condition=condition,
        current_value=csp_rds_instances.total + current_dashboard_value,
    )


def wait_dashboard_protection_jobs(
    context: Union[Context, AzureContext],
    jobs_count_dict,
    from_timestamp,
    status: ProtectionJobStatus,
    condition: CompareCondition,
):
    def _compare():
        jobs_count_after, _ = get_protection_jobs(context, from_timestamp)
        if condition.value(jobs_count_dict[status], jobs_count_after[status]):
            return jobs_count_after
        else:
            return False

    try:
        count_value_after = wait(_compare, timeout_seconds=3800, sleep_seconds=60)
    except TimeoutExpired:
        jobs_count_after, _ = get_protection_jobs(context, from_timestamp)
        raise ValueError(f"Protection Jobs before: {jobs_count_dict[status]}, after: {jobs_count_after[status]}")
    logger.info(f"Protection Jobs before: {jobs_count_dict[status]}, after: {count_value_after[status]}")
    return count_value_after


def wait_dashboard_eks_apps(context: Context, count_before: int, condition: CompareCondition):
    """Waits for compare condition of EKS apps counter in dashboard

    Args:
        context (Context): Context object
        count_before (int): Number of EKS apps before update
        condition (CompareCondition): Specifies if number should be less/greater/equal etc.
    """

    def _compare():
        eks_apps_count = get_inventory_summary(context).csp_eks_applications.aws
        logger.info(f"EKS apps count in dashboard before: {count_before}, and after wait: {eks_apps_count}")
        if condition.value(eks_apps_count, count_before):
            return eks_apps_count
        else:
            return False

    try:
        wait(_compare, timeout_seconds=3800, sleep_seconds=60)
    except TimeoutExpired:
        eks_apps_count = get_inventory_summary(context).csp_eks_applications.aws
        raise ValueError(f"EKS apps count before wait {count_before} and after {eks_apps_count}")


def wait_dashboard_ebs_volumes(context: Context, count_before: int, condition: CompareCondition):
    """Waits for compare condition of EBS volumes counter in dashboard

    Args:
        context (Context): Context object
        count_before (int): Number of EBS volumes before update
        condition (CompareCondition): Specifies if number should be less/greater/equal etc.
    """

    def _compare():
        ebs_volumes_count = get_inventory_summary(context).csp_volumes.aws
        logger.info(f"EBS volumes count in dashboard before: {count_before}, and after wait: {ebs_volumes_count}")
        if condition.value(ebs_volumes_count, count_before):
            return ebs_volumes_count
        else:
            return False

    try:
        wait(_compare, timeout_seconds=3800, sleep_seconds=60)
    except TimeoutExpired:
        ebs_volumes_count = get_inventory_summary(context).csp_volumes.aws
        raise ValueError(f"EBS volumes count before wait {count_before} and after {ebs_volumes_count}")


def get_protection_jobs(
    context: Union[Context, AzureContext], from_timestamp=None, app_type: AppType = AppType.aws
) -> tuple[dict[ProtectionJobStatus, int], str]:
    jobs = context.dashboard_manager.get_job_execution_status_summary(app_type=app_type)
    logger.info(f"{jobs=}")
    jobs_count = {ProtectionJobStatus.completed: 0, ProtectionJobStatus.failed: 0}

    if not jobs.job_status_info:
        return jobs_count, from_timestamp

    jobs.job_status_info.sort(key=lambda job: job.timestamp)
    jobs.job_status_info.reverse()

    if from_timestamp:
        jobs.job_status_info = [job for job in jobs.job_status_info if job.timestamp >= from_timestamp]
    else:
        jobs.job_status_info = [jobs.job_status_info[0]]
        from_timestamp = jobs.job_status_info[0].timestamp

    for job_status in jobs.job_status_info:
        for status in ProtectionJobStatus:
            if status not in jobs_count:
                jobs_count[status] = 0
            jobs_count[status] += job_status.__dict__[status.value]
    logger.info(f"{from_timestamp=}, {jobs_count=}")
    return jobs_count, from_timestamp


def wait_for_machine_protection_summary_change(
    context: Union[Context, AzureContext],
    csp_account: CSPAccountModel,
    protection_status: ProtectionStatus,
    condition: CompareCondition,
    current_value: int = None,
):
    filter = f"accountInfo/id eq {csp_account.id}"

    def _wait_summary():
        if current_value:
            cur_value = current_value
        else:
            csp_machines = context.inventory_manager.get_csp_machine_instances(filter=filter).items
            cur_value = len(
                [csp_machine for csp_machine in csp_machines if csp_machine.protectionStatus == protection_status.name]
            )

        result = condition.value(
            get_csp_machines_protections_summary_by_status(
                context=context, csp_account=csp_account, protection_status=protection_status
            ),
            cur_value,
        )
        return result

    try:
        wait(
            _wait_summary,
            timeout_seconds=60 * 60,
            sleep_seconds=30,
        )
    except TimeoutExpired as e:
        dashboard_value = get_csp_machines_protections_summary_by_status(
            context=context, csp_account=csp_account, protection_status=protection_status
        )
        if not current_value:
            current_value = context.inventory_manager.get_csp_machine_instances(filter=filter).items
        logger.info(
            f"Timeout for {protection_status}, current_value: {current_value}, dashboard_value: {dashboard_value} \
                condition: {condition}, csp_account: {csp_account}"
        )
        raise e


def wait_for_volume_protection_summary_change(
    context: Union[Context, AzureContext],
    csp_account: CSPAccountModel,
    protection_status: ProtectionStatus,
    condition: CompareCondition,
    current_value: int = None,
):
    filter = f"accountInfo/id eq {csp_account.id}"

    def _wait_summary():
        if current_value:
            cur_value = current_value
        else:
            csp_volumes = context.inventory_manager.get_csp_volumes(filter=filter).items
            cur_value = len(
                [csp_volumes for csp_volumes in csp_volumes if csp_volumes.protectionStatus == protection_status.name]
            )
        summary_value = get_csp_volumes_protections_summary_by_status(
            context=context, csp_account=csp_account, protection_status=protection_status
        )
        logger.info(f"{protection_status=}, {condition=}, {cur_value=}, {summary_value=}")

        result = condition.value(summary_value, cur_value)
        return result

    try:
        wait(
            _wait_summary,
            timeout_seconds=60 * 60,
            sleep_seconds=60,
        )
    except TimeoutExpired as e:
        dashboard_value = get_csp_volumes_protections_summary_by_status(
            context=context, csp_account=csp_account, protection_status=protection_status
        )
        if not current_value:
            current_value = context.inventory_manager.get_csp_volumes(filter=filter).items
        logger.info(
            f"Timeout for {protection_status}, current_value: {current_value}, dashboard_value: {dashboard_value} \
                condition: {condition}, csp_account: {csp_account}"
        )
        raise e


def wait_for_rds_protection_summary_change(
    context: Context,
    csp_account: CSPAccountModel,
    protection_status: ProtectionStatus,
    condition: CompareCondition,
    current_value: int,
):
    try:
        wait(
            lambda: condition.value(
                get_csp_rds_protections_summary_by_status(
                    context=context, csp_account=csp_account, protection_status=protection_status
                ),
                current_value,
            ),
            timeout_seconds=60 * 60,
            sleep_seconds=60,
        )
    except TimeoutExpired as e:
        dashboard_value = get_csp_rds_protections_summary_by_status(
            context=context, csp_account=csp_account, protection_status=protection_status
        )
        logger.error(
            f"Timeout for {protection_status}, current_value: {current_value}, dashboard_value: {dashboard_value} \
                condition: {condition}, csp_account: {csp_account}"
        )
        raise e


def get_csp_machines_protections_summary_by_status(
    context: Union[Context, AzureContext],
    csp_account: CSPAccountModel,
    protection_status: ProtectionStatus,
    csp_type: CspType = CspType.AWS,
) -> int:
    asset_status: Dashboard.ProtectionsSummaryModel = context.dashboard_manager.get_protections_summary()

    if csp_type.value == "AWS":
        aws_info: Dashboard.AWSInfoModel = [
            aws_account for aws_account in asset_status.csp_accounts.aws_info if aws_account.id == csp_account.id
        ]

        if len(aws_info) == 0:
            return 0

        aws_info = aws_info[0]

        if protection_status.value == ProtectionStatus.PENDING.value:
            return aws_info.pending.machines
        elif protection_status.value == ProtectionStatus.PARTIAL.value:
            return aws_info.partial.machines
        elif protection_status.value == ProtectionStatus.PROTECTED.value:
            return aws_info.protected.machines
        elif protection_status.value == ProtectionStatus.LAPSED.value:
            return aws_info.lapsed.machines
        elif protection_status.value == ProtectionStatus.PAUSED.value:
            return aws_info.paused.machines
        else:
            return aws_info.unprotected.machines

    # TODO
    # Add similarly for Azure depending on test case


def get_csp_volumes_protections_summary_by_status(
    context: Context,
    csp_account: CSPAccountModel,
    protection_status: ProtectionStatus,
    csp_type: CspType = CspType.AWS,
) -> int:
    asset_status: Dashboard.ProtectionsSummaryModel = context.dashboard_manager.get_protections_summary()

    if csp_type.value == "AWS":
        aws_info: Dashboard.AWSInfoModel = [
            aws_account for aws_account in asset_status.csp_accounts.aws_info if aws_account.id == csp_account.id
        ]

        if len(aws_info) == 0:
            return 0

        aws_info = aws_info[0]

        if protection_status.value == ProtectionStatus.PENDING.value:
            return aws_info.pending.volumes
        elif protection_status.value == ProtectionStatus.PARTIAL.value:
            return aws_info.partial.volumes
        elif protection_status.value == ProtectionStatus.PROTECTED.value:
            return aws_info.protected.volumes
        elif protection_status.value == ProtectionStatus.LAPSED.value:
            return aws_info.lapsed.volumes
        elif protection_status.value == ProtectionStatus.PAUSED.value:
            return aws_info.paused.volumes
        else:
            return aws_info.unprotected.volumes

    # TODO
    # Add similarly for Azure depending on test case


def get_csp_rds_protections_summary_by_status(
    context: Context,
    csp_account: CSPAccountModel,
    protection_status: ProtectionStatus,
) -> int:
    asset_status: Dashboard.ProtectionsSummaryModel = context.dashboard_manager.get_protections_summary()
    aws_info: Dashboard.AWSInfoModel = [
        aws_account for aws_account in asset_status.csp_accounts.aws_info if aws_account.id == csp_account.id
    ]

    if len(aws_info) == 0:
        return 0

    aws_info = aws_info[0]

    if protection_status.value == ProtectionStatus.PENDING.value:
        return aws_info.pending.rds
    elif protection_status.value == ProtectionStatus.PARTIAL.value:
        return aws_info.partial.rds
    elif protection_status.value == ProtectionStatus.PROTECTED.value:
        return aws_info.protected.rds
    elif protection_status.value == ProtectionStatus.LAPSED.value:
        return aws_info.lapsed.rds
    elif protection_status.value == ProtectionStatus.PAUSED.value:
        return aws_info.paused.rds
    else:
        return aws_info.unprotected.rds


def get_inventory_summary(context: Context) -> Dashboard.InventorySummaryModel:
    inventory_summary = context.dashboard_manager.get_inventory_summary()

    return inventory_summary


def get_csp_cloud_usage_in_bytes(
    context: Union[Context, AzureContext], region: str, app_type: AppType = AppType.aws
) -> float:
    cloud_usage_summary: Dashboard.BackupCapacityUsageSummaryCloudModel = (
        context.dashboard_manager.get_backup_capacity_usage_summary(
            app_type=app_type,
            backup_type=BackupType.cloud,
        )
    )

    usage_in_bytes: float = 0.0

    for cloud in cloud_usage_summary.cloud:
        if cloud.location.split(":")[1] == region:
            usage_in_bytes = cloud.total_user_bytes

    return usage_in_bytes
