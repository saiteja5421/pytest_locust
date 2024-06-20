from dataclasses import dataclass, field
import datetime
from typing import Optional
from dataclasses_json import dataclass_json, LetterCase, config

from lib.common.enums.app_type import AppType
from lib.common.enums.invoicing_model import InvoicingModel
from lib.common.enums.product_category import ProductCategory
from lib.common.enums.range import Range
from lib.common.enums.dashboard_backup_type import BackupType
from lib.dscc.backup_recovery.aws_protection.dashboard.domain_models.dashboard_and_reporting_model import (
    AvailableSubscriptionsModel,
    AzureCapacityModel,
    AzureInfoModel,
    AzureSubscriptionUsageModel,
    AzureTenantsModel,
    AzureVMDiskCountModel,
    CloudModel,
    StoresInfoModel,
    AccountsCountModel,
    MachinesCountModel,
    VolumesCountModel,
    AWSCountModel,
    SubscriptionAttributesModel,
    SubscriptionInfoModel,
    UsageInfoModel,
    VMWareCountModel,
    JobStatusInfoModel,
    CSPaccountsModel,
    HypervisorManagersModel,
    AWSInfoModel,
    VMWareInfoModel,
    CountModel,
    CSPAccountsModel,
    DatabasesInstancesInvSummaryModel,
    MsSqlInvSummaryModel,
    BackupCapacityUsageSummaryCloudModel,
    BackupCapacityUsageSummaryLocalModel,
    InventorySummaryModel,
    JobExecutionStatusSummaryModel,
    ProtectionsSummaryModel,
    PolicyCountModel,
    PolicyAWSInfoModel,
    PolicyAzureModel,
    ProtectionsPolicyStatusSummaryModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccounts:
    account_bytes: float
    csp_id: str
    id: str
    name: str

    def to_domain_model(self):
        return CSPAccountsModel(
            account_bytes=self.account_bytes,
            csp_id=self.csp_id,
            id=self.id,
            name=self.name,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Cloud:
    location: str
    total_disk_bytes: float
    total_user_bytes: float

    def to_domain_model(self):
        return CloudModel(
            location=self.location, total_disk_bytes=self.total_disk_bytes, total_user_bytes=self.total_user_bytes
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class BackupCapacityUsageSummaryCloud:
    app_type: AppType
    backup_type: BackupType
    cloud: list[Cloud]
    cloud_store_disk_bytes_limit: Optional[float] = field(default=0)

    def to_domain_model(self):
        return BackupCapacityUsageSummaryCloudModel(
            app_type=self.app_type,
            backup_type=self.backup_type,
            cloud=[item.to_domain_model() for item in self.cloud],
            cloud_store_disk_bytes_limit=self.cloud_store_disk_bytes_limit,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class StoresInfo:
    catalyst_gateway_id: str
    catalyst_gateway_name: str

    def to_domain_model(self):
        return StoresInfoModel(
            catalyst_gateway_id=self.catalyst_gateway_id,
            catalyst_gateway_name=self.catalyst_gateway_name,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class BackupCapacityUsageSummaryLocal:
    app_type: AppType
    backup_type: BackupType
    stores_info: list[StoresInfo]

    def to_domain_model(self):
        return BackupCapacityUsageSummaryLocalModel(
            app_type=self.app_type,
            backup_type=self.backup_type,
            stores_info=[item.to_domain_model() for item in self.stores_info],
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AccountsCount:
    aws: int
    ms365: int
    azure: int

    def to_domain_model(self):
        return AccountsCountModel(aws=self.aws, ms365=self.ms365, azure=self.azure)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MachinesCount:
    aws: int
    # TODO: Not available yet in filepoc
    # azure: int

    def to_domain_model(self):
        return MachinesCountModel(
            aws=self.aws,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumesCount:
    aws: int
    # TODO: Not available yet in filepoc
    # azure: int

    def to_domain_model(self):
        return VolumesCountModel(
            aws=self.aws,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class UsersCount:
    ms365: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AWSCount:
    aws: int

    def to_domain_model(self):
        return AWSCountModel(
            aws=self.aws,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VMWareCount:
    vmware: int

    def to_domain_model(self):
        return VMWareCountModel(
            vmware=self.vmware,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DatabasesInstancesInvSummary:
    databases: int = 0
    instances: int = 0

    def to_domain_model(self):
        return DatabasesInstancesInvSummaryModel(
            databases=self.databases,
            instances=self.instances,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MsSqlInvSummary:
    mssql: DatabasesInstancesInvSummary

    def to_domain_model(self):
        return MsSqlInvSummaryModel(
            mssql=self.mssql.to_domain_model(),
        )


# https://pages.github.hpe.com/cloud/storage-api/api-v1-index.html#get-/app-data-management/v1/dashboard/inventory-summary
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InventorySummary:
    csp_accounts: AccountsCount
    csp_machines: MachinesCount
    csp_volumes: VolumesCount
    csp_eks_cluster: AWSCount
    csp_eks_applications: AWSCount
    data_stores: VMWareCount
    v_centers: VMWareCount
    virtual_machines: VMWareCount
    application_hosts: int
    volume_protection_groups: int
    users: UsersCount
    csp_rds: AWSCount = field(metadata=config(field_name="cspRDS"), default=None)
    databases: Optional[MsSqlInvSummary] = None

    def to_domain_model(self):
        return InventorySummaryModel(
            csp_accounts=self.csp_accounts.to_domain_model(),
            csp_machines=self.csp_machines.to_domain_model(),
            csp_volumes=self.csp_volumes.to_domain_model(),
            csp_eks_cluster=self.csp_eks_cluster.to_domain_model(),
            csp_eks_applications=self.csp_eks_applications.to_domain_model(),
            data_stores=self.data_stores.to_domain_model(),
            v_centers=self.v_centers.to_domain_model(),
            virtual_machines=self.virtual_machines.to_domain_model(),
            csp_rds=self.csp_rds.to_domain_model() if self.csp_rds else None,
            databases=self.databases.to_domain_model() if self.databases else None,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class JobStatusInfo:
    timestamp: str
    completed: int
    failed: int

    def to_domain_model(self):
        return JobStatusInfoModel(
            timestamp=self.timestamp,
            completed=self.completed,
            failed=self.failed,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class JobExecutionStatusSummary:
    range: Range
    from_: str = field(metadata=config(field_name="from"))
    to: str
    job_status_info: list[JobStatusInfo]
    app_type: AppType

    def to_domain_model(self):
        return JobExecutionStatusSummaryModel(
            range=self.range,
            from_=self.from_,
            to=self.to,
            job_status_info=[item.to_domain_model() for item in self.job_status_info],
            app_type=self.app_type,
        )


# For the case where: unprotected=Count(machines=None, volumes=7)
# TypeError: '>' not supported between instances of 'int' and 'NoneType'
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Count:
    machines: Optional[int] = 0
    volumes: Optional[int] = 0
    rds: Optional[int] = 0

    def to_domain_model(self):
        return CountModel(
            machines=self.machines,
            volumes=self.volumes,
            rds=self.rds,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AWSInfo:
    lapsed: Count = field(default_factory=Count)
    partial: Count = field(default_factory=Count)
    pending: Count = field(default_factory=Count)
    paused: Count = field(default_factory=Count)
    protected: Count = field(default_factory=Count)
    unprotected: Count = field(default_factory=Count)
    id: str = ""
    csp_id: str = ""

    def to_domain_model(self):
        return AWSInfoModel(
            lapsed=self.lapsed.to_domain_model(),
            partial=self.partial.to_domain_model(),
            pending=self.pending.to_domain_model(),
            paused=self.paused.to_domain_model(),
            protected=self.protected.to_domain_model(),
            unprotected=self.unprotected.to_domain_model(),
            id=self.id,
            csp_id=self.csp_id,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VMWareInfo:
    id: str
    lapsed: int
    partial: int
    pending: int
    paused: int
    protected: int
    unprotected: int

    def to_domain_model(self):
        return VMWareInfoModel(
            id=self.id,
            lapsed=self.lapsed,
            partial=self.partial,
            pending=self.pending,
            paused=self.paused,
            protected=self.protected,
            unprotected=self.unprotected,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPaccounts:
    aws_info: list[AWSInfo] = field(default_factory=list)

    def to_domain_model(self):
        return CSPaccountsModel(
            aws_info=[item.to_domain_model() for item in self.aws_info],
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class HypervisorManagers:
    vm_protection_limit: int
    vmware_info: list[VMWareInfo] = field(default_factory=list)

    def to_domain_model(self):
        return HypervisorManagersModel(
            vm_protection_limit=self.vm_protection_limit,
            vmware_info=[item.to_domain_model() for item in self.vmware_info],
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionsSummary:
    csp_accounts: CSPaccounts
    hypervisor_managers: HypervisorManagers
    # TODO
    # azure_tenants: AzureTenants

    def to_domain_model(self):
        return ProtectionsSummaryModel(
            csp_accounts=self.csp_accounts.to_domain_model(),
            hypervisor_managers=self.hypervisor_managers.to_domain_model(),
            # azure_tenants=self.azure_tenants.to_domain_model(),
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureVMDiskCount:
    disks: int
    vms: int

    def to_domain_model(self):
        return AzureVMDiskCountModel(
            disks=self.disks,
            vms=self.vms,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureInfo:
    lapsed: AzureVMDiskCount
    partial: AzureVMDiskCount
    pending: AzureVMDiskCount
    paused: AzureVMDiskCount
    protected: AzureVMDiskCount
    unprotected: AzureVMDiskCount
    id: str
    csp_id: str

    def to_domain_model(self):
        return AzureInfoModel(
            lapsed=self.lapsed.to_domain_model(),
            partial=self.partial.to_domain_model(),
            pending=self.pending.to_domain_model(),
            paused=self.paused.to_domain_model(),
            protected=self.protected.to_domain_model(),
            unprotected=self.unprotected.to_domain_model(),
            id=self.id,
            csp_id=self.csp_id,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureTenants:
    azure_info: list[AzureInfo]

    def to_domain_model(self):
        return AzureTenantsModel(
            azure_info=[item.to_domain_model() for item in self.azure_info],
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureCapacity:
    disk_bytes: float
    user_bytes: float

    def to_domain_model(self):
        return AzureCapacityModel(
            disk_bytes=self.disk_bytes,
            user_bytes=self.user_bytes,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class UsageInfo:
    protected_azure_disks: int
    protected_azure_vms: int
    protected_ebs_volumes: int = field(metadata=config(field_name="protectedEBSVolumes"))
    protected_ec2_instances: int = field(metadata=config(field_name="protectedEC2Instances"))
    protected_eks_applications: int = field(metadata=config(field_name="protectedEKSApplications"))
    protected_ms365_users: int = field(metadata=config(field_name="protectedMS365Users"))
    protected_mssql_databases: int = field(metadata=config(field_name="protectedMSSQLDatabases"))
    protecte_rds_instances: int = field(metadata=config(field_name="protectedRDSInstances"))
    protected_vms: int = field(metadata=config(field_name="protectedVMs"))
    total_cloud_capacity: AzureCapacity
    total_on_prem_capacity: AzureCapacity

    def to_domain_model(self):
        return UsageInfoModel(
            protected_azure_disks=self.protected_azure_disks,
            protected_azure_vms=self.protected_azure_vms,
            protected_ebs_volumes=self.protected_ebs_volumes,
            protected_ec2_instances=self.protected_ec2_instances,
            protected_eks_applications=self.protected_eks_applications,
            protected_ms365_users=self.protected_ms365_users,
            protected_mssql_databases=self.protected_mssql_databases,
            protecte_rds_instances=self.protecte_rds_instances,
            protected_vms=self.protected_vms,
            total_cloud_capacity=self.total_cloud_capacity.to_domain_model(),
            total_on_prem_capacity=self.total_on_prem_capacity.to_domain_model(),
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SubscriptionAttributes:
    key: str
    value: str

    def to_domain_model(self):
        return SubscriptionAttributesModel(
            key=self.key,
            value=self.value,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AvailableSubscriptions:
    end_date: datetime
    invoicing_model: InvoicingModel
    product_category: ProductCategory
    start_date: datetime
    subscription_attributes: SubscriptionAttributes

    def to_domain_model(self):
        return AvailableSubscriptionsModel(
            end_date=self.end_date,
            invoicing_model=self.invoicing_model,
            product_category=self.product_category,
            start_date=self.start_date,
            subscription_attributes=self.subscription_attributes.to_domain_model(),
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SubscriptionInfo:
    committed: bool
    end_date: datetime
    invoicing_model: InvoicingModel
    product_category: ProductCategory
    start_date: datetime
    available_subscriptions: list[AvailableSubscriptions]
    azure_disks_commit: int
    azure_vms_commit: int
    cloud_capacity_gib_commit: int
    cs_product_id: str
    ebs_commit: int
    ec2_commit: int
    subscription_key: str
    vm_count_commit: int

    def to_domain_model(self):
        return SubscriptionInfoModel(
            available_subscriptions=[item.to_domain_model() for item in self.available_subscriptions],
            azure_disks_commit=self.azure_disks_commit,
            azure_vms_commit=self.azure_vms_commit,
            cloud_capacity_gib_commit=self.cloud_capacity_gib_commit,
            committed=self.committed,
            cs_product_id=self.cs_product_id,
            ebs_commit=self.ebs_commit,
            ec2_commit=self.ec2_commit,
            end_date=self.end_date,
            invoicing_model=self.invoicing_model,
            product_category=self.product_category,
            start_date=self.start_date,
            subscription_key=self.subscription_key,
            vm_count_commit=self.vm_count_commit,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureSubscriptionUsage:
    subscription_info: list[SubscriptionInfo]
    usage_info: list[UsageInfo]

    def to_domain_model(self):
        return AzureSubscriptionUsageModel(
            subscription_info=[item.to_domain_model() for item in self.subscription_info],
            usage_info=[item.to_domain_model() for item in self.usage_info],
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyCount:
    policy_applied: int
    policy_not_applied: int

    def to_domain_model(self):
        return PolicyCountModel(policy_applied=self.policy_applied, policy_not_applied=self.policy_not_applied)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyAWSInfo:
    ebs: PolicyCount
    ec2: PolicyCount
    eks: PolicyCount
    rds: PolicyCount

    def to_domain_model(self):
        return PolicyAWSInfoModel(
            ebs=self.ebs.to_domain_model(),
            ec2=self.ec2.to_domain_model(),
            eks=self.eks.to_domain_model(),
            rds=self.rds.to_domain_model(),
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyAzure:
    disks: PolicyCount
    vms: PolicyCount

    def to_domain_model(self):
        return PolicyAzureModel(disks=self.disks.to_domain_model(), vms=self.vms.to_domain_model())


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionsPolicyStatusSummary:
    awsinfo: PolicyAWSInfo
    azure: PolicyAzure

    def to_domain_model(self):
        return ProtectionsPolicyStatusSummaryModel(
            awsinfo=self.awsinfo.to_domain_model(), azure=self.azure.to_domain_model()
        )
