from typing import Protocol, Union, runtime_checkable

import requests

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ErrorResponse
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import (
    CSPK8sApplicationModel,
    CSPK8sApplicationsListModel,
    CSPK8sClustersListModel,
    CSPK8sClustersModel,
    CSPK8sResourceModel,
    CSPK8sResourcesListModel,
)


@runtime_checkable
class IEKSInventoryManager(Protocol):
    def trigger_k8s_inventory_refresh(self, csp_account_id: str) -> str: ...

    def get_csp_k8s_clusters(
        self,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: list = [],
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sClustersListModel, ErrorResponse]: ...

    def get_csp_k8s_instance_by_id(
        self,
        csp_k8s_instance_id: str,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sClustersModel, ErrorResponse]: ...

    def trigger_k8s_cluster_refresh(self, csp_cluster_id: str) -> str: ...

    def register_k8s_cluster_with_dscc(self, csp_k8s_instance_id: str) -> str: ...

    def unregister_k8s_cluster_from_dscc(self, csp_k8s_instance_id: str) -> str: ...

    def unregister_k8s_cluster_from_dscc_status_code(self, csp_k8s_instance_id: str) -> int: ...

    def validate_k8s_cluster_accessTo_dscc(self, csp_k8s_instance_id: str) -> str: ...

    def validate_k8s_cluster_access_to_dscc_status_code(self, csp_k8s_instance_id: str) -> int: ...

    def get_csp_k8s_resources(
        self,
        csp_k8s_instance_id: str,
        limit: int = 1000,
        offset: int = 1,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sResourcesListModel, ErrorResponse]: ...

    def get_k8s_resource_by_id(self, csp_k8s_instance_id: str, csp_k8s_resource_id: str) -> CSPK8sResourceModel: ...

    def trigger_k8s_resource_refresh(self, csp_k8s_instance_id: str, csp_k8s_resource_id: str) -> str: ...

    def get_csp_k8s_applications(
        self,
        csp_k8s_instance_id: str,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sApplicationsListModel, ErrorResponse]: ...

    def get_k8s_app_by_id(self, csp_k8s_instance_id: str, csp_k8s_application_id: str) -> CSPK8sApplicationModel: ...

    def trigger_k8s_app_refresh(self, csp_k8s_instance_id: str, csp_k8s_application_id: str) -> str: ...
