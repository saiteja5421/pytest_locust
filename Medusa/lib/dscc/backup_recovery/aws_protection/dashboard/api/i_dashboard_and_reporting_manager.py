from typing import Protocol, Union, runtime_checkable

from lib.common.enums.app_type import AppType
from lib.common.enums.dashboard_backup_type import BackupType
from lib.common.enums.range import Range
import lib.dscc.backup_recovery.aws_protection.dashboard.domain_models.dashboard_and_reporting_model as Dashboard


@runtime_checkable
class IDashboardManager(Protocol):
    def get_backup_capacity_usage_summary(
        self, app_type: AppType = AppType.all, backup_type: BackupType = BackupType.cloud
    ) -> Union[Dashboard.BackupCapacityUsageSummaryCloudModel, Dashboard.BackupCapacityUsageSummaryLocalModel]: ...

    def get_inventory_summary(self) -> Dashboard.InventorySummaryModel: ...

    def get_job_execution_status_summary(
        self, app_type: AppType = AppType.all, range: Range = Range.twenty_four_hours
    ) -> Dashboard.JobExecutionStatusSummaryModel: ...

    def get_protections_summary(
        self, app_type: AppType = AppType.all, limit: int = 5
    ) -> Dashboard.ProtectionsSummaryModel: ...
