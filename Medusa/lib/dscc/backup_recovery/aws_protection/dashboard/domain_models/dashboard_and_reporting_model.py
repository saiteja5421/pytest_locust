from dataclasses import dataclass, field
import datetime
from typing import Optional
from dataclasses_json import dataclass_json, LetterCase, config

from lib.common.enums.app_type import AppType
from lib.common.enums.dashboard_backup_type import BackupType
from lib.common.enums.invoicing_model import InvoicingModel
from lib.common.enums.product_category import ProductCategory
from lib.common.enums.range import Range


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CountModel:
    machines: Optional[int] = 0
    volumes: Optional[int] = 0
    rds: Optional[int] = 0


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AWSInfoModel:
    lapsed: CountModel = field(default_factory=CountModel)
    partial: CountModel = field(default_factory=CountModel)
    pending: CountModel = field(default_factory=CountModel)
    paused: CountModel = field(default_factory=CountModel)
    protected: CountModel = field(default_factory=CountModel)
    unprotected: CountModel = field(default_factory=CountModel)
    id: str = ""
    csp_id: str = ""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudModel:
    location: str
    total_disk_bytes: float
    total_user_bytes: float


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VMWareInfoModel:
    id: str
    lapsed: int
    partial: int
    pending: int
    paused: int
    protected: int
    unprotected: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AccountsCountModel:
    aws: int
    ms365: int
    azure: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MachinesCountModel:
    aws: int
    # TODO
    # azure: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumesCountModel:
    aws: int
    # TODO
    # azure: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AWSCountModel:
    aws: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VMWareCountModel:
    vmware: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class StoresInfoModel:
    catalyst_gateway_id: str
    catalyst_gateway_name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class JobStatusInfoModel:
    timestamp: str
    completed: int
    failed: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class HypervisorManagersModel:
    vm_protection_limit: int
    vmware_info: list[VMWareInfoModel] = field(default_factory=list)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DatabasesInstancesInvSummaryModel:
    databases: int = 0
    instances: int = 0


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MsSqlInvSummaryModel:
    mssql: DatabasesInstancesInvSummaryModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountsModel:
    account_bytes: float
    csp_id: str
    id: str
    name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class BackupCapacityUsageSummaryCloudModel:
    app_type: AppType
    backup_type: BackupType
    cloud: list[CloudModel]
    cloud_store_disk_bytes_limit: Optional[float] = field(default=0)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class BackupCapacityUsageSummaryLocalModel:
    app_type: AppType
    backup_type: BackupType
    stores_info: list[StoresInfoModel]


# https://pages.github.hpe.com/cloud/storage-api/api-v1-index.html#get-/app-data-management/v1/dashboard/inventory-summary
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InventorySummaryModel:
    csp_accounts: AccountsCountModel
    csp_machines: MachinesCountModel
    csp_volumes: VolumesCountModel
    csp_eks_cluster: AWSCountModel
    csp_eks_applications: AWSCountModel
    data_stores: VMWareCountModel
    v_centers: VMWareCountModel
    virtual_machines: VMWareCountModel
    csp_rds: AWSCountModel = field(metadata=config(field_name="cspRDS"), default=None)
    databases: Optional[MsSqlInvSummaryModel] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class JobExecutionStatusSummaryModel:
    range: Range
    from_: str = field(metadata=config(field_name="from"))
    to: str
    job_status_info: list[JobStatusInfoModel]
    app_type: AppType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureVMDiskCountModel:
    disks: int
    vms: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureInfoModel:
    lapsed: AzureVMDiskCountModel
    partial: AzureVMDiskCountModel
    pending: AzureVMDiskCountModel
    paused: AzureVMDiskCountModel
    protected: AzureVMDiskCountModel
    unprotected: AzureVMDiskCountModel
    id: str
    csp_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureTenantsModel:
    azure_info: list[AzureInfoModel]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPaccountsModel:
    aws_info: list[AWSInfoModel] = field(default_factory=list)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureCapacityModel:
    disk_bytes: float
    user_bytes: float


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class UsageInfoModel:
    protected_azure_disks: int
    protected_azure_vms: int
    protected_ebs_volumes: int = field(metadata=config(field_name="protectedEBSVolumes"))
    protected_ec2_instances: int = field(metadata=config(field_name="protectedEC2Instances"))
    protected_eks_applications: int = field(metadata=config(field_name="protectedEKSApplications"))
    protected_ms365_users: int = field(metadata=config(field_name="protectedMS365Users"))
    protected_mssql_databases: int = field(metadata=config(field_name="protectedMSSQLDatabases"))
    protecte_rds_instances: int = field(metadata=config(field_name="protectedRDSInstances"))
    protected_vms: int = field(metadata=config(field_name="protectedVMs"))
    total_cloud_capacity: AzureCapacityModel
    total_on_prem_capacity: AzureCapacityModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SubscriptionAttributesModel:
    key: str
    value: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AvailableSubscriptionsModel:
    end_date: datetime
    invoicing_model: InvoicingModel
    product_category: ProductCategory
    start_date: datetime
    subscription_attributes: SubscriptionAttributesModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SubscriptionInfoModel:
    committed: bool
    end_date: datetime
    invoicing_model: InvoicingModel
    product_category: ProductCategory
    start_date: datetime
    available_subscriptions: list[AvailableSubscriptionsModel]
    azure_disks_commit: int
    azure_vms_commit: int
    cloud_capacity_gib_commit: int
    cs_product_id: str
    ebs_commit: int
    ec2_commit: int
    subscription_key: str
    vm_count_commit: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureSubscriptionUsageModel:
    subscription_info: list[SubscriptionInfoModel]
    usage_info: list[UsageInfoModel]


# https://pages.github.hpe.com/cloud/storage-api/api-v1-index.html#get-/app-data-management/v1/dashboard/protections-summary
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionsSummaryModel:
    csp_accounts: CSPaccountsModel
    hypervisor_managers: HypervisorManagersModel
    # TODO: add "azureTenants" when available


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyCountModel:
    policy_applied: int
    policy_not_applied: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyAWSInfoModel:
    ebs: PolicyCountModel
    ec2: PolicyCountModel
    eks: PolicyCountModel
    rds: PolicyCountModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyAzureModel:
    disks: PolicyCountModel
    vms: PolicyCountModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionsPolicyStatusSummaryModel:
    awsinfo: PolicyAWSInfoModel
    azure: PolicyAzureModel
