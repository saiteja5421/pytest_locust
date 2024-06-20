import logging
from time import sleep
from typing import Union
from lib.common.users.user import User
from lib.common.common import get, get_task_id_from_header, post
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

from lib.dscc.backup_recovery.aws_protection.eks.models.csp_k8s_instances_filepoc import (
    CSPK8sClusters,
    CSPK8sClustersList,
)
from lib.dscc.backup_recovery.aws_protection.eks.models.csp_k8s_resources_filepoc import (
    CSPK8sResource,
    CSPK8sResourcesList,
)
from lib.dscc.backup_recovery.aws_protection.eks.models.csp_k8s_application_v1beta1_filepoc import (
    CSPK8sApplication,
    CSPK8sApplicationsList,
)
from lib.common.config.config_manager import ConfigManager
from requests import Response

logger = logging.getLogger()


class EKSInventoryManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.api_group = config["API-GROUP"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['atlantia-url']}/{self.api_group['hybrid-cloud']}/{self.dscc['beta-version']}"
        self.csp_accounts = self.atlantia_api["csp-accounts"]
        self.csp_k8s_clusters = self.atlantia_api["csp-k8s-clusters"]

    def trigger_k8s_inventory_refresh(self, csp_account_id: str) -> str:
        """Updates the CSP K8s inventory with latest information in the cloud account
            POST /hybrid-cloud/v1beta1/csp-accounts/{id}/k8s-refresh

        Args:
            csp_account_id (str): Unique identifier of a cloud account

        Returns:
            str: task uri that can be used to monitor progress of the operation
        """
        response: Response = self._raw_get_trigger_k8s_inventory_refresh_response(csp_account_id=csp_account_id)
        retry_limit = 6
        # Inventory refresh time may increase depending on the number of assets in different regions.
        while response.status_code == requests.codes.conflict and retry_limit > 0:
            sleep(120)
            response: Response = self._raw_get_trigger_k8s_inventory_refresh_response(csp_account_id=csp_account_id)
            retry_limit -= 1
        assert (
            response.status_code == requests.codes.accepted
        ), f"Error occurred while refresh of k8s inventory {response.text}"
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)[:-1]

    def _raw_get_trigger_k8s_inventory_refresh_response(self, csp_account_id: str) -> Response:
        path: str = f"{self.csp_accounts}/{csp_account_id}/k8s-refresh"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        return response

    def get_csp_k8s_clusters(
        self,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: list = [],
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sClustersListModel, ErrorResponse]:
        """Get list of CSP Kubernetes clusters

        Args:
            limit (int, optional): The number of items to omit from the beginning of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.Defaults to 1000.

            offset (int, optional): The maximum number of items to include in the response.
            Defaults to 1.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending). Sorting is supported on
            the following properties: name,accountId,state,k8sVersion,createdAt,updatedAt,
            validationInfo, ValidatedAt, refreshInfo,refreshedAt,cspInfo.region,cspInfo.networkInfo,
            vpc,id,cspInfo.status, cspInfo.createdAt. Defaults to "name".

            filter (list, optional): A list which contains one or more expressions by which to filter the results.
            The list item 'contains' expression can be used to filter the results based on case insensitive substring match.
            Defaults to "". These fields can be used for filtering: accountId, name, state, registrationStatus,
            k8sVersion, validationInfo.status, cspInfo.region, cspInfo.id, cspInfo.status, cspInfo.networkInfo.vpc.id

        Returns:
            CSPK8sClustersListModel: Returns a list of cloud service provider (CSP) Kubernetes (K8s) clusters
            ErrorResponse: if eks instance not found return error response
        """

        path: str = f"{self.csp_k8s_clusters}?offset={offset}&limit={limit}&sort={sort}"
        if len(filter):
            filter_str = filter[0]
            path += f"&filter={filter_str}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == expected_status_code, f"Error while retrieving k8s cluster list, {response.text}"
        logger.debug(f"response from get_csp_k8s_clusters: {response.text}")
        if response.status_code == requests.codes.ok:
            csp_cluster_list: CSPK8sClustersList = CSPK8sClustersList.from_json(response.text)
            return csp_cluster_list.to_domain_model()
        else:
            return ErrorResponse(**response.json())

    # GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}
    def get_csp_k8s_instance_by_id(
        self,
        csp_k8s_instance_id: str,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sClustersModel, ErrorResponse]:
        """Returns details of a specified cloud service provider (CSP) K8s cluster instance.
           GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}

        Args:
            csp_k8s_instance_id (str): Unique identifier of a CSP k8s cluster instance

        Returns:
            CSPK8sClustersModel: Details of a CSP K8s cluster instance
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving k8s cluster instance detail by id, {response.content}"
        logger.info(f"response from get_csp_k8s_instance_by_id: {response.text}")
        if response.status_code == requests.codes.ok:
            csp_k8s_clusters: CSPK8sClusters = CSPK8sClusters.from_json(response.text)
            return csp_k8s_clusters.to_domain_model()
        else:
            return ErrorResponse(**response.json())

    def trigger_k8s_cluster_refresh(self, csp_cluster_id: str) -> str:
        """Refresh a Kubernetes cluster with latest
           POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/refresh

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster

        Returns:
            str:  Task uri that can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_cluster_id}/refresh"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.accepted, "Error while performing k8s cluster refresh"
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)[:-1]

    # Register the Kubernetes cluster with DSCC
    # POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{id}/register
    def register_k8s_cluster_with_dscc(self, csp_k8s_instance_id: str) -> str:
        """Register the Kubernetes cluster with DSCC
           POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{id}/register

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster

        Returns:
            str: Returns the command that needs to be executed to configure DSCC
            access to the Kubernetes resources belonging to the Kubernetes cluster
            in the customer's cloud account
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/register"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, "Error while registering k8s cluster"
        return response.text.strip('"')

    # TODO: Verify if any solution for string returned from api
    # Unregister a Kubernetes cluster POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/unregister
    def unregister_k8s_cluster_from_dscc(self, csp_k8s_instance_id: str) -> str:
        """Unregister a Kubernetes cluster
           POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/unregister

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster

        Returns:
            str: task uri that can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/unregister"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        # assert response.status_code == requests.codes.accepted
        # return (self.tasks.get_task_id_from_header(response))[:-1]
        # Since unregister flow is not fully implemented, right now returning command instead of task_id
        assert response.status_code == requests.codes.accepted, "Error while unregistering k8s cluster"
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)[:-1]

    # Unregister a Kubernetes cluster POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/unregister
    def unregister_k8s_cluster_from_dscc_status_code(self, csp_k8s_instance_id: str) -> int:
        """Unregister a Kubernetes cluster
           POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/unregister

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster

        Returns:
            int: status code of response
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/unregister"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        return response.status_code

    # Validate DSCC has access to the specified Kubernetes cluster
    # POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{id}/validate
    def validate_k8s_cluster_accessTo_dscc(self, csp_k8s_instance_id: str) -> str:
        """Validate DSCC has access to the specified Kubernetes cluster in customer's cloud account

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster

        Returns:
            str: task uri that can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/validate"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.accepted, "Error while validating k8s cluster access to DSCC"
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)[:-1]

    # Validate DSCC has access to the specified Kubernetes cluster
    # POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{id}/validate
    def validate_k8s_cluster_access_to_dscc_status_code(self, csp_k8s_instance_id: str) -> int:
        """Validate DSCC has access to the specified Kubernetes cluster in customer's cloud account

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster

        Returns:
            int: status code of response
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/validate"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        return response.status_code

    # K8s resource methods
    # GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-resources

    def get_csp_k8s_resources(
        self,
        csp_k8s_instance_id: str,
        limit: int = 1000,
        offset: int = 1,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sResourcesListModel, ErrorResponse]:
        """Get list of Kubernetes resources belonging to the specified Kubernetes cluster
           GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-resources

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster
            offset (int, optional): The number of items to omit from the beginning of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items. Defaults to 0

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 20.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending). Sorting is supported on
            the following properties: name,state,createdAt,updatedAt, refreshInfo.refreshedAt,
            refreshInfo.status, namespaceInfo.resourceUri, k8sInfo.kind, k8sInfo.createdAt.

            filter (str, optional): An expression by which to filter the results. A 'contains' expression
            can be used to filter the results based on case insensitive substring match. E.g. filter=contains(name, 'r-')
            will return all Kubernetes resources with names containing the string 'r-' or 'R-'.
            These fields can be used for filtering: name, k8sInfo.kind, k8sInfo.id, namespaceScoped,
            namespaceInfo.resourceUri

        Returns:
            CSPK8sResourcesListModel: Returns a list of Kubernetes resources
            ErrorResponse: if k8s resource is not found return error response
        """

        path: str = (
            f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/k8s-resources?offset={offset} \
            &limit={limit}&filter={filter}&sort={sort}"
        )
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving k8s cluster resources {response.text}"
        if response.status_code == requests.codes.ok:
            csp_k8s_resources_list: CSPK8sResourcesList = CSPK8sResourcesList.from_json(response.text)
            return csp_k8s_resources_list.to_domain_model()
        else:
            return ErrorResponse(**response.json())

    # Get details of a Kubernetes resource
    # GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-resources/{id}
    def get_k8s_resource_by_id(self, csp_k8s_instance_id: str, csp_k8s_resource_id: str) -> CSPK8sResourceModel:
        """Returns details of a specified cloud service provider (CSP) K8s cluster resource.
           GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-resources/{id}

        Args:
            csp_k8s_instance_id (str): Unique identifier of a CSP k8s cluster instance
            csp_k8s_resource_id (str): Unique identifier of a CSP k8s resource instance

        Returns:
            CSPK8sResourceModel: Details of a CSP K8s cluster resource
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/k8s-resources/{csp_k8s_resource_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == requests.codes.ok
        ), f"Error while retrieving k8s cluster resource details {response.content}"
        csp_k8s_resource: CSPK8sResource = CSPK8sResource.from_json(response.text)
        return csp_k8s_resource.to_domain_model()

    # Refresh a Kubernetes resource with its source
    # POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-resources/{id}/refresh
    def trigger_k8s_resource_refresh(self, csp_k8s_instance_id: str, csp_k8s_resource_id: str) -> str:
        """Refresh a Kubernetes resource with its source
           POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-resources/{id}/refresh

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster
            csp_k8s_resource_id (str): Unique identifier of a Kubernetes resource

        Returns:
            str: Task uri that can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/k8s-applications/{csp_k8s_resource_id}/refresh"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.accepted, "Error while performing k8s cluster resource refresh"
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)[:-1]

    # K8s application methods
    # GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-applications
    def get_csp_k8s_applications(
        self,
        csp_k8s_instance_id: str,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPK8sApplicationsListModel, ErrorResponse]:
        """Get list of applications belonging to the specified Kubernetes cluster
           GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-applications

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster
            offset (int, optional): The number of items to omit from the beginning of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items. Defaults to 0

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 20.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending). Sorting is supported on
            the following properties: name,state,createdAt,updatedAt, refreshInfo.refreshedAt,
            refreshInfo.status, namespaceInfo.resourceUri, k8sInfo.kind, k8sInfo.createdAt.

            filter (str, optional): An expression by which to filter the results.A 'contains'
            expression can be used to filter the results based on case insensitive substring
            match. E.g. filter=contains(name, 'a-') will return all K8s applications with names containing the string 'a-' or 'A-'.
            These fields can be used for filtering: name, state, protectionSupported, protectionStatus
            expected_status_code (str, optional): expected stautus code. Defaults to requests.codes.accepted
            expected_error (str, optional): expected error msg. Defaults to ""


        Returns:
            CSPK8sApplicationsListModel: Returns a list of applications belonging to the specified Kubernetes cluster
             ErrorResponse: if k8s applications are not found return error response
        """
        path: str = (
            f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/k8s-applications?offset={offset} \
            &limit={limit}&filter={filter}&sort={sort}"
        )
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving k8s cluster applications, {response.text}"
        # app_info = response.json()
        logger.debug(f"response from k8 application API: {response.text}")
        csp_k8s_application_list: CSPK8sApplicationsList = CSPK8sApplicationsList.from_json(response.text)
        return csp_k8s_application_list.to_domain_model()

    # Get details of a Kubernetes application
    # GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-applications/{id}
    def get_k8s_app_by_id(self, csp_k8s_instance_id: str, csp_k8s_application_id: str) -> CSPK8sApplicationModel:
        """Returns details of a specified cloud service provider (CSP) K8s cluster application.
           GET /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-applications/{id}

        Args:
            csp_k8s_instance_id (str): Unique identifier of a CSP k8s cluster instance
            csp_k8s_application_id (str): Unique identifier of a CSP k8s cluster application

        Returns:
            CSPK8sApplication: Details of a specified K8s application
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/k8s-applications/{csp_k8s_application_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == requests.codes.ok
        ), f"Error while retrieving k8s cluster application details, {response.content}"
        csp_k8s_application: CSPK8sApplication = CSPK8sApplication.from_json(response.text)
        return csp_k8s_application.to_domain_model()

    # Refresh a Kubernetes application with its source
    # POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-applications/{id}/refresh
    def trigger_k8s_app_refresh(self, csp_k8s_instance_id: str, csp_k8s_application_id: str) -> str:
        """Refresh static members of the K8s application with its source
           POST /hybrid-cloud/v1beta1/csp-k8s-clusters/{clusterId}/k8s-applications/{id}/refresh

        Args:
            csp_k8s_instance_id (str): Unique identifier of a Kubernetes cluster
            csp_k8s_application_id (str): Unique identifier of a Kubernetes application

        Returns:
        str: task uri that can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_k8s_clusters}/{csp_k8s_instance_id}/k8s-applications/{csp_k8s_application_id}/refresh"
        response: Response = post(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.accepted, "Error while performing k8s application refresh"
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)[:-1]
