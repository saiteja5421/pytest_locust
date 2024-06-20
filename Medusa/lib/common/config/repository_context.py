import logging
from typing import TypeVar

# CAM
from lib.dscc.backup_recovery.aws_protection.accounts.api.i_cloud_account_manager import ICloudAccountManager
from lib.dscc.backup_recovery.aws_protection.accounts.api.cloud_account_manager_v1beta1 import (
    CloudAccountManager as CloudAccountManagerV1Beta1,
)
from lib.dscc.backup_recovery.aws_protection.accounts.api.cloud_account_manager_v1beta1_filepoc import (
    CloudAccountManager as CloudAccountManagerV1Beta1Filepoc,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.api.eks_data_protection_manager_v1beta1 import (
    EKSDataProtectionManager as EKSDataProtectionManagerV1beta1,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.api.eks_data_protection_manager_v1beta1_filepoc import (
    EKSDataProtectionManager as EKSDataProtectionManagerV1beta1Filepoc,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.api.i_eks_data_protection_manager import (
    IEKSDataProtectionManager,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.api.gfrs_data_protection_manager_v1beta1 import (
    GFRSDataProtectionManagerV1Beta1,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.api.gfrs_data_protection_manager_v1beta1_filepoc import (
    GFRSDataProtectionManagerV1Beta1Filepoc,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.api.i_gfrs_data_protection_manager import IGFRSDataProtectionManager

# RDS IM
from lib.dscc.backup_recovery.aws_protection.rds.api.i_rds_inventory_manager import IRDSInventoryManager
from lib.dscc.backup_recovery.aws_protection.rds.api.rds_inventory_manager_v1beta1 import (
    RDSInventoryManager as RDSInventoryManagerV1beta1,
)
from lib.dscc.backup_recovery.aws_protection.rds.api.rds_inventory_manager_v1beta1_filepoc import (
    RDSInventoryManager as RDSInventoryManagerV1beta1Filepoc,
)
from lib.dscc.backup_recovery.aws_protection.eks.api.eks_inventory_manager_v1beta1 import (
    EKSInventoryManager as EKSInventoryManagerV1Beta1,
)
from lib.dscc.backup_recovery.aws_protection.eks.api.eks_inventory_manager_v1beta1_filepoc import (
    EKSInventoryManager as EKSInventoryManagerV1Beta1Filepoc,
)
from lib.dscc.backup_recovery.aws_protection.eks.api.i_eks_inventory_manager import IEKSInventoryManager

# IM
from lib.dscc.backup_recovery.aws_protection.inventory_manager.api.i_inventory_manager import IInventoryManager
from lib.dscc.backup_recovery.aws_protection.inventory_manager.api.inventory_manager_v1beta1 import (
    InventoryManager as InventoryManagerV1Beta1,
)
from lib.dscc.backup_recovery.aws_protection.inventory_manager.api.inventory_manager_v1beta1_filepoc import (
    InventoryManager as InventoryManagerV1Beta1Filepoc,
)

from lib.dscc.backup_recovery.aws_protection.backup_restore.api.rds_data_protection_manager_v1beta1 import (
    RDSDataProtectionManager as RDSDataProtectionManagerV1Beta1,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.api.rds_data_protection_manager_v1beta1_filepoc import (
    RDSDataProtectionManager as RDSDataProtectionManagerV1Beta1Filepoc,
)

# DPM
from lib.dscc.backup_recovery.aws_protection.backup_restore.api.i_data_protection_manager import IDataProtectionManager
from lib.dscc.backup_recovery.aws_protection.backup_restore.api.data_protection_manager_v1beta1 import (
    DataProtectionManager as DataProtectionManagerV1Beta1,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.api.data_protection_manager_v1beta1_filepoc import (
    DataProtectionManager as DataProtectionManagerV1Beta1Filepoc,
)

# Dashboard
from lib.dscc.backup_recovery.aws_protection.dashboard.api.dashboard_and_reporting_manager_v1 import (
    DashboardManager as DashboardManagerV1,
)
from lib.dscc.backup_recovery.aws_protection.dashboard.api.dashboard_and_reporting_manager_v1_filepoc import (
    DashboardManager as DashboardManagerV1Filepoc,
)
from lib.dscc.secret_manager.api.secret_manager_v1 import SecretManager as SecretManagerV1
from lib.dscc.secret_manager.api.secret_manager_v1_filepoc import SecretManager as SecretManagerV1Filepoc

from lib.dscc.backup_recovery.aws_protection.dashboard.api.i_dashboard_and_reporting_manager import IDashboardManager

# Secret Manager
from lib.dscc.secret_manager.api.i_secret_manager import ISecretManager

# GFRS Index Manager
from lib.dscc.backup_recovery.aws_protection.gfrs.api.i_gfrs_index_manager import IGFRSIndexManager
from lib.dscc.backup_recovery.aws_protection.gfrs.api.gfrs_index_manager_v1beta1 import (
    GFRSIndexManager as GFRSIndexManagerV1Beta1,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.api.gfrs_index_manager_v1beta1_filepoc import (
    GFRSIndexManager as GFRSIndexManagerV1beta1Filepoc,
)

from lib.dscc.backup_recovery.aws_protection.backup_restore.api.i_rds_data_protection_manager import (
    IRDSDataProtectionManager,
)

from lib.common.users.user import User

logger = logging.getLogger()


class RepositoryContext:
    T = TypeVar("T")

    @staticmethod
    def init_repository(repository_type: T, env_name: str, backend_version: str, user: User) -> T:
        """This method fetches exact repository for provided environment, backend version and user.

        Args:
            repository_type (T): Repository Type of respective service
            env_name (str): Environment name on which tests runs
            backend_version (str): Backend version name on which tests runs
            user (User): User Object

        Raises:
            Exception: If the Interface is not implemented then we raise an exception.

        Returns:
            T: this method returns exact repository type.
        """
        logger.info(f"Setting the {repository_type} repository with {env_name} and {backend_version} version")

        repository_map = {
            ICloudAccountManager: {
                "filepoc": {
                    "v1beta1": CloudAccountManagerV1Beta1Filepoc,
                },
                "stable": {
                    "v1beta1": CloudAccountManagerV1Beta1,
                },
            },
            IRDSInventoryManager: {
                "filepoc": {
                    "v1beta1": RDSInventoryManagerV1beta1Filepoc,
                },
                "stable": {
                    "v1beta1": RDSInventoryManagerV1beta1,
                },
            },
            IInventoryManager: {
                "filepoc": {
                    "v1beta1": InventoryManagerV1Beta1Filepoc,
                },
                "stable": {
                    "v1beta1": InventoryManagerV1Beta1,
                },
            },
            IRDSDataProtectionManager: {
                "filepoc": {
                    "v1beta1": RDSDataProtectionManagerV1Beta1Filepoc,
                },
                "stable": {
                    "v1beta1": RDSDataProtectionManagerV1Beta1,
                },
            },
            IDataProtectionManager: {
                "filepoc": {
                    "v1beta1": DataProtectionManagerV1Beta1Filepoc,
                },
                "stable": {
                    "v1beta1": DataProtectionManagerV1Beta1,
                },
            },
            IGFRSDataProtectionManager: {
                "filepoc": {
                    "v1beta1": GFRSDataProtectionManagerV1Beta1Filepoc,
                },
                "stable": {
                    "v1beta1": GFRSDataProtectionManagerV1Beta1,
                },
            },
            ISecretManager: {
                "filepoc": {
                    "v1": SecretManagerV1Filepoc,
                },
                "stable": {
                    "v1": SecretManagerV1,
                },
            },
            IEKSInventoryManager: {
                "filepoc": {
                    "v1beta1": EKSInventoryManagerV1Beta1Filepoc,
                },
                "stable": {
                    "v1beta1": EKSInventoryManagerV1Beta1,
                },
            },
            IDashboardManager: {
                "filepoc": {
                    "v1": DashboardManagerV1Filepoc,
                },
                "stable": {
                    "v1": DashboardManagerV1,
                },
            },
            IGFRSIndexManager: {
                "filepoc": {
                    "v1beta1": GFRSIndexManagerV1beta1Filepoc,
                },
                "stable": {
                    "v1beta1": GFRSIndexManagerV1Beta1,
                },
            },
            IEKSDataProtectionManager: {
                "filepoc": {
                    "v1beta1": EKSDataProtectionManagerV1beta1Filepoc,
                },
                "stable": {
                    "v1beta1": EKSDataProtectionManagerV1beta1,
                },
            },
        }

        repository = repository_map[repository_type][env_name][backend_version](user)
        if not isinstance(repository, repository_type):
            raise Exception("Interface is not implemented in repository")
        return repository
