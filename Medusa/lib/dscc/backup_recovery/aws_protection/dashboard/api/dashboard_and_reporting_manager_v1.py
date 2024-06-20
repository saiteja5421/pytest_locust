from typing import Union
import logging
from requests import codes, Response

from lib.common.common import get
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.app_type import AppType
from lib.common.enums.dashboard_backup_type import BackupType
from lib.common.enums.range import Range
from lib.common.users.user import User
import lib.dscc.backup_recovery.aws_protection.dashboard.models.dashboard_and_reporting_v1 as Dashboard

logger = logging.getLogger()


class DashboardManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['atlantia-url']}/app-data-management/{self.dscc['version']}"
        self.dashboard = self.atlantia_api["dashboard"]
        self.backup_capacity_usage_summary = self.atlantia_api["backup-capacity-usage-summary"]
        self.inventory_summary = self.atlantia_api["inventory-summary"]
        self.job_execution_status_summary = self.atlantia_api["job-execution-status-summary"]
        self.protections_summary = self.atlantia_api["protections-summary"]
        self.protections_policy_status_summary = self.atlantia_api["protections-policy-status-summary"]

    def get_backup_capacity_usage_summary(
        self, app_type: AppType = AppType.all, backup_type: BackupType = BackupType.cloud
    ) -> Union[Dashboard.BackupCapacityUsageSummaryCloudModel, Dashboard.BackupCapacityUsageSummaryLocalModel]:
        query_string = f"?backupType={backup_type.value}&appType={app_type.value}"
        path = f"{self.dashboard}/{self.backup_capacity_usage_summary}{query_string}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        if backup_type.value == BackupType.cloud.value:
            backup_capacity_usage_summary_cloud: Dashboard.BackupCapacityUsageSummaryCloud = (
                Dashboard.BackupCapacityUsageSummaryCloud.from_json(response.text)
            )
            return backup_capacity_usage_summary_cloud.to_domain_model()
        backup_capacity_usage_summary_local: Dashboard.BackupCapacityUsageSummaryLocal = (
            Dashboard.BackupCapacityUsageSummaryLocal.from_json(response.text)
        )
        return backup_capacity_usage_summary_local.to_domain_model()

    def get_inventory_summary(self) -> Dashboard.InventorySummaryModel:
        path = f"{self.dashboard}/{self.inventory_summary}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        inventory_summary: Dashboard.InventorySummary = Dashboard.InventorySummary.from_json(response.text)
        return inventory_summary.to_domain_model()

    def get_job_execution_status_summary(
        self, app_type: AppType = AppType.all, range: Range = Range.twenty_four_hours
    ) -> Dashboard.JobExecutionStatusSummaryModel:
        query_string = f"?appType={app_type.value}&range={range.value}"
        path = f"{self.dashboard}/{self.job_execution_status_summary}{query_string}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        job_execution_status_summary: Dashboard.JobExecutionStatusSummary = (
            Dashboard.JobExecutionStatusSummary.from_json(response.text)
        )
        return job_execution_status_summary.to_domain_model()

    def get_protections_summary(
        self, app_type: AppType = AppType.all, limit: int = 5
    ) -> Dashboard.ProtectionsSummaryModel:
        query_string = f"?appType={app_type.value}&limit={limit}"
        path = f"{self.dashboard}/{self.protections_summary}{query_string}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        protection_summary: Dashboard.ProtectionsSummary = Dashboard.ProtectionsSummary.from_json(response.text)
        return protection_summary.to_domain_model()

    # Present in the API spec. Expected to come in the future.
    def get_protections_policy_status_summary(self, app_type: AppType.all) -> Dashboard.ProtectionsPolicyStatusSummary:
        query_string = f"?appType={app_type.value}"
        path = f"{self.dashboard}/{self.protections_policy_status_summary}{query_string}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        protections_policy_status_summary: Dashboard.ProtectionsPolicyStatusSummary = (
            Dashboard.ProtectionsPolicyStatusSummary.from_json(response.text)
        )
        return protections_policy_status_summary.to_domain_model()
