import logging
import requests

from requests import codes, Response
from typing import Union

from lib.common.common import get, post, patch, delete
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ErrorResponse
from lib.dscc.secret_manager.models.domain_model.secret_payload_model import (
    AddAzureSecretModel,
    PatchSecretModel,
)
from lib.dscc.secret_manager.models.domain_model.secrets_model import SecretListModel, SecretModel

from lib.dscc.secret_manager.models.secrets_v1 import (
    Secret,
    SecretList,
)
from lib.dscc.secret_manager.payload.secret_payload_v1 import AddAzureSecret, PatchSecret

from lib.common.users.user import User
from lib.common.config.config_manager import ConfigManager

logger = logging.getLogger()


class SecretManager:
    """
    Secret Manager class to interact with Azure secret manager endpoints.

    Implementation of:
    Get azure report secret
    Get azure report assignments
    Post azure secret
    """

    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.secrets = self.atlantia_api["secrets"]
        self.url = f"{self.dscc['atlantia-url']}/api/{self.dscc['version']}"

    def get_secret_by_id(
        self,
        secret_id: str,
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[SecretModel, ErrorResponse]:
        response: Response = self._raw_get_secrets_by_id(secret_id=secret_id)
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.ok:
            secret: Secret = Secret.from_json(response.text)
            return secret.to_domain_model()
        else:
            return ErrorResponse(**response.json())

    # GET /api/v1/secrets/{id} - Report Secret
    def _raw_get_secrets_by_id(
        self,
        secret_id: str,
    ) -> Response:
        path: str = f"{self.secrets}/{secret_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response

    def get_all_secrets(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[SecretListModel, ErrorResponse]:
        """
        Get all the secret details

        Args:
            limit (int):limit query parameter.Default is 20
            offset (int):offset is the number of items from the beginning of the complete result set to the first
            item included in the response. Default is 0.
            sort (str): response attribute to sort by, followed by a direction indicator ("asc" or "desc").
            The attribute may be one of "assignmentsCount", "classifier", "createdAt", "createdBy", "id", "label",
            "lastUpdatedBy", "name", "service", "status", "subclassifier" or "updatedAt"
            default order is ascending
            filter (str): An OData expression to filter responses by attribute. The OData logical operator "eq" is
            case-sensitive and supported for attributes "classifier", "label", "name", "service", "status" and
            "subclassifier". The OData function "contains()" is not case-sensitive and supported for attributes
            "label", "name" and "service". The OData logical operator "and" is supported for all attributes.
            expected_status_code (requests.codes): API request codes

        Returns:
            SecretListModel: Response of list of all the secrets
        """
        response: Response = self._raw_get_secrets(limit=limit, offset=offset, sort=sort, filter=filter)
        assert response.status_code == expected_status_code, f"{response.text}"
        if expected_status_code == requests.codes.ok:
            secrets_list: SecretList = SecretList.from_json(response.text)
            return secrets_list.to_domain_model()
        else:
            return ErrorResponse(**response.json())

    # GET /api/v1/secrets - Report Secrets
    def _raw_get_secrets(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
    ) -> Response:
        """
        Get all the Secret definition GET /api/v1/secrets

        Args:
            limit (int):limit query parameter.Default is 20
            offset (int):offset is the number of items from the beginning of the complete result set to the first
            item included in the response. Default is 0.
            sort (str): response attribute to sort by, followed by a direction indicator ("asc" or "desc").
            default order is ascending. The attribute may be one of "assignmentsCount", "classifier", "createdAt",
            "createdBy", "id", "label", "lastUpdatedBy", "name", "service", "status", "subclassifier" or "updatedAt"
            filter (str): An OData expression to filter responses by attribute. The OData logical operator "eq" is
            case-sensitive and supported for attributes "classifier", "label", "name", "service", "status" and
            "subclassifier". The OData function "contains()" is not case-sensitive and supported for attributes
            "label", "name" and "service". The OData logical operator "and" is supported for all attributes.

        Returns:
            Response: All the secret definition info
        """
        path: str = f"{self.secrets}?offset={offset}&limit={limit}&sort={sort}&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response

    # PATCH /api/v1/secrets/{id} - Change Secret
    def update_secret_by_id(
        self,
        secret_id: str,
        patch_secret_payload: PatchSecretModel,
    ) -> SecretModel:
        """
        Changes an existing Secret using the Secret Redefinition object provided in the request body
        PATCH /api/v1/secrets/{id}

        Args:
            secret_id (str): ID of the Secret
            patch_secret_payload (PatchSecretModel): Payload for an update secret

        Returns:
            SecretModel: Response of the object Secret
        """
        path: str = f"{self.secrets}/{secret_id}"
        payload = PatchSecret.from_domain_model(domain_model=patch_secret_payload)
        response: Response = patch(
            self.url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.accepted, response.content
        secret: Secret = Secret.from_json(response.text)
        return secret.to_domain_model()

    # DELETE /api/v1/secrets/{id} - Remove Secret
    #  AS per API spec return 204 no content
    # A DELETE will return an empty response with HTTP result code 204 if there was no error, like so
    # https://github.hpe.com/cloud/secrets/blob/master/docs/SecretsAPIUsersGuide.md#delete-apiv1secretsid---remove-secret-
    def delete_secret_by_id(self, secret_id: str) -> None:
        """
        Removes the specified Secret
        DELETE /api/v1/secrets/{id}

        Args:
            secret_id (str): ID of the Secret

        Returns:
            none
        """
        path: str = f"{self.secrets}/{secret_id}"
        response: Response = delete(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == codes.no_content
        ), f"Delete secret {secret_id} is unsuccessful with response {response.text}"

    # POST /api/v1/secrets - Add Secret
    # NOTE: Task id not created and response code is 200 than 202 both are reported to developer
    def add_azure_secrets(self, add_secret_payload: AddAzureSecretModel) -> SecretModel:
        """
        Adds a new Azure Secret using the Secret Specification object provided in the request body
        POST /api/v1/secrets

        Args:
            add_secret_payload (AddAzureSecretModel): payload for add secrets

        Returns:
            SecretModel: Secret definition payload
        """
        path: str = self.secrets
        payload = AddAzureSecret.from_domain_model(domain_model=add_secret_payload)
        response: Response = post(
            self.url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == requests.codes.ok, response.content
        secret: Secret = Secret.from_json(response.text)
        return secret.to_domain_model()
