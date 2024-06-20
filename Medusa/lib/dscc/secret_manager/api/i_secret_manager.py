from typing import Protocol, Union, runtime_checkable
import requests
from lib.dscc.secret_manager.models.domain_model.secret_payload_model import (
    AddAzureSecretModel,
    PatchSecretModel,
)
from lib.dscc.secret_manager.models.domain_model.secrets_model import SecretListModel, SecretModel
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ErrorResponse


@runtime_checkable
class ISecretManager(Protocol):

    def get_secret_by_id(
        self,
        secret_id: str,
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[SecretModel, ErrorResponse]: ...

    def get_all_secrets(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[SecretListModel, ErrorResponse]: ...

    def update_secret_by_id(
        self,
        secret_id: str,
        patch_secret_payload: PatchSecretModel,
    ) -> SecretModel: ...

    def delete_secret_by_id(self, secret_id: str) -> None: ...

    def add_azure_secrets(self, add_secret_payload: AddAzureSecretModel) -> SecretModel: ...
